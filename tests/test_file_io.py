# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.

import os
import shutil
import tempfile
import unittest
import uuid
from contextlib import contextmanager
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

from iopath.common import file_io
from iopath.common.file_io import (
    HTTPURLHandler,
    LazyPath,
    OneDrivePathHandler,
    PathManager,
    PathManagerFactory,
    g_pathmgr,
    get_cache_dir,
)


# from iopath.common.event_logger import EventLogger


# @patch("iopath.common.event_logger.EventLogger.log_event", side_effect=log_event_mock)
class TestNativeIO(unittest.TestCase):

    _tmpdir: Optional[str] = None
    _filename: Optional[str] = None
    _tmpfile: Optional[str] = None
    _tmpfile_contents = "Hello, World"
    _pathmgr = PathManager()

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.mkdtemp()
        cls._filename = "test_file_for_iopath_with_a_really_uncommon_name.txt"
        # pyre-ignore
        with open(os.path.join(cls._tmpdir, cls._filename), "w") as f:
            cls._tmpfile = f.name
            f.write(cls._tmpfile_contents)
            f.flush()

    @classmethod
    def tearDownClass(cls) -> None:
        # Cleanup temp working dir.
        if cls._tmpdir is not None:
            shutil.rmtree(cls._tmpdir)  # type: ignore

    def run(self, result=None):
        with patch("iopath.common.event_logger.EventLogger.log_event"):
            super(TestNativeIO, self).run(result)

    def setUp(self) -> None:
        # Reset class variables set by methods before each test.
        self._pathmgr.set_cwd(None)
        self._pathmgr._native_path_handler._non_blocking_io_manager = None
        self._pathmgr._native_path_handler._non_blocking_io_executor = None
        self._pathmgr._async_handlers.clear()

    # @patch("iopath.common.event_logger.EventLogger.log_event")
    def log_event_mock(self, topic: Optional[str] = None):
        pass

    def test_open(self) -> None:
        # with patch("iopath.common.event_logger.EventLogger.log_event") as foo:
        # pyre-ignore
        with self._pathmgr.open(self._tmpfile, "r") as f:
            self.assertEqual(f.read(), self._tmpfile_contents)

    def test_factory_open(self) -> None:
        with g_pathmgr.open(self._tmpfile, "r") as f:
            self.assertEqual(f.read(), self._tmpfile_contents)

        _pathmgr = PathManagerFactory.get("test_pm")
        with _pathmgr.open(self._tmpfile, "r") as f:
            self.assertEqual(f.read(), self._tmpfile_contents)

        PathManagerFactory.remove("test_pm")

    def test_open_args(self) -> None:
        # with patch("iopath.common.event_logger.EventLogger.log_event") as foo:
        self._pathmgr.set_strict_kwargs_checking(True)
        f = self._pathmgr.open(
            self._tmpfile,  # type: ignore
            mode="r",
            buffering=1,
            encoding="UTF-8",
            errors="ignore",
            newline=None,
            closefd=True,
            opener=None,
        )
        f.close()

    def test_get_local_path(self) -> None:
        self.assertEqual(
            # pyre-ignore
            self._pathmgr.get_local_path(self._tmpfile),
            self._tmpfile,
        )

    def test_get_local_path_forced(self) -> None:
        self.assertEqual(
            # pyre-ignore
            self._pathmgr.get_local_path(self._tmpfile, force=True),
            self._tmpfile,
        )

    def test_exists(self) -> None:
        # pyre-ignore
        self.assertTrue(self._pathmgr.exists(self._tmpfile))
        # pyre-ignore
        fake_path = os.path.join(self._tmpdir, uuid.uuid4().hex)
        self.assertFalse(self._pathmgr.exists(fake_path))

    def test_isfile(self) -> None:
        self.assertTrue(self._pathmgr.isfile(self._tmpfile))  # pyre-ignore
        # This is a directory, not a file, so it should fail
        self.assertFalse(self._pathmgr.isfile(self._tmpdir))  # pyre-ignore
        # This is a non-existing path, so it should fail
        fake_path = os.path.join(self._tmpdir, uuid.uuid4().hex)  # pyre-ignore
        self.assertFalse(self._pathmgr.isfile(fake_path))

    def test_isdir(self) -> None:
        # pyre-ignore
        self.assertTrue(self._pathmgr.isdir(self._tmpdir))
        # This is a file, not a directory, so it should fail
        # pyre-ignore
        self.assertFalse(self._pathmgr.isdir(self._tmpfile))
        # This is a non-existing path, so it should fail
        # pyre-ignore
        fake_path = os.path.join(self._tmpdir, uuid.uuid4().hex)
        self.assertFalse(self._pathmgr.isdir(fake_path))

    def test_ls(self) -> None:
        # Create some files in the tempdir to ls out.
        root_dir = os.path.join(self._tmpdir, "ls")  # pyre-ignore
        os.makedirs(root_dir, exist_ok=True)
        files = sorted(["foo.txt", "bar.txt", "baz.txt"])
        for f in files:
            open(os.path.join(root_dir, f), "a").close()

        children = sorted(self._pathmgr.ls(root_dir))
        self.assertListEqual(children, files)

        # Cleanup the tempdir
        shutil.rmtree(root_dir)

    def test_mkdirs(self) -> None:
        # pyre-ignore
        new_dir_path = os.path.join(self._tmpdir, "new", "tmp", "dir")
        self.assertFalse(self._pathmgr.exists(new_dir_path))
        self._pathmgr.mkdirs(new_dir_path)
        self.assertTrue(self._pathmgr.exists(new_dir_path))

    def test_copy(self) -> None:
        _tmpfile_2 = self._tmpfile + "2"  # pyre-ignore
        _tmpfile_2_contents = "something else"
        with open(_tmpfile_2, "w") as f:
            f.write(_tmpfile_2_contents)
            f.flush()
        self.assertTrue(self._pathmgr.copy(self._tmpfile, _tmpfile_2, overwrite=True))
        with self._pathmgr.open(_tmpfile_2, "r") as f:
            self.assertEqual(f.read(), self._tmpfile_contents)

    def test_move(self) -> None:
        _tmpfile_2 = self._tmpfile + "2" + uuid.uuid4().hex  # pyre-ignore
        _tmpfile_3 = self._tmpfile + "3_" + uuid.uuid4().hex  # pyre-ignore
        _tmpfile_2_contents = "Hello Move"
        with open(_tmpfile_2, "w") as f:
            f.write(_tmpfile_2_contents)
            f.flush()
        # pyre-ignore
        self.assertTrue(self._pathmgr.mv(_tmpfile_2, _tmpfile_3))
        with self._pathmgr.open(_tmpfile_3, "r") as f:
            self.assertEqual(f.read(), _tmpfile_2_contents)
        self.assertFalse(self._pathmgr.exists(_tmpfile_2))
        self._pathmgr.rm(_tmpfile_3)

    def test_symlink(self) -> None:
        _symlink = self._tmpfile + "_symlink"  # pyre-ignore
        self.assertTrue(self._pathmgr.symlink(self._tmpfile, _symlink))  # pyre-ignore
        with self._pathmgr.open(_symlink) as f:
            self.assertEqual(f.read(), self._tmpfile_contents)
        self.assertEqual(os.readlink(_symlink), self._tmpfile)
        os.remove(_symlink)

    def test_rm(self) -> None:
        # pyre-ignore
        with open(os.path.join(self._tmpdir, "test_rm.txt"), "w") as f:
            rm_file = f.name
            f.write(self._tmpfile_contents)
            f.flush()
        self.assertTrue(self._pathmgr.exists(rm_file))
        self.assertTrue(self._pathmgr.isfile(rm_file))
        self._pathmgr.rm(rm_file)
        self.assertFalse(self._pathmgr.exists(rm_file))
        self.assertFalse(self._pathmgr.isfile(rm_file))

    def test_set_cwd(self) -> None:
        # File not found since cwd not set yet.
        self.assertFalse(self._pathmgr.isfile(self._filename))
        self.assertTrue(self._pathmgr.isfile(self._tmpfile))
        # Once cwd is set, relative file path works.
        self._pathmgr.set_cwd(self._tmpdir)
        self.assertTrue(self._pathmgr.isfile(self._filename))

        # Set cwd to None
        self._pathmgr.set_cwd(None)
        self.assertFalse(self._pathmgr.isfile(self._filename))
        self.assertTrue(self._pathmgr.isfile(self._tmpfile))

        # Set cwd to invalid path
        with self.assertRaises(ValueError):
            self._pathmgr.set_cwd("/nonexistent/path")

    def test_get_path_with_cwd(self) -> None:
        self._pathmgr.set_cwd(self._tmpdir)
        # Make sure _get_path_with_cwd() returns correctly.
        self.assertEqual(
            self._pathmgr._native_path_handler._get_path_with_cwd(self._filename),
            self._tmpfile,
        )
        self.assertEqual(
            self._pathmgr._native_path_handler._get_path_with_cwd("/abs.txt"),
            "/abs.txt",
        )

    def test_bad_args(self) -> None:
        # TODO (T58240718): Replace with dynamic checks
        with self.assertRaises(ValueError):
            self._pathmgr.copy(self._tmpfile, self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.exists(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.get_local_path(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.isdir(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.isfile(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.ls(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.mkdirs(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.open(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.opena(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.rm(self._tmpfile, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.set_cwd(self._tmpdir, foo="foo")  # type: ignore

        self._pathmgr.set_strict_kwargs_checking(False)

        self._pathmgr.copy(
            self._tmpfile, self._tmpfile + "2", foo="foo"  # type: ignore
        )
        self._pathmgr.exists(self._tmpfile, foo="foo")  # type: ignore
        self._pathmgr.get_local_path(self._tmpfile, foo="foo")  # type: ignore
        self._pathmgr.isdir(self._tmpfile, foo="foo")  # type: ignore
        self._pathmgr.isfile(self._tmpfile, foo="foo")  # type: ignore
        self._pathmgr.ls(self._tmpdir, foo="foo")  # type: ignore
        self._pathmgr.mkdirs(self._tmpdir, foo="foo")  # type: ignore
        f = self._pathmgr.open(self._tmpfile, foo="foo")  # type: ignore
        f.close()
        # pyre-ignore
        with open(os.path.join(self._tmpdir, "test_rm.txt"), "w") as f:
            rm_file = f.name
            f.write(self._tmpfile_contents)
            f.flush()
        self._pathmgr.rm(rm_file, foo="foo")  # type: ignore


class TestHTTPIO(unittest.TestCase):
    _remote_uri = "https://www.facebook.com"
    _filename = "facebook.html"
    _pathmgr = PathManager()

    def run(self, result=None):
        with patch("iopath.common.event_logger.EventLogger.log_event"):
            super(TestHTTPIO, self).run(result)

    @contextmanager
    def _patch_download(self) -> Generator[None, None, None]:
        def fake_download(url: str, dir: str, *, filename: str) -> str:
            dest = os.path.join(dir, filename)
            with open(dest, "w") as f:
                f.write("test")
            return dest

        with patch.object(
            file_io, "get_cache_dir", return_value=self._cache_dir
        ), patch.object(file_io, "download", side_effect=fake_download):
            yield

    @classmethod
    def setUpClass(cls) -> None:
        # Use a unique pid based cache directory name.
        pid = os.getpid()
        cls._cache_dir: str = os.path.join(get_cache_dir(), f"{__name__}_{pid}")
        cls._pathmgr.register_handler(HTTPURLHandler())
        if os.path.exists(cls._cache_dir):
            shutil.rmtree(cls._cache_dir)
        os.makedirs(cls._cache_dir, exist_ok=True)

    def test_get_local_path(self) -> None:
        with self._patch_download():
            local_path = self._pathmgr.get_local_path(self._remote_uri)
            self.assertTrue(os.path.exists(local_path))
            self.assertTrue(os.path.isfile(local_path))
            # Now get a copy with force set to True.
            local_path = self._pathmgr.get_local_path(self._remote_uri, force=True)
            self.assertTrue(os.path.exists(local_path))
            self.assertTrue(os.path.isfile(local_path))
            # Now get a copy with cache_dir set to a temporary directory.
            local_path = self._pathmgr.get_local_path(
                self._remote_uri, cache_dir=self._cache_dir
            )
            self.assertTrue(local_path.startswith(self._cache_dir))
            self.assertTrue(os.path.exists(local_path))
            self.assertTrue(os.path.isfile(local_path))

    def test_open(self) -> None:
        with self._patch_download():
            with self._pathmgr.open(self._remote_uri, "rb") as f:
                self.assertTrue(os.path.exists(f.name))
                self.assertTrue(os.path.isfile(f.name))
                self.assertTrue(f.read() != "")

    def test_open_writes(self) -> None:
        # HTTPURLHandler does not support writing, only reading.
        with self.assertRaises(AssertionError):
            with self._pathmgr.open(self._remote_uri, "w") as f:
                f.write("foobar")  # pyre-ignore

    def test_open_new_path_manager(self) -> None:
        with self._patch_download():
            path_manager = PathManager()
            with self.assertRaises(OSError):  # no handler registered
                f = path_manager.open(self._remote_uri, "rb")

            path_manager.register_handler(HTTPURLHandler())
            with path_manager.open(self._remote_uri, "rb") as f:
                self.assertTrue(os.path.isfile(f.name))
                self.assertTrue(f.read() != "")

    def test_bad_args(self) -> None:
        with self.assertRaises(NotImplementedError):
            self._pathmgr.copy(
                self._remote_uri, self._remote_uri, foo="foo"  # type: ignore
            )
        with self.assertRaises(NotImplementedError):
            self._pathmgr.exists(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.get_local_path(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.isdir(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.isfile(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.ls(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.mkdirs(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.open(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(ValueError):
            self._pathmgr.opena(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.rm(self._remote_uri, foo="foo")  # type: ignore
        with self.assertRaises(NotImplementedError):
            self._pathmgr.set_cwd(self._remote_uri, foo="foo")  # type: ignore

        self._pathmgr.set_strict_kwargs_checking(False)

        self._pathmgr.get_local_path(self._remote_uri, foo="foo")  # type: ignore
        f = self._pathmgr.open(self._remote_uri, foo="foo")  # type: ignore
        f.close()
        self._pathmgr.set_strict_kwargs_checking(True)

    def test_copy_across_handlers(self) -> None:
        with tempfile.NamedTemporaryFile(delete=True) as file:
            local_path = file.name
        with self._patch_download():
            self._pathmgr.copy(self._remote_uri, local_path)
            self.assertTrue(self._pathmgr.exists(local_path))

        self._pathmgr.rm(local_path)


class TestLazyPath(unittest.TestCase):
    _pathmgr = PathManager()

    def run(self, result=None):
        with patch("iopath.common.event_logger.EventLogger.log_event"):
            super(TestLazyPath, self).run(result)

    def test_materialize(self) -> None:
        f = MagicMock(return_value="test")
        x = LazyPath(f)
        f.assert_not_called()

        p = os.fspath(x)
        f.assert_called()
        self.assertEqual(p, "test")

        p = os.fspath(x)
        # should only be called once
        f.assert_called_once()
        self.assertEqual(p, "test")

    def test_join(self) -> None:
        f = MagicMock(return_value="test")
        x = LazyPath(f)
        p = os.path.join(x, "a.txt")
        f.assert_called_once()
        self.assertEqual(p, "test/a.txt")

    def test_getattr(self) -> None:
        x = LazyPath(lambda: "abc")
        with self.assertRaises(AttributeError):
            x.startswith("ab")
        _ = os.fspath(x)
        self.assertTrue(x.startswith("ab"))

    def test_PathManager(self) -> None:
        x = LazyPath(lambda: "./")
        output = self._pathmgr.ls(x)  # pyre-ignore
        output_gt = self._pathmgr.ls("./")
        self.assertEqual(sorted(output), sorted(output_gt))

    def test_getitem(self) -> None:
        x = LazyPath(lambda: "abc")
        with self.assertRaises(TypeError):
            x[0]
        _ = os.fspath(x)
        self.assertEqual(x[0], "a")


class TestOneDrive(unittest.TestCase):
    _url = "https://1drv.ms/u/s!Aus8VCZ_C_33gQbJsUPTIj3rQu99"

    def run(self, result=None):
        with patch("iopath.common.event_logger.EventLogger.log_event"):
            super(TestOneDrive, self).run(result)

    def test_one_drive_download(self) -> None:
        _direct_url = OneDrivePathHandler().create_one_drive_direct_download(self._url)
        _gt_url = (
            "https://api.onedrive.com/v1.0/shares/u!aHR0cHM6Ly8xZHJ2Lm1zL3UvcyFBd"
            + "XM4VkNaX0NfMzNnUWJKc1VQVElqM3JRdTk5/root/content"
        )
        self.assertEqual(_direct_url, _gt_url)
