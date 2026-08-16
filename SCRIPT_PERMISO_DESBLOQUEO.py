"""Consulta no interactiva del permiso de desbloqueo Xiaomi."""

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXIT_FUNCTIONAL = 10
EXIT_CONFIGURATION = 20
EXIT_SYSTEM = 30
EXIT_TIMEOUT = 40
DEFAULT_TIMEOUT_SECONDS = 26 * 60 * 60
TIMESHIFT_MIN_MS = 0
TIMESHIFT_MAX_MS = 86_400_000
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

NTP_SERVERS = [f"ntp{i}.ntp-servers.net" for i in range(7)]
APPLY_URL = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
STATE_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"


class ConfigurationError(ValueError):
    """Entrada o configuración inválida (código 20)."""


class FunctionalError(RuntimeError):
    """Respuesta válida que impide continuar (código 10)."""


class RemoteError(RuntimeError):
    """Red, HTTP, JSON o respuesta remota no reconocida (código 30)."""


class JobError(RuntimeError):
    """Error al crear o persistir los artefactos de un trabajo."""


class JobTimeout(TimeoutError):
    """El trabajo superó su límite operativo."""


def redact(value, token):
    """Redacta el secreto también cuando aparece dentro de una excepción."""
    text = str(value)
    return text.replace(token, "[REDACTED]") if token else text


def validate_arguments(token, timeshift, job_id):
    if not isinstance(token, str) or not token.strip() or any(ord(c) < 32 for c in token):
        raise ConfigurationError("token ausente o inválido (token=[REDACTED])")
    if not isinstance(job_id, str) or not JOB_ID_RE.fullmatch(job_id):
        raise ConfigurationError("job_id ausente o inseguro")
    try:
        shift = float(timeshift)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("timeshift debe ser un número finito en milisegundos") from exc
    if not math.isfinite(shift) or not TIMESHIFT_MIN_MS <= shift <= TIMESHIFT_MAX_MS:
        raise ConfigurationError(
            f"timeshift debe estar entre {TIMESHIFT_MIN_MS:g} y "
            f"{TIMESHIFT_MAX_MS:g} milisegundos"
        )
    return token, shift, job_id


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class JobArtifacts:
    """Persistencia aislada y atómica de un trabajo."""

    TRANSITIONS = {"starting": {"running", "failed"}, "running": {"success", "failed", "timeout"}}

    def __init__(self, root, job_id, token):
        self.token = token
        self.root = Path(root).expanduser().resolve()
        self.path = (self.root / job_id).resolve()
        if self.path.parent != self.root:
            raise JobError("ruta de trabajo inválida")
        try:
            self.path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise JobError("job_id ya existe") from exc
        except OSError as exc:
            raise JobError(f"no se pudo crear el directorio del trabajo: {exc}") from exc
        self.status_path = self.path / "status.json"
        self.log_path = self.path / "output.log"
        self.pid_path = self.path / "process.pid"
        self.status = None

    def _atomic_write(self, path, content):
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        try:
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
        except OSError as exc:
            raise JobError(f"no se pudo escribir {path.name}: {exc}") from exc

    def set_state(self, state, exit_code=None, result=None, error=None, timeout_at=None):
        if self.status is not None and state not in self.TRANSITIONS.get(self.status["state"], set()):
            raise JobError(f"transición inválida: {self.status['state']} -> {state}")
        now = utc_now()
        current = self.status or {}
        self.status = {
            "schema_version": 1,
            "job_id": current.get("job_id", self.path.name),
            "state": state,
            "exit_code": exit_code,
            "result": result,
            "error": redact(error, self.token) if error else None,
            "created_at": current.get("created_at", now),
            "started_at": current.get("started_at", now),
            "updated_at": now,
            "timeout_at": timeout_at if timeout_at is not None else current.get("timeout_at"),
            "finished_at": now if state in {"success", "failed", "timeout"} else None,
        }
        self._atomic_write(self.status_path, json.dumps(self.status, ensure_ascii=True, indent=2) + "\n")

    def write_pid(self):
        self._atomic_write(self.pid_path, f"{os.getpid()}\n")

    def log(self, message):
        try:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(redact(message, self.token).rstrip() + "\n")
        except OSError as exc:
            raise JobError(f"no se pudo escribir output.log: {exc}") from exc


