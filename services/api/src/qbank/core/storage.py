"""File storage behind one small interface (ADR-0012).

Callers use opaque keys such as ``org/<organization id>/image/<uuid>`` and never see a path. The
local implementation writes to a folder (a Docker volume); a cloud one (S3 or Google Cloud Storage)
can replace it without changing any caller (``S3Storage`` below). Files never change once written:
``put`` refuses a key that exists, and a checksum is kept in the database by the caller.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Protocol

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


class S3Storage:
    """Stores each file as one object in a private S3 bucket (ADR-0012, ADR-0025).

    Same promises as the local one: a key is checked first, a file is never replaced (S3's
    conditional write, ``If-None-Match: *``, refuses an existing key), and a missing key is reported
    as ``Missing``. The server's own role decides who may reach the bucket; no credentials are
    handled here, so boto3 finds them the usual way (the instance role). Objects are encrypted at
    rest by the bucket's own setting.
    """

    def __init__(self, bucket: str, region: str | None = None, client: Any = None) -> None:
        if client is None:
            import boto3  # only the cloud deployment needs it

            client = boto3.client("s3", region_name=region)
        self._bucket, self._client = bucket, client

    @staticmethod
    def _code(error: Exception) -> str:
        response = getattr(error, "response", None) or {}
        return str(response.get("Error", {}).get("Code", ""))

    def put(self, key: str, data: bytes) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=check_key(key), Body=data, IfNoneMatch="*"
            )
        except Exception as error:
            code = self._code(error)
            if code in ("PreconditionFailed", "ConditionalRequestConflict"):
                raise AlreadyExists("A file with that key already exists.") from error
            raise StorageError("The file could not be stored.") from error

    def get(self, key: str) -> bytes:
        try:
            body: bytes = self._client.get_object(Bucket=self._bucket, Key=check_key(key))[
                "Body"
            ].read()
        except Exception as error:
            if self._code(error) in ("NoSuchKey", "404"):
                raise Missing("No file with that key.") from error
            raise StorageError("The file could not be read.") from error
        return body

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=check_key(key))
        except Exception as error:
            raise StorageError("The file could not be deleted.") from error
