"""Shared test utilities."""

import json
import os
import zipfile
from typing import Dict

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def write_config(directory: str, data, raw: str = None) -> str:
    """Write a config file into `directory` and return its path."""
    path = os.path.join(directory, "BambuStudio.conf")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(raw if raw is not None else json.dumps(data))
    return path


def make_3mf(directory: str, name: str, entries: Dict[str, bytes]) -> str:
    """Create a zip-based .3mf file with the given entries and return its path."""
    path = os.path.join(directory, name)
    with zipfile.ZipFile(path, "w") as archive:
        for entry, payload in entries.items():
            archive.writestr(entry, payload)
    return path
