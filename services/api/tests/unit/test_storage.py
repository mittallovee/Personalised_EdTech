# ruff: noqa: N803  (the fake mirrors boto3's own CamelCase argument names)
import io
from pathlib import Path
from typing import Any

import pytest

from qbank.core.config import AppEnv, Settings
from qbank.core.storage import (
    AlreadyExists,
    LocalDiskStorage,
    Missing,
    S3Storage,
    StorageError,
)

KEY = "org/6f1c2a9e-0000-4000-8000-000000000001/image/6f1c2a9e-0000-4000-8000-000000000002"


def test_a_stored_file_can_be_read_back(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path)
    storage.put(KEY, b"hello")
    assert storage.get(KEY) == b"hello"


def test_a_file_is_never_replaced(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path)
    storage.put(KEY, b"first")
    with pytest.raises(AlreadyExists):
        storage.put(KEY, b"second")
    assert storage.get(KEY) == b"first"


def test_no_half_written_file_is_left_beside_it(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path)
    storage.put(KEY, b"x")
    with pytest.raises(AlreadyExists):
        storage.put(KEY, b"y")
    names = [p.name for p in (tmp_path / KEY).parent.iterdir()]
    assert names == [KEY.rsplit("/", 1)[1]]


def test_a_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(Missing):
        LocalDiskStorage(tmp_path).get(KEY)


def test_delete_removes_the_file_and_is_harmless_twice(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path)
    storage.put(KEY, b"x")
    storage.delete(KEY)
    storage.delete(KEY)
    with pytest.raises(Missing):
        storage.get(KEY)


@pytest.mark.parametrize(
    "key",
    [
        "",
        "image",
        "../outside",
        "org/../../outside",
        "/etc/passwd",
        "org//image/x",
        "org/a/image/x/",
        "org/a b/image/x",
        "org/a.png/image/x",
        "org\\a\\image",
        "org/a/b/c/d/e/f/g",
    ],
)
def test_keys_that_could_leave_the_folder_are_refused(tmp_path: Path, key: str) -> None:
    storage = LocalDiskStorage(tmp_path)
    for call in (
        lambda: storage.put(key, b"x"),
        lambda: storage.get(key),
        lambda: storage.delete(key),
    ):
        with pytest.raises(StorageError):
            call()
    assert list(tmp_path.iterdir()) == []


class FakeS3:
    """An in-memory stand-in for the S3 client: the calls S3Storage makes, with S3's errors."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_with: str | None = None

    def _error(self, code: str) -> Exception:
        error = Exception(code)
        error.response = {"Error": {"Code": code}}  # type: ignore[attr-defined]
        return error

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, IfNoneMatch: str) -> None:
        assert Bucket == "bucket" and IfNoneMatch == "*", "never overwrites"
        if self.fail_with:
            raise self._error(self.fail_with)
        if Key in self.objects:
            raise self._error("PreconditionFailed")
        self.objects[Key] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.fail_with:
            raise self._error(self.fail_with)
        if Key not in self.objects:
            raise self._error("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        if self.fail_with:
            raise self._error(self.fail_with)
        self.objects.pop(Key, None)


def test_s3_keeps_the_same_promises_as_the_folder() -> None:
    client = FakeS3()
    storage = S3Storage("bucket", client=client)
    storage.put(KEY, b"first")
    assert storage.get(KEY) == b"first"
    with pytest.raises(AlreadyExists):
        storage.put(KEY, b"second")
    assert storage.get(KEY) == b"first"
    storage.delete(KEY)
    storage.delete(KEY)
    with pytest.raises(Missing):
        storage.get(KEY)


@pytest.mark.parametrize("key", ["../outside", "/etc/passwd", "org//image/x", "org/a.png/image/x"])
def test_s3_refuses_keys_before_any_call(key: str) -> None:
    client = FakeS3()
    storage = S3Storage("bucket", client=client)
    for call in (
        lambda: storage.put(key, b"x"),
        lambda: storage.get(key),
        lambda: storage.delete(key),
    ):
        with pytest.raises(StorageError):
            call()
    assert client.objects == {}


def test_s3_failures_become_storage_errors_not_missing_or_exists() -> None:
    client = FakeS3()
    storage = S3Storage("bucket", client=client)
    client.fail_with = "AccessDenied"
    for call in (
        lambda: storage.put(KEY, b"x"),
        lambda: storage.get(KEY),
        lambda: storage.delete(KEY),
    ):
        with pytest.raises(StorageError) as raised:
            call()
        assert not isinstance(raised.value, (Missing, AlreadyExists))


def test_settings_choose_the_backend_and_s3_needs_a_bucket() -> None:
    local = Settings(app_env=AppEnv.TEST, database_url="postgresql://x", storage_dir=Path("/x"))
    assert isinstance(local.storage(), LocalDiskStorage)
    with pytest.raises(ValueError, match="STORAGE_S3_BUCKET"):
        Settings(app_env=AppEnv.TEST, database_url="postgresql://x", storage_backend="s3")
    cloud = Settings(
        app_env=AppEnv.TEST,
        database_url="postgresql://x",
        storage_backend="s3",
        storage_s3_bucket="bucket",
        storage_s3_region="ap-south-1",
    )
    assert isinstance(cloud.storage(), S3Storage)  # builds a client; makes no request
