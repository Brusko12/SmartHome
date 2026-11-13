"""Exercise the real launcher/executable without depending on its Python environment."""

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import URLError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


def check(executable: Path):
    command = [sys.executable, str(executable)] if executable.suffix == ".py" else [str(executable)]
    with tempfile.TemporaryDirectory(prefix="SmartHome-release-check-") as temporary:
        data = Path(temporary) / "data"
        data.mkdir()
        env = {
            **os.environ,
            "SMARTHOME_DATA_DIR": str(data),
            "SMARTHOME_LOG_LEVEL": "debug",
            "PYTHONTZPATH": "",
        }
        for key in ("SMARTHOME_FRONTEND_DIR", "SMARTHOME_PORT", "SMARTHOME_BACKGROUND_TASKS"):
            env.pop(key, None)
        if executable.suffix != ".py":
            env["PATH"] = (
                str(Path(os.environ["SystemRoot"]) / "System32")
                if os.name == "nt"
                else "/usr/bin:/bin"
            )
            for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
                env.pop(key, None)
        jar = CookieJar()
        opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar))
        base = ""

        def request(path, method="GET", body=None):
            headers = {}
            payload = None
            if body is not None:
                payload = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
            csrf = next((c.value for c in jar if c.name == "smarthome_csrf"), None)
            if csrf:
                headers["X-CSRF-Token"] = csrf
            with opener.open(
                Request(base + path, data=payload, headers=headers, method=method), timeout=20
            ) as response:
                raw = response.read()
                return (
                    json.loads(raw)
                    if "application/json" in response.headers.get("content-type", "")
                    else raw
                )

        @contextmanager
        def running():
            nonlocal base
            log = data / "child.log"
            with log.open("ab") as output:
                process = subprocess.Popen(
                    command + ["--no-browser"], env=env, stdout=output, stderr=subprocess.STDOUT
                )
                try:
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise AssertionError(
                                f"Launcher exited early ({process.returncode}). See {log}."
                            )
                        try:
                            info = json.loads((data / "instance.json").read_text())
                            base = f"http://127.0.0.1:{info['port']}"
                            with opener.open(base + "/api/health", timeout=1) as response:
                                if (
                                    response.status == 200
                                    and response.headers.get("X-SmartHome-Instance")
                                    == info["instance_id"]
                                ):
                                    break
                        except (OSError, ValueError, URLError, KeyError):
                            pass
                        time.sleep(0.1)
                    else:
                        raise AssertionError("Server readiness timeout.")
                    yield process, info
                    process.wait(timeout=20)
                    assert process.returncode == 0, (
                        f"Launcher shutdown failed: {process.returncode}"
                    )
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)

        password = secrets.token_urlsafe(24)
        with running() as (first, info):
            html = request("/")
            assert b'<div id="root">' in html
            assert b"http://cdn" not in html and b"https://fonts" not in html
            request(
                "/api/auth/register",
                "POST",
                {
                    "username": "release-check",
                    "password": password,
                    "home_name": "Release check",
                    "timezone": "Asia/Yakutsk",
                },
            )
            rooms = request("/api/rooms")["items"]
            assert len(rooms) == 4
            lamp = request(
                "/api/devices",
                "POST",
                {"room_id": rooms[0]["id"], "name": "Persistent lamp", "device_type": "light"},
            )
            assert (
                request(
                    f"/api/devices/{lamp['id']}/command",
                    "POST",
                    {"command": "turn_on", "params": {}},
                )["values"]["power"]
                is True
            )
            second = subprocess.run(
                command + ["--no-browser"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=40,
            )
            assert second.returncode == 0, (
                f"Second launch failed ({second.returncode}): "
                f"{second.stdout.decode(errors='replace')[-2000:]}\n"
                f"{(data / 'SmartHome.log').read_text(errors='replace')[-6000:]}"
            )
            assert (
                first.poll() is None
                and json.loads((data / "instance.json").read_text())["instance_id"]
                == info["instance_id"]
            )
            status = request("/api/system/status")
            assert status["can_shutdown"] and status["database"]["integrity"] == "ok"
            assert Path(status["database"]["path"]).resolve() == (data / "smart_home.db").resolve()
            request("/api/system/shutdown", "POST", {})
        assert not (data / "instance.json").exists()
        jar.clear()
        with running():
            request("/api/auth/login", "POST", {"username": "release-check", "password": password})
            assert request(f"/api/devices/{lamp['id']}/state")["values"]["power"] is True
            request("/api/system/shutdown", "POST", {})
        return {
            "ok": True,
            "platform": sys.platform,
            "packaged": executable.suffix != ".py",
            "static_ui": True,
            "local_auth": True,
            "device_command": True,
            "second_launch_reused": True,
            "restart_preserved_state": True,
            "graceful_shutdown": True,
            "restricted_child_path": executable.suffix != ".py",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.executable.resolve())
    except Exception as error:
        result = {"ok": False, "error": str(error), "platform": sys.platform}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, indent=2))
        raise
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
