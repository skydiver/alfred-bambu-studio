import json
import os
import subprocess
import sys
import tempfile
import unittest

from bambu_recent import (
    MISSING_SUBTITLE,
    THUMBNAIL_ENTRIES,
    build_response,
    display_folder,
    error_item,
    to_alfred_item,
)
from tests.helpers import make_3mf, write_config

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DisplayFolderTests(unittest.TestCase):
    def test_display_folder_tilde(self):
        self.assertEqual(display_folder("/Users/example/Docs/a.3mf", "/Users/example"), "~/Docs")

    def test_display_folder_home_itself(self):
        self.assertEqual(display_folder("/Users/example/a.3mf", "/Users/example"), "~")

    def test_display_folder_no_false_prefix(self):
        self.assertEqual(
            display_folder("/Users/examplex/a.3mf", "/Users/example"), "/Users/examplex"
        )

    def test_display_folder_external(self):
        self.assertEqual(
            display_folder("/Volumes/External/a.3mf", "/Users/example"), "/Volumes/External"
        )


class ItemTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(self._tmp.name)
        self.docs = os.path.join(self.home, "Docs")
        os.makedirs(self.docs)
        self.thumbs = os.path.join(self.home, "cache", "thumbs")

    def tearDown(self):
        self._tmp.cleanup()

    def test_existing_item_with_thumbnail(self):
        path = make_3mf(self.docs, "a.3mf", {THUMBNAIL_ENTRIES[0]: b"png"})
        item = to_alfred_item(path, self.thumbs, self.home)
        self.assertEqual(item["uid"], path)
        self.assertEqual(item["arg"], path)
        self.assertEqual(item["title"], "a.3mf")
        self.assertEqual(item["subtitle"], "~/Docs")
        self.assertEqual(item["type"], "file")
        self.assertTrue(item.get("valid", True))
        self.assertTrue(item["icon"]["path"].startswith(self.thumbs))
        self.assertNotIn("type", item["icon"])

    def test_existing_item_without_thumbnail(self):
        path = os.path.join(self.docs, "part.stl")
        open(path, "w").close()
        item = to_alfred_item(path, self.thumbs, self.home)
        self.assertEqual(item["icon"], {"type": "fileicon", "path": path})

    def test_existing_item_mods(self):
        path = os.path.join(self.docs, "part.stl")
        open(path, "w").close()
        mods = to_alfred_item(path, self.thumbs, self.home)["mods"]
        self.assertEqual(mods["cmd"]["arg"], path)
        self.assertEqual(mods["cmd"]["subtitle"], "Reveal in Finder")
        self.assertEqual(mods["alt"]["arg"], path)
        self.assertEqual(mods["alt"]["subtitle"], "Copy path to clipboard")

    def test_missing_item(self):
        path = os.path.join(self.home, "Gone", "b.3mf")
        item = to_alfred_item(path, self.thumbs, self.home)
        self.assertIs(item["valid"], False)
        self.assertEqual(item["subtitle"], MISSING_SUBTITLE)
        self.assertEqual(MISSING_SUBTITLE, "File not found (volume not mounted?)")
        self.assertEqual(item["type"], "file:skipcheck")
        self.assertEqual(item["icon"], {"type": "fileicon", "path": path})
        self.assertIs(item["mods"]["alt"]["valid"], True)
        self.assertIs(item["mods"]["cmd"]["valid"], False)
        self.assertEqual(item["match"], "b.3mf ~/Gone")
        self.assertFalse(os.path.exists(self.thumbs))

    def test_match_contains_name_and_folder(self):
        path = make_3mf(self.docs, "a.3mf", {})
        self.assertEqual(to_alfred_item(path, self.thumbs, self.home)["match"], "a.3mf ~/Docs")

    def test_unicode_and_parens_name(self):
        path = make_3mf(self.docs, "Café box (2).3mf", {})
        item = to_alfred_item(path, self.thumbs, self.home)
        self.assertEqual(item["title"], "Café box (2).3mf")
        self.assertEqual(item["uid"], path)
        self.assertEqual(json.loads(json.dumps(item)), item)

    def test_error_item(self):
        self.assertEqual(
            error_item("Title", "Sub"), {"title": "Title", "subtitle": "Sub", "valid": False}
        )


class BuildResponseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_response_error_item(self):
        response = build_response(os.path.join(self.tmp, "nope.conf"), None, self.tmp)
        self.assertEqual(len(response["items"]), 1)
        self.assertIs(response["items"][0]["valid"], False)
        self.assertEqual(response["items"][0]["title"], "Bambu Studio config not found")

    def test_build_response_empty(self):
        conf = write_config(self.tmp, {"recent_projects": {}})
        items = build_response(conf, None, self.tmp)["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "No recent projects")
        self.assertIs(items[0]["valid"], False)

    def test_build_response_order(self):
        paths = []
        for name in ("first.3mf", "second.stl", "third.3mf"):
            path = os.path.join(self.tmp, name)
            open(path, "w").close()
            paths.append(path)
        conf = write_config(
            self.tmp,
            {"recent_projects": {"003": paths[2], "001": paths[0], "002": paths[1]}},
        )
        items = build_response(conf, None, self.tmp)["items"]
        self.assertEqual([i["title"] for i in items], ["first.3mf", "second.stl", "third.3mf"])


class MainTests(unittest.TestCase):
    def test_main_outputs_json(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cache:
            env = {"HOME": home, "PATH": os.environ.get("PATH", ""), "alfred_workflow_cache": cache}
            result = subprocess.run(
                [sys.executable, os.path.join(REPO, "bambu_recent.py")],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
        items = json.loads(result.stdout)["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Bambu Studio config not found")
        self.assertTrue(items[0]["subtitle"].startswith("~/Library/Application Support/BambuStudio"))


if __name__ == "__main__":
    unittest.main()
