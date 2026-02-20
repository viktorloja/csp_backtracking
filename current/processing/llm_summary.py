from __future__ import annotations

import os
import re
import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml


import os
print("CWD:", os.getcwd())

# Ollama config
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b"

# Utility functions
def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def safe_slug(name: str, max_len: int = 64) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:max_len] if name else "item"


def stable_hash(s: str, n: int = 8) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]


def minutes_from_time_str(s: str) -> Optional[int]:
    """
    Very small helper (optional).
    Accepts '10:30' -> 630, '9:00' -> 540.
    """
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh * 60 + mm


# Ollama client

def ollama_generate(model: str, prompt: str, *, temperature: float = 0.0, timeout: int = 180) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")


def extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Find the first JSON object in the model output.
    """
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found (no '{').")

    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                return json.loads(candidate)

    raise ValueError("Could not find a complete JSON object in output.")


def llm_json_with_repair(model: str, prompt: str) -> Dict[str, Any]:
    """
    Ask for JSON; if parse fails, do one repair pass.
    """
    raw = ollama_generate(model, prompt, temperature=0.0)
    try:
        return extract_first_json_object(raw)
    except Exception as e:
        repair_prompt = (
            "You returned invalid JSON.\n"
            "Fix it so it is valid JSON and matches the requested schema.\n"
            "Return ONLY a JSON object. No commentary.\n\n"
            f"ORIGINAL_PROMPT:\n{prompt}\n\n"
            f"MODEL_OUTPUT:\n{raw}\n\n"
            f"ERROR:\n{str(e)}\n"
        )
        raw2 = ollama_generate(model, repair_prompt, temperature=0.0)
        return extract_first_json_object(raw2)

# Prompts (JSON extraction)

CASE_SCHEMA = {
    "name": "string",
    "case_type": "criminal|civil|family|immigration|commercial|employment|other",
    "subtype": "string|null",
    "seniority_required": "int 1..5",
    "location": "string",
    "court": "string|null",
    "time_minutes": "int 0..1440|null",
    "duration_minutes": "int minutes|null",
    "experience_required": "list[str]",
    "risk_level": "low|medium|high|null",
    "summary": "string",
}

BARRISTER_SCHEMA = {
    "name": "string",
    "seniority": "int 1..5",
    "home": "string|null",
    "expertise": "list[str]",
    "schedule": "list[{start_time:int,end_time:int,location:string}]",
    "profile": "string",
}


def make_case_prompt(paragraph: str, default_name: str) -> str:
    return f"""
You are an information extraction system. Return ONLY one JSON object.

Schema (CaseInfo):
{json.dumps(CASE_SCHEMA, indent=2)}

Rules:
- If the case name is missing, use "{default_name}".
- time_minutes: minutes from midnight. If time like "10:30" appears, convert to minutes (630).
- duration_minutes: in minutes if possible.
- Keep experience_required as short skill tags (e.g. ["fraud","cross-examination"]).
- If unsure, use null or [] (do not hallucinate specifics).

Paragraph:
\"\"\"{paragraph}\"\"\"
""".strip()


def make_barrister_prompt(paragraph: str, default_name: str) -> str:
    return f"""
You are an information extraction system. Return ONLY one JSON object.

Schema (BarristerInfo):
{json.dumps(BARRISTER_SCHEMA, indent=2)}

Rules:
- If the barrister name is missing, use "{default_name}".
- schedule blocks must be minutes from midnight for start_time/end_time when possible.
- If no schedule given, use [].
- Keep expertise as short tags (e.g. ["criminal","fraud"]).
- If unsure, use null or [].

