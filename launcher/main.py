import argparse
import json
import logging
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from http.client import HTTPConnection, HTTPException
from logging.handlers import RotatingFileHandler
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import uvicorn
from app.core.config import Settings
from app.core.errors import Unavailable
from app.database.lock import DatabaseLock
from app.main import create_app

logger = logging.getLogger(__name__)
HEADLESS = False


def probe(instance: dict, require_healthy=False) -> bool:
    connection = None
    try:
        port = instance["port"]
        identity = instance["instance_id"]
        if type(port) is not int or not 1024 <= port <= 65535 or not isinstance(identity, str):
            return False
        # HTTPConnection never initializes HTTPS or reads system proxy/CA settings.
        # This endpoint is exclusively on our hardcoded loopback address.
        connection = HTTPConnection("127.0.0.1", port, timeout=0.7)
        connection.request("GET", "/api/health")
        response = connection.getresponse()
        return (not require_healthy or response.status == 200) and (
            response.getheader("X-SmartHome") == "SmartHome"
            and response.getheader("X-SmartHome-Instance") == identity
        )
    except (OSError, HTTPException, KeyError, ValueError, TypeError) as error:
        logger.debug("Local readiness probe failed: %s: %s", type(error).__name__, error)
        return False
    finally:
        if connection is not None:
            connection.close()


def read_instance(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def message(text: str):
    if os.name == "nt" and not HEADLESS:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "SmartHome", 0x10)
    else:
        logger.error("%s", text)
        if sys.stderr is not None:
            print(text, file=sys.stderr)


def configure_logging(settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        settings.data_dir / "SmartHome.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=settings.log_level.upper(),
        handlers=[handler],
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = sys.stdout


def run(settings: Settings, open_browser=True, ready_timeout=30) -> int:
    configure_logging(settings)
    instance_file = settings.data_dir / "instance.json"
    control = DatabaseLock(settings.data_dir / "launcher")
    instance = None
    listener = None
    ready = threading.Event()
    stop = threading.Event()
    thread = None
    try:
        try:
            control.acquire()
        except Unavailable:
            deadline = time.monotonic() + ready_timeout
            while time.monotonic() < deadline:
                active = read_instance(instance_file)
                if probe(active):
                    if open_browser:
                        webbrowser.open(f"http://127.0.0.1:{active['port']}/")
                    return 0
                time.sleep(0.15)
            message(
                "SmartHome уже запущен, но не отвечает. Проверьте SmartHome.log в каталоге данных."
            )
            return 1
        active = read_instance(instance_file)
        if probe(active):
            if open_browser:
                webbrowser.open(f"http://127.0.0.1:{active['port']}/")
            return 0
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        application = create_app(settings.model_copy(update={"port": port}))
        server = uvicorn.Server(
            uvicorn.Config(
                application,
                host="127.0.0.1",
                port=port,
                log_config=None,
                access_log=False,
                http="h11",
                ws="none",
                lifespan="on",
                loop="asyncio",
            )
        )
        application.state.shutdown_callback = lambda: setattr(server, "should_exit", True)
        instance = {
            "pid": os.getpid(),
            "port": port,
            "instance_id": application.state.instance_id,
        }
        temporary = settings.data_dir / f".instance-{secrets.token_hex(8)}.tmp"
        temporary.write_text(json.dumps(instance), encoding="utf-8")
        temporary.replace(instance_file)

        def wait_ready():
            deadline = time.monotonic() + ready_timeout
            while not stop.is_set() and time.monotonic() < deadline:
                if probe(instance, require_healthy=True):
                    ready.set()
                    if open_browser:
                        if not webbrowser.open(f"http://127.0.0.1:{port}/"):
                            message(f"Откройте SmartHome в браузере: http://127.0.0.1:{port}/")
                    return
                stop.wait(0.15)
            if not stop.is_set():
                message(
                    "Не удалось дождаться запуска SmartHome. "
                    "Подробности в SmartHome.log в каталоге данных."
                )
                server.should_exit = True

        thread = threading.Thread(target=wait_ready, name="SmartHome-ready", daemon=True)
        thread.start()
        server.run(sockets=[listener])
        return 0 if ready.is_set() else 1
    except Exception:
        logger.exception("Launcher failed")
        message(f"Не удалось запустить SmartHome. Журнал: {settings.data_dir / 'SmartHome.log'}")
        return 1
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=2)
        if listener is not None:
            listener.close()
        if instance and read_instance(instance_file).get("instance_id") == instance["instance_id"]:
            instance_file.unlink(missing_ok=True)
        control.release()


def main():
    global HEADLESS
    parser = argparse.ArgumentParser(description="SmartHome local desktop launcher")
    parser.add_argument("--no-browser", action="store_true", help="For automated release checks")
    parser.add_argument("--data-dir", type=Path, help="Absolute persistent data directory override")
    args = parser.parse_args()
    HEADLESS = args.no_browser
    try:
        settings = Settings(**({"data_dir": args.data_dir} if args.data_dir is not None else {}))
        return run(settings, not args.no_browser)
    except Exception:
        message("Некорректная конфигурация SmartHome. Проверьте .env и путь каталога данных.")
        return 1


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    raise SystemExit(main())
