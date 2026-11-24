"""Alfred Script Filter that lists Bambu Studio's recently opened projects.

Reads Bambu Studio's config (read-only), extracts project thumbnails into the
workflow cache and prints Alfred Script Filter JSON to stdout.
"""

import hashlib
import json
import os
import sys
import tempfile
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Tuple

CONFIG_PATH = "~/Library/Application Support/BambuStudio/BambuStudio.conf"
RECENT_KEY = "recent_projects"
MISSING_SUBTITLE = "File not found (volume not mounted?)"
THUMBNAIL_ENTRIES = (
    "Auxiliaries/.thumbnails/thumbnail_small.png",
    "Metadata/plate_1.png",
)


class ConfigError(Exception):
    """The config can't provide a recent list; carries a user-facing message."""

    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__(title)
        self.title = title
        self.subtitle = subtitle


def log(message: str) -> None:
    """Write a diagnostic line to stderr (visible in Alfred's debugger)."""
    print("bambu_recent: " + message, file=sys.stderr)


def _key_order(key: str) -> Tuple[int, int, str]:
    """Sort numeric keys by value ("999" before "1000"), others after by text."""
    if key.isdigit():
        return (0, int(key), "")
    return (1, 0, key)


def _read_config(conf_path: str) -> dict:
    try:
        with open(conf_path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise ConfigError("Bambu Studio config not found", conf_path) from None
    except (OSError, ValueError) as exc:
        raise ConfigError("Can't read Bambu Studio config", str(exc)) from exc


def load_recent(conf_path: str) -> List[str]:
    """Return recent project paths, most recent first, without duplicates."""
    config = _read_config(conf_path)
    recent = config.get(RECENT_KEY) if isinstance(config, dict) else None
    if not isinstance(recent, dict):
        raise ConfigError(
            "No recent projects in Bambu Studio config",
            "The '{}' entry is missing or malformed".format(RECENT_KEY),
        )

    paths: List[str] = []
    for key in sorted(recent, key=_key_order):
        path = recent[key]
        if not isinstance(path, str) or not path:
            log("skipping malformed entry {!r}: {!r}".format(key, path))
            continue
        if path in paths:
            continue
        paths.append(path)
    return paths


def cache_key(path: str, mtime: float) -> str:
    """Cache file stem; changes whenever the project file is modified."""
    return hashlib.sha1((path + str(mtime)).encode("utf-8")).hexdigest()


def _read_thumbnail(path: str) -> Optional[bytes]:
    """Return the first available thumbnail's bytes, or None if there is none."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        for entry in THUMBNAIL_ENTRIES:
            if entry in names:
                return archive.read(entry)
    return None


def _write_atomically(target: str, data: bytes) -> None:
    """Write via a temp file in the same directory so readers never see a partial PNG."""
    directory = os.path.dirname(target)
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False)
    try:
        with handle:
            handle.write(data)
        os.replace(handle.name, target)
    except BaseException:
        os.unlink(handle.name)
        raise


def thumbnail_for(path: str, thumbs_dir: Optional[str]) -> Optional[str]:
    """Return a cached thumbnail PNG for a .3mf project, extracting it if needed."""
    if thumbs_dir is None:
        return None
    if not path.lower().endswith(".3mf"):
        return None
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return None

    target = os.path.join(thumbs_dir, cache_key(path, mtime) + ".png")
    if os.path.isfile(target):
        return target

    try:
        data = _read_thumbnail(path)
        if data is None:
            return None
        _write_atomically(target, data)
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, KeyError) as exc:
        log("thumbnail failed for {}: {}".format(path, exc))
        return None
    return target


def tildify(path: str, home: str) -> str:
    """Show `home` as "~" when `path` is inside it (on a path-component boundary)."""
    home = home.rstrip(os.sep)
    if not home:
        return path
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def display_folder(path: str, home: str) -> str:
    """Parent folder of `path`, with the home directory shown as "~"."""
    return tildify(os.path.dirname(path), home)


def error_item(title: str, subtitle: str) -> Dict[str, Any]:
    """A single non-actionable item explaining why there is nothing to show."""
    return {"title": title, "subtitle": subtitle, "valid": False}


def _missing_item(path: str, name: str, folder: str) -> Dict[str, Any]:
    return {
        "uid": path,
        "title": name,
        "subtitle": MISSING_SUBTITLE,
        "arg": path,
        # Plain "file" would make Alfred silently hide nonexistent files.
        "type": "file:skipcheck",
        "valid": False,
        "match": "{} {}".format(name, folder),
        "icon": {"type": "fileicon", "path": path},
        "mods": {
            "cmd": {"valid": False, "subtitle": MISSING_SUBTITLE},
            "alt": {"valid": True, "arg": path, "subtitle": "Copy path to clipboard"},
        },
    }


def to_alfred_item(path: str, thumbs_dir: Optional[str], home: str) -> Dict[str, Any]:
    """Build the Alfred Script Filter item for one recent project."""
    name = os.path.basename(path)
    folder = display_folder(path, home)
    if not os.path.exists(path):
        return _missing_item(path, name, folder)

    thumb = thumbnail_for(path, thumbs_dir)
    icon = {"path": thumb} if thumb else {"type": "fileicon", "path": path}
    return {
        "uid": path,
        "title": name,
        "subtitle": folder,
        "arg": path,
        "type": "file",
        "match": "{} {}".format(name, folder),
        "icon": icon,
        "mods": {
            "cmd": {"arg": path, "subtitle": "Reveal in Finder"},
            "alt": {"arg": path, "subtitle": "Copy path to clipboard"},
        },
    }


def build_response(conf_path: str, thumbs_dir: Optional[str], home: str) -> Dict[str, Any]:
    """Full Script Filter response: project items, or a single error item."""
    try:
        paths = load_recent(conf_path)
    except ConfigError as exc:
        return {"items": [error_item(exc.title, tildify(exc.subtitle, home))]}
    if not paths:
        return {"items": [error_item("No recent projects", "Open a project in Bambu Studio first")]}
    return {"items": [to_alfred_item(path, thumbs_dir, home) for path in paths]}


def main() -> int:
    home = os.path.expanduser("~")
    cache = os.environ.get("alfred_workflow_cache")
    thumbs_dir = os.path.join(cache, "thumbs") if cache else None
    response = build_response(os.path.expanduser(CONFIG_PATH), thumbs_dir, home)
    json.dump(response, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
