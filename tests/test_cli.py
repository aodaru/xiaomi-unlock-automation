import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "SCRIPT_PERMISO_DESBLOQUEO.py"
spec = importlib.util.spec_from_file_location("permiso", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ValidationTests(unittest.TestCase):
    def test_valid_arguments_are_normalized(self):
        token, shift, job_id = module.validate_arguments("fake-token", "1400", "job-1")
        self.assertEqual((token, shift, job_id), ("fake-token", 1400.0, "job-1"))

    def test_invalid_arguments_fail_before_network(self):
        for token, shift, job_id in [
            ("", "1400", "job-1"),
            ("fake-token", "nan", "job-1"),
            ("fake-token", "86400001", "job-1"),
            ("fake-token", "1400", "../unsafe"),
        ]:
            with self.assertRaises(module.ConfigurationError):
                module.validate_arguments(token, shift, job_id)

    def test_cli_missing_argument_returns_20_without_network(self):
        self.assertEqual(module.main(["--token", "fake-token", "--timeshift", "1"]), 20)

    def test_invalid_arguments_do_not_create_http_session(self):
        class UnexpectedDependency:
            def PoolManager(self, **kwargs):
                raise AssertionError("network dependency was initialized")

        self.assertEqual(
            module.main(
                ["--token", "fake-token", "--timeshift", "nan", "--job-id", "job-1"],
                dependencies=(None, None, UnexpectedDependency()),
            ),
            20,
        )

    def test_valid_execution_never_reads_stdin(self):
        class HTTP:
            Timeout = mock.Mock()

            def PoolManager(self, **kwargs):
                response = mock.Mock(status=200)
                response.data = module.json.dumps({"code": 0, "data": {"is_pass": 1}}).encode()
                response.release_conn = mock.Mock()
                manager = mock.Mock()
                manager.request.return_value = response
                return manager

        with tempfile.TemporaryDirectory() as work_dir, mock.patch(
            "builtins.input", side_effect=AssertionError("stdin must not be read")
        ):
            result = module.main(
                ["--token", "fake-token", "--timeshift", "1", "--job-id", "job-no-stdin",
                 "--work-dir", work_dir],
                dependencies=(None, None, HTTP()),
            )
        self.assertEqual(result, 0)


class ResponseTests(unittest.TestCase):
    def response(self, payload):
        class Response:
            data = module.json.dumps(payload).encode()

            def release_conn(self):
                pass

        return Response()

    def test_already_approved_is_a_successful_status(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"is_pass": 1}}
        )
        self.assertEqual(module.check_unlock_status(session, "secret-token", "device"), "already_allowed")

    def test_pending_status_is_allowed(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"is_pass": 4, "button_state": 1}}
        )
        self.assertEqual(module.check_unlock_status(session, "secret-token", "device"), "allowed")

    def test_too_new_status_preserves_deadline(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"is_pass": 4, "button_state": 3,
                                   "deadline_format": "10/01"}}
        )
        with self.assertRaisesRegex(module.FunctionalError, "cuenta demasiado nueva.*10/01"):
            module.check_unlock_status(session, "secret-token", "device")

    def test_blocked_apply_preserves_deadline_without_token(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"apply_result": 4, "deadline_format": "08/20"}}
        )
        with self.assertRaisesRegex(module.FunctionalError, "08/20") as caught:
            module.apply_unlock(session, "secret-token", "device")
        self.assertNotIn("secret-token", str(caught.exception))

    def test_rejected_apply_returns_functional_error(self):
        session = mock.Mock()
        session.make_request.return_value = self.response({"code": 100001})
        with self.assertRaisesRegex(module.FunctionalError, "permiso rechazado"):
            module.apply_unlock(session, "secret-token", "device")

    def test_ambiguous_apply_is_returned_for_follow_up_check(self):
        session = mock.Mock()
        session.make_request.return_value = self.response({"code": 100003})
        self.assertEqual(module.apply_unlock(session, "secret-token", "device"), "applied")

    def test_ambiguous_apply_follow_up_status_is_checked_by_main_flow(self):
        session = mock.Mock()
        session.make_request.side_effect = [
            self.response({"code": 100003}),
            self.response({"code": 0, "data": {"is_pass": 4, "button_state": 2,
                                                   "deadline_format": "09/01"}}),
        ]
        self.assertEqual(module.apply_unlock(session, "secret-token", "device"), "applied")
        with self.assertRaisesRegex(module.FunctionalError, "09/01"):
            module.check_unlock_status(session, "secret-token", "device")
        self.assertEqual(session.make_request.call_count, 2)

    def test_blocked_status_preserves_deadline_without_token(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"is_pass": 4, "button_state": 2, "deadline_format": "09/01"}}
        )
        with self.assertRaisesRegex(module.FunctionalError, "09/01") as caught:
            module.check_unlock_status(session, "secret-token", "device")
        self.assertNotIn("secret-token", str(caught.exception))

    def test_token_is_redacted_in_errors(self):
        output = io.StringIO()
        with redirect_stderr(output):
            result = module.main(
                ["--token", "secret-token", "--timeshift", "nan", "--job-id", "job-1"]
            )
        self.assertEqual(result, 20)
        self.assertNotIn("secret-token", output.getvalue())


