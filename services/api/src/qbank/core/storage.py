"""File storage behind one small interface (ADR-0012).

Callers use opaque keys such as ``org/<organization id>/image/<uuid>`` and never see a path. The
local implementation writes to a folder (a Docker volume); a cloud one (S3 or Google Cloud Storage)
can replace it without changing any caller. Files never change once written: ``put`` refuses a key
that exists, and a checksum is kept in the database by the caller.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

# A key is a few "/"-separated parts of letters, digits and "-". No dots, so no "..", and no empty
# part, so no absolute path or double slash.
_KEY = re.compile(r"[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+){1,5}")


class StorageError(Exception):
    """A file could not be stored or read."""


class AlreadyExists(StorageError):
    """The key is taken; stored files are never overwritten."""


class Missing(StorageError):
    """No file under this key."""


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def check_key(key: str) -> str:
    if not _KEY.fullmatch(key):
        raise StorageError("That is not a valid storage key.")
    return key


class LocalDiskStorage:
    """Stores each file as one file under a root folder."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / check_key(key)).resolve()
        if not path.is_relative_to(self._root):  # belt and braces: the key check already stops it
            raise StorageError("That is not a valid storage key.")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Written beside the target and then linked into place, so a reader never sees half a file
        # and an existing file is never replaced (os.link fails if the target exists).
        fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".part-")
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp, path)
            except FileExistsError as exc:
                raise AlreadyExists("A file with that key already exists.") from exc
        finally:
            temp.unlink(missing_ok=True)

    def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError as exc:
            raise Missing("No file with that key.") from exc

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