def generate_device_id():
    return hashlib.sha1(f"{random.random()}-{time.time()}".encode()).hexdigest().upper()


def get_initial_beijing_time(ntplib_module, pytz_module):
    client = ntplib_module.NTPClient()
    beijing_tz = pytz_module.timezone("Asia/Shanghai")
    last_error = None
    for server in NTP_SERVERS:
        try:
            response = client.request(server, version=3)
            return datetime.fromtimestamp(response.tx_time, timezone.utc).astimezone(beijing_tz)
        except Exception as exc:  # NTP server failover is intentional.
            last_error = exc
    raise RemoteError(f"no se pudo sincronizar la hora: {last_error}")


def wait_until_target_time(start_time, start_timestamp, timeshift_ms, sleep=time.sleep,
                           timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, clock=time.time):
    target = (start_time + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(milliseconds=timeshift_ms)
    while True:
        elapsed = clock() - start_timestamp
        if elapsed >= timeout_seconds:
            raise JobTimeout("se alcanzó el límite operativo")
        current = start_time + timedelta(seconds=elapsed)
        remaining = (target - current).total_seconds()
        if remaining <= 0:
            return
        sleep(min(1.0, remaining, timeout_seconds - elapsed))


class HTTP11Session:
    def __init__(self, urllib3_module):
        self.http = urllib3_module.PoolManager(
            maxsize=10, retries=True,
            timeout=urllib3_module.Timeout(connect=2.0, read=15.0), headers={}
        )

    def make_request(self, method, url, headers=None, body=None):
        request_headers = dict(headers or {})
        request_headers["Content-Type"] = "application/json; charset=utf-8"
        if method == "POST":
            body = body if body is not None else b'{"is_retry":true}'
            request_headers.update({
                "Content-Length": str(len(body)), "Accept-Encoding": "gzip, deflate, br",
                "User-Agent": "okhttp/4.12.0", "Connection": "keep-alive",
            })
        try:
            response = self.http.request(method, url, headers=request_headers,
                                         body=body, preload_content=False)
            if getattr(response, "status", 200) >= 400:
                raise RemoteError(f"HTTP {response.status}")
            return response
        except RemoteError:
            raise
        except Exception as exc:
            raise RemoteError(f"error de red: {exc}") from exc


def decode_response(response, token):
    try:
        raw = response.data
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise RemoteError(f"JSON inválido: {redact(exc, token)}") from exc
    finally:
        release = getattr(response, "release_conn", None)
        if release:
            release()


def check_unlock_status(session, token, device_id):
    headers = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;"
                         f"versionName=5.4.11;deviceId={device_id};"}
    response = session.make_request("GET", STATE_URL, headers=headers)
    payload = decode_response(response, token)
    if payload.get("code") == 100004:
        raise FunctionalError("token caducado")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RemoteError("respuesta de estado desconocida")
    is_pass, button = data.get("is_pass"), data.get("button_state")
    if is_pass == 4 and button == 1:
        return "allowed"
    if is_pass == 4 and button in (2, 3):
        deadline = data.get("deadline_format") or "fecha no indicada"
        cause = "cuenta demasiado nueva" if button == 3 else "cuenta bloqueada"
        raise FunctionalError(f"{cause}; permiso rechazado hasta {deadline}")
    if is_pass == 1:
        return "already_allowed"
    raise RemoteError("estado de cuenta desconocido")


