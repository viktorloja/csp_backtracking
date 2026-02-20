from __future__ import annotations

import os
import glob
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml


# -----------------------------
# Frontmatter parsing
# -----------------------------
def parse_frontmatter(markdown_text: str) -> Tuple[Dict[str, Any], str]:
    """
    Extract YAML frontmatter from a Markdown string.

    Returns:
      (frontmatter_dict, body_markdown)

    Accepts:
      ---
      key: value
      ...
      ---

    If no frontmatter is present, returns ({}, full_text).
    """
    text = markdown_text.lstrip()
    if not text.startswith("---"):
        return {}, markdown_text

    lines = text.splitlines()
    if len(lines) < 3:
        return {}, markdown_text

    # first line is '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # no closing fence
        return {}, markdown_text

    yaml_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    data = yaml.safe_load(yaml_block) or {}
    if not isinstance(data, dict):
        raise ValueError("Frontmatter YAML must parse to a dictionary/object.")

    return data, body


# -----------------------------
# Helpers
# -----------------------------
def _require(d: Dict[str, Any], key: str, file_path: str) -> Any:
    if key not in d or d[key] is None:
        raise ValueError(f"Missing required field '{key}' in {file_path}")
    return d[key]

def _as_int(v: Any, key: str, file_path: str) -> int:
    try:
        return int(v)
    except Exception:
        raise ValueError(f"Field '{key}' must be an int in {file_path} (got {v!r})")

def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    # allow comma-separated strings
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [v]


# -----------------------------
# Case / Barrister converters
# -----------------------------
def frontmatter_to_case(front: Dict[str, Any], body: str, file_path: str) -> Dict[str, Any]:
    """
    Convert frontmatter into your scheduler's case dict shape.

    Output fields (typical):
      {
        "name": str,
        "time": int,        # minutes from midnight
        "duration": int,    # minutes
        "location": str,
        "seniority": int,   # required seniority
        "case_type": str,
        "experience_required": [str...],
        "notes": str
      }
    """
    name = str(_require(front, "name", file_path))
    time_minutes = _as_int(_require(front, "time_minutes", file_path), "time_minutes", file_path)
    duration_minutes = _as_int(_require(front, "duration_minutes", file_path), "duration_minutes", file_path)
    location = str(_require(front, "location", file_path))
    seniority_required = _as_int(_require(front, "seniority_required", file_path), "seniority_required", file_path)

    case_type = str(front.get("case_type", "other"))
    subtype = front.get("subtype", None)
    court = front.get("court", None)

    experience_required = [str(x) for x in _as_list(front.get("experience_required"))]
    risk_level = front.get("risk_level", None)

    case = {
        "name": name,
        "time": time_minutes,
        "duration": duration_minutes,
        "location": location,
        "seniority": seniority_required,
        "type": case_type,
        "subtype": subtype,
        "court": court,
        "experience_required": experience_required,
        "risk_level": risk_level,
        # keep body as notes/description (optional)
        "notes": body.strip() if body else "",
        # keep raw path if useful for debugging
        "_source_file": file_path,
    }
    return case


def frontmatter_to_barrister(front: Dict[str, Any], body: str, file_path: str) -> Dict[str, Any]:
    """
    Convert frontmatter into your scheduler's barrister dict shape.

    Expected frontmatter fields:
      name: str
      seniority: int
      home: str (optional)
      schedule: (optional) list of blocks:
        - start_time: int (minutes)
          end_time: int (minutes)
          location: str

    Output:
      {
        "name": str,
        "seniority": int,
        "home": str,
        "schedule": [{"start_time":int,"end_time":int,"location":str}, ...],
        "expertise": [str...],
        "notes": str
      }
    """
    name = str(_require(front, "name", file_path))
    seniority = _as_int(_require(front, "seniority", file_path), "seniority", file_path)
    home = front.get("home", None)

    schedule_raw = front.get("schedule", []) or []
    if not isinstance(schedule_raw, list):
        raise ValueError(f"Field 'schedule' must be a list in {file_path}")

    schedule = []
    for idx, blk in enumerate(schedule_raw):
        if not isinstance(blk, dict):
            raise ValueError(f"schedule[{idx}] must be an object/dict in {file_path}")
        st = _as_int(_require(blk, "start_time", file_path), f"schedule[{idx}].start_time", file_path)
        en = _as_int(_require(blk, "end_time", file_path), f"schedule[{idx}].end_time", file_path)
        loc = str(_require(blk, "location", file_path))
        if en < st:
            raise ValueError(f"schedule[{idx}] end_time < start_time in {file_path}")
        schedule.append({"start_time": st, "end_time": en, "location": loc})

    # optional metadata
    expertise = [str(x) for x in _as_list(front.get("expertise"))]
    courts = [str(x) for x in _as_list(front.get("courts"))]
    locations = [str(x) for x in _as_list(front.get("locations"))]
    win_rate = front.get("win_rate", None)

    barrister = {
        "name": name,
        "seniority": seniority,
        "home": home,
        "schedule": schedule,
        "expertise": expertise,
        "courts": courts,
        "locations": locations,
        "winrate": win_rate,
        "notes": body.strip() if body else "",
        "_source_file": file_path,
    }
    return barrister


# -----------------------------
# Folder loaders
# -----------------------------
def load_markdown_file(path: str) -> Tuple[Dict[str, Any], str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    front, body = parse_frontmatter(text)
    return front, body

def load_cases_from_folder(folder: str) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(os.path.join(folder, "*.md")))
    cases = []
    for p in paths:
        front, body = load_markdown_file(p)
        cases.append(frontmatter_to_case(front, body, p))
    return cases

def load_barristers_from_folder(folder: str) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(os.path.join(folder, "*.md")))
    barrs = []
    for p in paths:
        front, body = load_markdown_file(p)
        barrs.append(frontmatter_to_barrister(front, body, p))
    return barrs


# -----------------------------
# Demo
# -----------------------------
if __name__ == "__main__":
    cases = load_cases_from_folder("data/cases")
    barristers = load_barristers_from_folder("data/barristers")
    print("Loaded cases:", len(cases))
    print("Loaded barristers:", len(barristers))
    print("First case:", cases[0] if cases else None)
    print("First barrister:", barristers[0] if barristers else None)
