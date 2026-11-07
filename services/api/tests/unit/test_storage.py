from pathlib import Path

import pytest

from qbank.core.storage import AlreadyExists, LocalDiskStorage, Missing, StorageError

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
