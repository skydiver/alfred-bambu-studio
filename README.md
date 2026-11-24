# Bambu Recent

An [Alfred](https://www.alfredapp.com) workflow that lists the projects you
recently opened in Bambu Studio, with thumbnails, and opens them in one
keystroke.

## Requirements

- macOS with Alfred and the Powerpack (workflows need it)
- Bambu Studio installed at `/Applications/BambuStudio.app`
- `/usr/bin/python3`

## Install

```sh
make install
```

This packages `dist/Bambu-Recent.alfredworkflow` and opens it, and Alfred
shows its import dialog.

## Usage

Type `bambu` in Alfred. Keep typing to filter by file name or folder.

| Key | Action                              |
| --- | ----------------------------------- |
| ↵   | Open the project in Bambu Studio    |
| ⌘↵  | Reveal the file in Finder           |
| ⌥↵  | Copy the full path to the clipboard |
| ⇧   | Quick Look preview                  |

Projects on a volume that isn't mounted stay in the list, marked
_File not found (volume not mounted?)_. You can still copy their path
with ⌥↵.

## How it works

`bambu_recent.py` is a Script Filter that only uses the Python standard
library.

1. **Reads the recent list** from
   `~/Library/Application Support/BambuStudio/BambuStudio.conf`, a JSON file
   that has a `recent_projects` object keyed by `"001"`, `"002"`, and so on.
   Keys are sorted numerically, so `001` (most recent) comes first. The
   file is only ever read, never written: Bambu Studio rewrites it while
   it runs.
2. **Extracts thumbnails.** A `.3mf` project is a zip archive. The
   workflow takes `Auxiliaries/.thumbnails/thumbnail_small.png`, or falls
   back to `Metadata/plate_1.png`, and caches it at
   `$alfred_workflow_cache/thumbs/<sha1(path + mtime)>.png`. A modified
   project gets a new cache key, so its thumbnail refreshes. Projects with
   no thumbnail (for example `.stl` files) or a damaged archive show their
   Finder icon. The reason is logged to stderr, which you can see in
   Alfred's workflow debugger.
3. **Builds the results.** Each project becomes an Alfred `file` item, so
   Quick Look and Alfred's file actions work. Alfred learns your preferred
   results from each item's path.
4. **Reports problems.** A missing or unreadable config, or one without
   recent projects, shows a single explanatory item instead of failing.

Cached thumbnails are never deleted automatically. Use Alfred's workflow
cache folder to clear them.

## Development

```sh
make         # list the available targets
make test    # run the unit tests (fixtures only; the real config is never touched)
make dist    # package dist/Bambu-Recent.alfredworkflow
make clean   # remove dist/ and Python caches
```

## Icon

The workflow doesn't include an `icon.png` yet. When one is added to the
repository root, `make dist` packages it automatically.
