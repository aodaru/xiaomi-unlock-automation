import importlib.util
import io
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


if __name__ == "__main__":
    unittest.main()
