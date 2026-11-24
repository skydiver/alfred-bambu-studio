import contextlib
import io
import os
import tempfile
import unittest
import zipfile

from bambu_recent import THUMBNAIL_ENTRIES, cache_key, thumbnail_for
from tests.helpers import make_3mf

SMALL = THUMBNAIL_ENTRIES[0]
PLATE = THUMBNAIL_ENTRIES[1]


class ThumbnailTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.thumbs = os.path.join(self.tmp, "cache", "thumbs")
        self.stderr = io.StringIO()

    def tearDown(self):
        self._tmp.cleanup()

    def call(self, path, thumbs_dir=None):
        with contextlib.redirect_stderr(self.stderr):
            return thumbnail_for(path, self.thumbs if thumbs_dir is None else thumbs_dir)

    def read(self, path):
        with open(path, "rb") as handle:
            return handle.read()

    def test_entry_order(self):
        self.assertEqual(
            THUMBNAIL_ENTRIES,
            ("Auxiliaries/.thumbnails/thumbnail_small.png", "Metadata/plate_1.png"),
        )

    def test_prefers_thumbnail_small(self):
        path = make_3mf(self.tmp, "a.3mf", {SMALL: b"small", PLATE: b"plate"})
        thumb = self.call(path)
        self.assertEqual(self.read(thumb), b"small")
        expected = cache_key(path, os.stat(path).st_mtime) + ".png"
        self.assertEqual(os.path.basename(thumb), expected)
        self.assertEqual(os.path.dirname(thumb), self.thumbs)

    def test_falls_back_to_plate_1(self):
        path = make_3mf(self.tmp, "a.3mf", {PLATE: b"plate"})
        self.assertEqual(self.read(self.call(path)), b"plate")

    def test_no_thumbnail_returns_none(self):
        path = make_3mf(self.tmp, "a.3mf", {"3D/3dmodel.model": b"<model/>"})
        self.assertIsNone(self.call(path))
        self.assertEqual(self.stderr.getvalue(), "")

    def test_corrupt_zip_returns_none_and_logs(self):
        path = os.path.join(self.tmp, "broken.3mf")
        with open(path, "wb") as handle:
            handle.write(b"not a zip")
        self.assertIsNone(self.call(path))
        self.assertIn("thumbnail failed", self.stderr.getvalue())

    def test_corrupt_entry_returns_none_and_logs(self):
        payload = b"thumbnail-payload-0123456789"
        path = make_3mf(self.tmp, "a.3mf", {SMALL: payload})
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data.replace(payload, b"X" * len(payload)))
        self.assertIsNone(self.call(path))
        self.assertIn("thumbnail failed", self.stderr.getvalue())

    def test_corrupt_deflated_entry_returns_none_and_logs(self):
        path = os.path.join(self.tmp, "a.3mf")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(SMALL, os.urandom(4096))
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo(SMALL)
            start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        with open(path, "r+b") as handle:
            handle.seek(start)
            handle.write(b"\xff" * 64)
        self.assertIsNone(self.call(path))
        self.assertIn("thumbnail failed", self.stderr.getvalue())

    def test_stl_returns_none_without_reading(self):
        path = os.path.join(self.tmp, "part.stl")
        with open(path, "wb") as handle:
            handle.write(b"solid part")
        self.assertIsNone(self.call(path))
        self.assertEqual(self.stderr.getvalue(), "")

    def test_uppercase_extension_is_handled(self):
        path = make_3mf(self.tmp, "A.3MF", {SMALL: b"small"})
        self.assertEqual(self.read(self.call(path)), b"small")

    def test_cache_hit_skips_zip(self):
        path = make_3mf(self.tmp, "a.3mf", {SMALL: b"small"})
        first = self.call(path)
        mtime = os.stat(path).st_mtime
        with open(path, "wb") as handle:
            handle.write(b"junk")
        os.utime(path, (mtime, mtime))
        second = self.call(path)
        self.assertEqual(second, first)
        self.assertEqual(self.read(second), b"small")

    def test_mtime_change_new_thumbnail(self):
        path = make_3mf(self.tmp, "a.3mf", {SMALL: b"small"})
        first = self.call(path)
        later = os.stat(path).st_mtime + 60
        os.utime(path, (later, later))
        self.assertNotEqual(self.call(path), first)

    def test_no_cache_dir_returns_none(self):
        path = make_3mf(self.tmp, "a.3mf", {SMALL: b"small"})
        with contextlib.redirect_stderr(self.stderr):
            self.assertIsNone(thumbnail_for(path, None))

    def test_missing_file_returns_none(self):
        self.assertIsNone(self.call(os.path.join(self.tmp, "gone.3mf")))

    def test_unusable_cache_dir_falls_back(self):
        path = make_3mf(self.tmp, "a.3mf", {SMALL: b"small"})
        blocker = os.path.join(self.tmp, "blocker")
        with open(blocker, "w") as handle:
            handle.write("x")
        self.assertIsNone(self.call(path, thumbs_dir=blocker))
        self.assertIn("thumbnail failed", self.stderr.getvalue())

    def test_no_temp_files_left(self):
        os.makedirs(self.thumbs)
        path = os.path.join(self.tmp, "broken.3mf")
        with open(path, "wb") as handle:
            handle.write(b"not a zip")
        self.call(path)
        self.assertEqual(os.listdir(self.thumbs), [])


if __name__ == "__main__":
    unittest.main()
