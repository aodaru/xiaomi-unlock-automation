import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr
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

    def test_blocked_apply_preserves_deadline_without_token(self):
        session = mock.Mock()
        session.make_request.return_value = self.response(
            {"code": 0, "data": {"apply_result": 4, "deadline_format": "08/20"}}
        )
        with self.assertRaisesRegex(module.FunctionalError, "08/20") as caught:
            module.apply_unlock(session, "secret-token", "device")
        self.assertNotIn("secret-token", str(caught.exception))

    def test_ambiguous_apply_is_returned_for_follow_up_check(self):
        session = mock.Mock()
        session.make_request.return_value = self.response({"code": 100003})
        self.assertEqual(module.apply_unlock(session, "secret-token", "device"), "applied")

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
            response.data = module.json.dumps(self.payload).encode()
            response.release_conn = mock.Mock()
            manager = mock.Mock()
            manager.request.return_value = response
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