class ArtifactTests(unittest.TestCase):
    class HTTP:
        Timeout = mock.Mock()

        def __init__(self, payload):
            self.payload = payload

        def PoolManager(self, **kwargs):
            response = mock.Mock()
            response.status = 200
            response.data = self.payload if isinstance(self.payload, bytes) else module.json.dumps(self.payload).encode()
            response.release_conn = mock.Mock()
            manager = mock.Mock()
            manager.request.return_value = response
            return manager

    class SequenceHTTP:
        Timeout = mock.Mock()

        def __init__(self, payloads, status=200):
            self.payloads = list(payloads)
            self.status = status

        def PoolManager(self, **kwargs):
            manager = mock.Mock()

            def request(*args, **kwargs):
                payload = self.payloads.pop(0)
                response = mock.Mock()
                response.status = self.status
                response.data = payload if isinstance(payload, bytes) else module.json.dumps(payload).encode()
                response.release_conn = mock.Mock()
                return response

            manager.request.side_effect = request
            return manager

    def run_job(self, payload, *extra):
        with tempfile.TemporaryDirectory() as work_dir:
            result = module.main(
                ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-1",
                 "--work-dir", work_dir, *extra],
                dependencies=(None, None, self.HTTP(payload)),
            )
            path = Path(work_dir) / "job-1"
            status = json.loads((path / "status.json").read_text())
            log = (path / "output.log").read_text()
            pid_exists = (path / "process.pid").exists()
            return result, status, log, pid_exists

    def test_success_persists_isolated_artifacts(self):
        result, status, log, pid_exists = self.run_job({"code": 0, "data": {"is_pass": 1}})
        self.assertEqual(result, 0)
        self.assertEqual(status["state"], "success")
        self.assertEqual(status["result"], "already_allowed")
        self.assertEqual(status["job_id"], "job-1")
        self.assertTrue(pid_exists)
        self.assertNotIn("secret-token", log)

    def test_functional_failure_is_persisted_without_secret(self):
        result, status, log, _ = self.run_job({"code": 100004})
        self.assertEqual(result, module.EXIT_FUNCTIONAL)
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["exit_code"], module.EXIT_FUNCTIONAL)
        self.assertNotIn("secret-token", json.dumps(status) + log)

    def test_expired_token_returns_10_from_main(self):
        result, status, log, _ = self.run_job({"code": 100004})
        self.assertEqual(result, module.EXIT_FUNCTIONAL)
        self.assertEqual(status["error"], "token caducado")
        self.assertNotIn("secret-token", log)

    def test_unknown_state_returns_30_from_main(self):
        result, status, _, _ = self.run_job({"code": 0, "data": {"is_pass": 4, "button_state": 99}})
        self.assertEqual(result, module.EXIT_SYSTEM)
        self.assertEqual(status["exit_code"], module.EXIT_SYSTEM)
        self.assertEqual(status["state"], "failed")

    def test_ambiguous_apply_is_followed_by_status_and_cannot_fake_success(self):
        with tempfile.TemporaryDirectory() as work_dir:
            dependencies = (mock.Mock(), mock.Mock(), self.SequenceHTTP([
                {"code": 0, "data": {"is_pass": 4, "button_state": 1}},
                {"code": 100003},
                {"code": 0, "data": {"is_pass": 4, "button_state": 2,
                                       "deadline_format": "09/01"}},
            ]))
            with mock.patch.object(module, "get_initial_beijing_time",
                                   return_value=module.datetime.now(module.timezone.utc)), \
                 mock.patch.object(module, "wait_until_target_time"):
                result = module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-ambiguous",
                     "--work-dir", work_dir], dependencies=dependencies)
            status = json.loads((Path(work_dir) / "job-ambiguous" / "status.json").read_text())
            self.assertEqual(result, module.EXIT_FUNCTIONAL)
            self.assertIn("09/01", status["error"])

    def test_applied_permission_returns_success_from_main(self):
        with tempfile.TemporaryDirectory() as work_dir:
            dependencies = (mock.Mock(), mock.Mock(), self.SequenceHTTP([
                {"code": 0, "data": {"is_pass": 4, "button_state": 1}},
                {"code": 0, "data": {"apply_result": 1}},
                {"code": 0, "data": {"is_pass": 4, "button_state": 1}},
            ]))
            with mock.patch.object(module, "get_initial_beijing_time",
                                   return_value=module.datetime.now(module.timezone.utc)), \
                 mock.patch.object(module, "wait_until_target_time"):
                result = module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-applied",
                     "--work-dir", work_dir], dependencies=dependencies)
            status = json.loads((Path(work_dir) / "job-applied" / "status.json").read_text())
            self.assertEqual(result, 0)
            self.assertEqual(status["result"], "applied")

    def test_invalid_json_returns_30(self):
        result, status, _, _ = self.run_job(b"not-json")
        self.assertEqual(result, module.EXIT_SYSTEM)
        self.assertEqual(status["exit_code"], module.EXIT_SYSTEM)

    def test_http_error_returns_30(self):
        with tempfile.TemporaryDirectory() as work_dir:
            result = module.main(
                ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-http",
                 "--work-dir", work_dir],
                dependencies=(None, None, self.SequenceHTTP([{}], status=503)),
            )
            status = json.loads((Path(work_dir) / "job-http" / "status.json").read_text())
            self.assertEqual(result, module.EXIT_SYSTEM)
            self.assertEqual(status["state"], "failed")

    def test_network_error_returns_30(self):
        class BrokenHTTP:
            Timeout = mock.Mock()

            def PoolManager(self, **kwargs):
                manager = mock.Mock()
                manager.request.side_effect = OSError("network unavailable")
                return manager

        with tempfile.TemporaryDirectory() as work_dir:
            result = module.main(
                ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-network",
                 "--work-dir", work_dir],
                dependencies=(None, None, BrokenHTTP()),
            )
            self.assertEqual(result, module.EXIT_SYSTEM)

    def test_two_jobs_can_run_concurrently_without_shared_artifacts(self):
        with tempfile.TemporaryDirectory() as work_dir:
            def run(job_id):
                return module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", job_id,
                     "--work-dir", work_dir],
                    dependencies=(None, None, self.HTTP({"code": 0, "data": {"is_pass": 1}})),
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(run, ("job-concurrent-a", "job-concurrent-b")))
            self.assertEqual(results, [0, 0])
            for job_id in ("job-concurrent-a", "job-concurrent-b"):
                path = Path(work_dir) / job_id
                self.assertEqual(json.loads((path / "status.json").read_text())["state"], "success")
                self.assertNotIn("secret-token", (path / "output.log").read_text())

    def test_persistence_failure_cannot_produce_success(self):
        original = module.JobArtifacts.set_state

        def fail_success(artifacts, state, *args, **kwargs):
            if state == "success":
                raise module.JobError("disk full")
            return original(artifacts, state, *args, **kwargs)

        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch.object(module.JobArtifacts, "set_state", fail_success):
                result = module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-disk",
                     "--work-dir", work_dir],
                    dependencies=(None, None, self.HTTP({"code": 0, "data": {"is_pass": 1}})),
                )
            status = json.loads((Path(work_dir) / "job-disk" / "status.json").read_text())
            self.assertEqual(result, module.EXIT_SYSTEM)
            self.assertNotEqual(status["state"], "success")

    def test_timeout_is_persisted(self):
        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch.object(module, "wait_until_target_time",
                                   side_effect=module.JobTimeout("limit")), \
                 mock.patch.object(module, "get_initial_beijing_time",
                                   return_value=module.datetime.now(module.timezone.utc)):
                result = module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-timeout",
                     "--work-dir", work_dir],
                    dependencies=(mock.Mock(), mock.Mock(), self.HTTP(
                        {"code": 0, "data": {"is_pass": 4, "button_state": 1}})),
                )
            path = Path(work_dir) / "job-timeout"
            status = json.loads((path / "status.json").read_text())
            self.assertEqual(result, module.EXIT_TIMEOUT)
            self.assertEqual(status["state"], "timeout")
            self.assertEqual(status["exit_code"], module.EXIT_TIMEOUT)

    def test_existing_job_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as work_dir:
            Path(work_dir, "job-1").mkdir()
            result = module.main(
                ["--token", "secret-token", "--timeshift", "1", "--job-id", "job-1",
                 "--work-dir", work_dir],
                dependencies=(None, None, self.HTTP({})),
            )
            self.assertEqual(result, module.EXIT_SYSTEM)

    def test_two_jobs_do_not_share_artifacts(self):
        with tempfile.TemporaryDirectory() as work_dir:
            for job_id in ("job-a", "job-b"):
                result = module.main(
                    ["--token", "secret-token", "--timeshift", "1", "--job-id", job_id,
                     "--work-dir", work_dir],
                    dependencies=(None, None, self.HTTP({"code": 0, "data": {"is_pass": 1}})),
                )
                self.assertEqual(result, 0)
            self.assertNotEqual(
                (Path(work_dir) / "job-a" / "status.json").read_text(),
                (Path(work_dir) / "job-b" / "status.json").read_text(),
            )

    def test_invalid_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as work_dir:
            artifacts = module.JobArtifacts(work_dir, "job-1", "secret-token")
            artifacts.set_state("starting")
            artifacts.set_state("running")
            with self.assertRaises(module.JobError):
                artifacts.set_state("starting")


if __name__ == "__main__":
    unittest.main()
