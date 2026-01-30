#!/usr/bin/env python3
"""
PS2 Title ID to Title Renamer (Current Directory, Windows Safe)

Scans the current directory for PS2 disc image files named by serial (e.g., SCUS-XXXXX).
Looks up the game title using SerialStation and renames the files to "Game Title.ext",
stripping out illegal Windows filename characters.
"""

import json
import re
import ssl
import os
from pathlib import Path
from urllib.request import Request, urlopen

# SerialStation API endpoint for PS2 titles (system UUID for PlayStation 2)
START_URL = (
    "https://api.serialstation.com/titles/"
    "?title_id_type=&title_id_number=&systems=b88ad131-ac80-458e-81a1-33ec9e75ea8a"
)

# Use the current directory
PS2_FOLDER = Path(os.getcwd())

def fetch_json(url: str) -> dict:
    """Fetch JSON data with basic headers and no SSL verification."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context()
    with urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

def pick_title(entry: dict) -> str:
    """Prefer English title if available, otherwise use default."""
    name_info = entry.get("name") or {}
    default_title = (name_info.get("default_value") or "").strip()
    for trans in (name_info.get("translations") or []):
        lang = (trans.get("language") or "").lower()
        title_val = (trans.get("value") or "").strip()
        if title_val and "english" in lang:
            return title_val
    return default_title

def build_ps2_title_mapping() -> dict:
    """Fetch and build a serial-to-title mapping from SerialStation."""
    mapping = {}
    seen_ids = set()
    url = START_URL
    print(f"Scanning PS2 ISOs in: {PS2_FOLDER}")
    while url:
        data = fetch_json(url)
        for entry in data.get("results", []):
            if "PlayStation 2" not in (entry.get("systems") or []):
                continue
            if (entry.get("content_type") or "").lower() != "game":
                continue
            t_type = (entry.get("title_id_type") or "").strip()
            t_num = (entry.get("title_id_number") or "").strip()
            if not (t_type and t_num):
                continue
            serial = f"{t_type}-{t_num}"
            if serial in seen_ids:
                continue
            title = pick_title(entry)
            if title:
                seen_ids.add(serial)
                mapping[serial] = title
        url = data.get("next")
    print(f"Found {len(mapping)} PS2 title mappings.")
    return mapping

def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in Windows filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def rename_ps2_files(mapping: dict):
    """Rename files in current directory based on serial-title mapping."""
    for file_path in PS2_FOLDER.iterdir():
        if not file_path.is_file():
            continue
        original_name = file_path.name
        base_name, ext = file_path.stem, file_path.suffix
        code = re.sub(r"\s*\(.*\)$", "", base_name)
        if not re.match(r"^[A-Z]{4}-\d{5}$", code):
            continue
        if code in mapping:
            raw_title = mapping[code]
            clean_title = sanitize_filename(raw_title)
            new_name = f"{clean_title}{ext}"
            new_path = file_path.with_name(new_name)
            try:
                file_path.rename(new_path)
                print(f'Renamed: "{original_name}" → "{new_name}"')
            except Exception as e:
                print(f'Error renaming "{original_name}": {e}')
        else:
            print(f'Serial code "{code}" not found; skipping "{original_name}".')

def main():
    mapping = build_ps2_title_mapping()
    rename_ps2_files(mapping)

if __name__ == "__main__":
    main()
