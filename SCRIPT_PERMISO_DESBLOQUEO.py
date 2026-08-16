"""Consulta no interactiva del permiso de desbloqueo Xiaomi.

La interfaz de esta fase es exclusivamente CLI. Los artefactos persistentes
(status.json, output.log y process.pid) pertenecen a la Fase 3 y no se crean
en este módulo.
"""

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone

EXIT_FUNCTIONAL = 10
EXIT_CONFIGURATION = 20
EXIT_SYSTEM = 30
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


def wait_until_target_time(start_time, start_timestamp, timeshift_ms, sleep=time.sleep):
    target = (start_time + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(milliseconds=timeshift_ms)
    while True:
        current = start_time + timedelta(seconds=time.time() - start_timestamp)
        remaining = (target - current).total_seconds()
        if remaining <= 0:
            return
        sleep(min(1.0, remaining))


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
    return parser


def main(argv=None, dependencies=None):
    args = build_parser().parse_args(argv)
    try:
        token, timeshift, job_id = validate_arguments(args.token, args.timeshift, args.job_id)
    except ConfigurationError as exc:
        print(f"[configuración] {redact(exc, args.token)}", file=sys.stderr)
        return EXIT_CONFIGURATION

    try:
        import ntplib
        import pytz
        import urllib3
        deps = dependencies or (ntplib, pytz, urllib3)
        session = HTTP11Session(deps[2])
        device_id = generate_device_id()
        initial_status = check_unlock_status(session, token, device_id)
        if initial_status == "already_allowed":
            print(f"job_id={job_id}: permiso ya concedido")
            return 0
        start = get_initial_beijing_time(deps[0], deps[1])
        start_timestamp = time.time()
        wait_until_target_time(start, start_timestamp, timeshift)
        apply_unlock(session, token, device_id)
        # Se valida el estado final; un estado bloqueado nunca concede permiso.
        check_unlock_status(session, token, device_id)
        print(f"job_id={job_id}: permiso solicitado correctamente")
        return 0
    except FunctionalError as exc:
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_FUNCTIONAL
    except (ConfigurationError, RemoteError, Exception) as exc:
        print(f"job_id={job_id}: {redact(exc, token)}", file=sys.stderr)
        return EXIT_SYSTEM


if __name__ == "__main__":
    raise SystemExit(main())
