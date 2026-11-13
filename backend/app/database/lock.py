import os
from pathlib import Path

from app.core.errors import Unavailable


class DatabaseLock:
    """OS lock survives stale lockfiles and is released when a process exits."""

    def __init__(self, path: Path):
        self.path = path.with_suffix(path.suffix + ".lock")
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        if handle.seek(0, 2) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise Unavailable("Другой экземпляр SmartHome уже использует эту базу.") from error
        self.file = handle

    def release(self):
        if self.file is not None:
            self.file.close()
            self.file = None