def apply_unlock(session, token, device_id):
    headers = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;"
                         f"versionName=5.4.11;deviceId={device_id};"}
    payload = decode_response(session.make_request("POST", APPLY_URL, headers=headers), token)
    code, data = payload.get("code"), payload.get("data")
    if code == 0 and isinstance(data, dict) and data.get("apply_result") == 1:
        return "applied"
    if code == 0 and isinstance(data, dict) and data.get("apply_result") in (3, 4):
        deadline = data.get("deadline_format") or "fecha no indicada"
        raise FunctionalError(f"solicitud bloqueada hasta {deadline}")
    if code == 100001:
        raise FunctionalError("permiso rechazado")
    if code == 100003:
        return "applied"
    raise RemoteError("respuesta de solicitud desconocida")


def build_parser():
    parser = argparse.ArgumentParser(description="Consulta no interactiva de permiso Xiaomi")
    parser.add_argument("--token", help="token de servicio (nunca se muestra)")
    parser.add_argument("--timeshift", help="desfase en milisegundos, entre 0 y 86400000")
    parser.add_argument("--job-id", dest="job_id", help="identificador seguro del trabajo")
    parser.add_argument("--work-dir", default="jobs", help="raíz de los artefactos por trabajo")
    parser.add_argument("--timeout-seconds", default=str(DEFAULT_TIMEOUT_SECONDS),
                        help="límite operativo en segundos")
    return parser


def validate_timeout(value):
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("timeout-seconds debe ser un número positivo") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ConfigurationError("timeout-seconds debe ser un número positivo")
    return timeout


def main(argv=None, dependencies=None):
    args = build_parser().parse_args(argv)
    try:
        token, timeshift, job_id = validate_arguments(args.token, args.timeshift, args.job_id)
        timeout_seconds = validate_timeout(args.timeout_seconds)
    except ConfigurationError as exc:
        print(f"[configuración] {redact(exc, args.token)}", file=sys.stderr)
        return EXIT_CONFIGURATION

    try:
        artifacts = JobArtifacts(args.work_dir, job_id, token)
        timeout_at = (datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)).isoformat(
            timespec="seconds").replace("+00:00", "Z")
        artifacts.set_state("starting", timeout_at=timeout_at)
        artifacts.write_pid()
        artifacts.log(f"job_id={job_id}: starting")
    except JobError as exc:
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_SYSTEM

    def finish(state, code, result=None, error=None):
        artifacts.log(f"job_id={job_id}: {result or error or state}")
        artifacts.set_state(state, exit_code=code, result=result, error=error)

    try:
        if dependencies is None:
            import ntplib
            import pytz
            import urllib3
            deps = (ntplib, pytz, urllib3)
        else:
            deps = dependencies
        session = HTTP11Session(deps[2])
        device_id = generate_device_id()
        artifacts.set_state("running", timeout_at=timeout_at)
        artifacts.log(f"job_id={job_id}: running")
        initial_status = check_unlock_status(session, token, device_id)
        if initial_status == "already_allowed":
            finish("success", 0, result="already_allowed")
            print(f"job_id={job_id}: permiso ya concedido")
            return 0
        start = get_initial_beijing_time(deps[0], deps[1])
        start_timestamp = time.time()
        wait_until_target_time(start, start_timestamp, timeshift, timeout_seconds=timeout_seconds)
        apply_unlock(session, token, device_id)
        # Se valida el estado final; un estado bloqueado nunca concede permiso.
        check_unlock_status(session, token, device_id)
        finish("success", 0, result="applied")
        print(f"job_id={job_id}: permiso solicitado correctamente")
        return 0
    except JobTimeout as exc:
        finish("timeout", EXIT_TIMEOUT, error=redact(exc, token))
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_TIMEOUT
    except FunctionalError as exc:
        finish("failed", EXIT_FUNCTIONAL, error=redact(exc, token))
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_FUNCTIONAL
    except (ConfigurationError, RemoteError, Exception) as exc:
        try:
            finish("failed", EXIT_SYSTEM, error=redact(exc, token))
        except JobError:
            pass
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_SYSTEM


if __name__ == "__main__":
    raise SystemExit(main())