Paragraph:
\"\"\"{paragraph}\"\"\"
""".strip()

# Validation + normalization

VALID_CASE_TYPES = {"criminal", "civil", "family", "immigration", "commercial", "employment", "other"}
VALID_RISK = {"low", "medium", "high"}

def require_keys(d: Dict[str, Any], keys: List[str], context: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{context}: missing keys {missing}")

def clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        x = int(v)
    except Exception:
        return default
    return max(lo, min(hi, x))

def normalize_case(data: Dict[str, Any], source_path: str) -> Dict[str, Any]:
    require_keys(data, ["name", "case_type", "seniority_required", "location", "summary"], f"Case from {source_path}")

    case_type = str(data.get("case_type", "other")).lower().strip()
    if case_type not in VALID_CASE_TYPES:
        case_type = "other"

    risk = data.get("risk_level", None)
    if isinstance(risk, str):
        risk = risk.lower().strip()
        if risk not in VALID_RISK:
            risk = None

    # coerce ints
    seniority_required = clamp_int(data.get("seniority_required"), 1, 5, 1)
    time_minutes = data.get("time_minutes", None)
    if isinstance(time_minutes, str):
        tm = minutes_from_time_str(time_minutes)
        time_minutes = tm if tm is not None else None
    if time_minutes is not None:
        time_minutes = clamp_int(time_minutes, 0, 1440, 0)

    duration_minutes = data.get("duration_minutes", None)
    if duration_minutes is not None:
        duration_minutes = clamp_int(duration_minutes, 1, 12 * 60, 60)

    exp = data.get("experience_required", [])
    if not isinstance(exp, list):
        exp = []
    exp = [str(x).strip() for x in exp if str(x).strip()]

    out = {
        "name": str(data["name"]).strip(),
        "case_type": case_type,
        "subtype": data.get("subtype", None),
        "seniority_required": seniority_required,
        "location": str(data["location"]).strip(),
        "court": data.get("court", None),
        "time_minutes": time_minutes,
        "duration_minutes": duration_minutes,
        "experience_required": exp,
        "risk_level": risk,
        "summary": str(data["summary"]).strip(),
        "_source_file": source_path,
    }
    return out

def normalize_barrister(data: Dict[str, Any], source_path: str) -> Dict[str, Any]:
    require_keys(data, ["name", "seniority", "expertise", "schedule", "profile"], f"Barrister from {source_path}")

    seniority = clamp_int(data.get("seniority"), 1, 5, 1)

    expertise = data.get("expertise", [])
    if not isinstance(expertise, list):
        expertise = []
    expertise = [str(x).strip() for x in expertise if str(x).strip()]

    schedule = data.get("schedule", [])
    if not isinstance(schedule, list):
        schedule = []

    clean_sched = []
    for blk in schedule:
        if not isinstance(blk, dict):
            continue
        st = blk.get("start_time", None)
        en = blk.get("end_time", None)
        loc = blk.get("location", None)
        if isinstance(st, str):
            st = minutes_from_time_str(st)
        if isinstance(en, str):
            en = minutes_from_time_str(en)
        if st is None or en is None or loc is None:
            continue
        st = clamp_int(st, 0, 1440, 0)
        en = clamp_int(en, 0, 1440, st)
        if en < st:
            continue
        clean_sched.append({"start_time": st, "end_time": en, "location": str(loc).strip()})

    clean_sched.sort(key=lambda b: (b["start_time"], b["end_time"]))

    out = {
        "name": str(data["name"]).strip(),
        "seniority": seniority,
        "home": data.get("home", None),
        "expertise": expertise,
        "schedule": clean_sched,
        "profile": str(data.get("profile", "")).strip(),
        "_source_file": source_path,
    }
    return out

# Markdown writer (YAML frontmatter + body)

def dict_to_frontmatter_md(front: Dict[str, Any], body_md: str) -> str:
    front_clean = {k: v for k, v in front.items() if k != "_source_file"}
    yaml_text = yaml.safe_dump(front_clean, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{yaml_text}\n---\n\n{body_md.strip()}\n"

def write_case_md(case: Dict[str, Any], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    slug = safe_slug(case["name"])
    # disambiguate duplicates
    fname = f"{slug}_{stable_hash(case['_source_file'])}.md"

    front = {
        "name": case["name"],
        "case_type": case["case_type"],
        "subtype": case["subtype"],
        "seniority_required": case["seniority_required"],
        "time_minutes": case["time_minutes"],
        "duration_minutes": case["duration_minutes"],
        "location": case["location"],
        "court": case["court"],
        "experience_required": case["experience_required"],
        "risk_level": case["risk_level"],
    }
    body = f"## Summary\n{case['summary']}\n"
    md = dict_to_frontmatter_md(front, body)

    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path

def write_barrister_md(b: Dict[str, Any], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    slug = safe_slug(b["name"])
    fname = f"{slug}_{stable_hash(b['_source_file'])}.md"

    front = {
        "name": b["name"],
        "seniority": b["seniority"],
        "home": b["home"],
        "expertise": b["expertise"],
        "schedule": b["schedule"],
    }
    body = f"## Profile\n{b['profile']}\n"
    md = dict_to_frontmatter_md(front, body)

    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path

# Folder pipeline

def process_folder_txt_to_md(
    cases_txt_dir: str,
    barristers_txt_dir: str,
    out_cases_md_dir: str,
    out_barristers_md_dir: str,
    model: str = DEFAULT_MODEL,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Reads .txt files from the input folders, writes .md files with YAML frontmatter.
    Returns summary stats.
    """

    def list_txt(folder: str) -> List[str]:
        if not os.path.isdir(folder):
            return []
        return sorted(
            os.path.join(folder, fn)
            for fn in os.listdir(folder)
            if fn.lower().endswith(".txt")
        )

    case_paths = list_txt(cases_txt_dir)
    barr_paths = list_txt(barristers_txt_dir)

    if verbose:
        print(f"Found {len(case_paths)} case txt files in {cases_txt_dir}")
        print(f"Found {len(barr_paths)} barrister txt files in {barristers_txt_dir}")

    written_cases = []
    written_barrs = []
    errors = []

    # Cases
    for p in case_paths:
        try:
            text = read_text_file(p)
            default_name = os.path.splitext(os.path.basename(p))[0]
            prompt = make_case_prompt(text, default_name=default_name)
            raw = llm_json_with_repair(model, prompt)
            case = normalize_case(raw, p)
            out_path = write_case_md(case, out_cases_md_dir)
            written_cases.append(out_path)
            if verbose:
                print("Wrote case:", out_path)
        except Exception as e:
            errors.append(("case", p, str(e)))
            if verbose:
                print("ERROR case:", p, "->", e)

    # Barristers
    for p in barr_paths:
        try:
            text = read_text_file(p)
            default_name = os.path.splitext(os.path.basename(p))[0]
            prompt = make_barrister_prompt(text, default_name=default_name)
            raw = llm_json_with_repair(model, prompt)
            b = normalize_barrister(raw, p)
            out_path = write_barrister_md(b, out_barristers_md_dir)
            written_barrs.append(out_path)
            if verbose:
                print("Wrote barrister:", out_path)
        except Exception as e:
            errors.append(("barrister", p, str(e)))
            if verbose:
                print("ERROR barrister:", p, "->", e)

    return {
        "cases_written": len(written_cases),
        "barristers_written": len(written_barrs),
        "errors": errors,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Local LLM: TXT -> Markdown frontmatter files (cases + barristers)")
    ap.add_argument("--cases_txt", default="data/raw_cases_txt", help="Folder of case .txt files")
    ap.add_argument("--barristers_txt", default="data/raw_barristers_txt", help="Folder of barrister .txt files")
    ap.add_argument("--out_cases_md", default="data/cases", help="Output folder for case .md files")
    ap.add_argument("--out_barristers_md", default="data/barristers", help="Output folder for barrister .md files")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name (e.g. llama3.1:8b, mistral, qwen2.5:7b)")
    ap.add_argument("--quiet", action="store_true", help="Less logging")
    args = ap.parse_args()

    stats = process_folder_txt_to_md(
        cases_txt_dir=args.cases_txt,
        barristers_txt_dir=args.barristers_txt,
        out_cases_md_dir=args.out_cases_md,
        out_barristers_md_dir=args.out_barristers_md,
        model=args.model,
        verbose=(not args.quiet),
    )
    print("\nDone.")
    print("Cases written:", stats["cases_written"])
    print("Barristers written:", stats["barristers_written"])
    if stats["errors"]:
        print("Errors:")
        for kind, path, msg in stats["errors"]:
            print(f"  - {kind}: {path}: {msg}")