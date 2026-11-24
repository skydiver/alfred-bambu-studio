import contextlib
import io
import os
import tempfile
import unittest

from bambu_recent import ConfigError, load_recent
from tests.helpers import FIXTURES, write_config


class LoadRecentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_sorts_by_key_not_file_order(self):
        paths = load_recent(os.path.join(FIXTURES, "BambuStudio.conf"))
        self.assertEqual(
            paths,
            [
                "/Volumes/External/a.3mf",
                "/Users/example/Documents/b.3mf",
                "/Users/example/Documents/c.stl",
            ],
        )

    def test_numeric_key_order_beyond_999(self):
        conf = write_config(self.tmp, {"recent_projects": {"1000": "/late.3mf", "999": "/early.3mf"}})
        self.assertEqual(load_recent(conf), ["/early.3mf", "/late.3mf"])

    def test_missing_config_raises(self):
        with self.assertRaises(ConfigError) as ctx:
            load_recent(os.path.join(self.tmp, "nope.conf"))
        self.assertEqual(ctx.exception.title, "Bambu Studio config not found")

    def test_truncated_json_raises(self):
        conf = write_config(self.tmp, None, raw='{"recent_projects": {"001": "/a.3mf"')
        with self.assertRaises(ConfigError) as ctx:
            load_recent(conf)
        self.assertEqual(ctx.exception.title, "Can't read Bambu Studio config")
        self.assertTrue(ctx.exception.subtitle)

    def test_missing_key_raises(self):
        conf = write_config(self.tmp, {})
        with self.assertRaises(ConfigError) as ctx:
            load_recent(conf)
        self.assertEqual(ctx.exception.title, "No recent projects in Bambu Studio config")

    def test_wrong_type_raises(self):
        for value in (None, ["/a.3mf"]):
            with self.subTest(value=value):
                conf = write_config(self.tmp, {"recent_projects": value})
                with self.assertRaises(ConfigError) as ctx:
                    load_recent(conf)
                self.assertEqual(ctx.exception.title, "No recent projects in Bambu Studio config")

    def test_empty_returns_empty_list(self):
        conf = write_config(self.tmp, {"recent_projects": {}})
        self.assertEqual(load_recent(conf), [])

    def test_skips_non_string_values(self):
        conf = write_config(self.tmp, {"recent_projects": {"001": 5, "002": "/b.3mf", "003": ""}})
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            paths = load_recent(conf)
        self.assertEqual(paths, ["/b.3mf"])
        self.assertIn("001", stderr.getvalue())

    def test_dedupes_keeping_most_recent(self):
        conf = write_config(
            self.tmp, {"recent_projects": {"001": "/a.3mf", "002": "/b.3mf", "003": "/a.3mf"}}
        )
        self.assertEqual(load_recent(conf), ["/a.3mf", "/b.3mf"])


if __name__ == "__main__":
    unittest.main()
