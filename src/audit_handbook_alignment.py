"""Audit major/minor requirements JSON against extracted handbook text.

This script performs two checks:
1. Key handbook statements exist in extracted text.
2. Generated JSON rules match expected constraints.

Usage:
  python src/audit_handbook_alignment.py \
    --handbook-text data/IISER-P/Major-Minor-Req/maj-min_extracted.txt \
    --requirements data/IISER-P/major_minor_requirements.json \
    --courses data/IISER-P/all_courses.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _entry_map(requirements: list[dict]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for r in requirements:
        md = r.get("program_metadata", {})
        key = (md.get("subject", ""), md.get("major_or_minor", ""))
        out[key] = r
    return out


def _assert_true(cond: bool, message: str, failures: list[str]) -> None:
    if not cond:
        failures.append(message)


def _countable_pool(entry: dict) -> set[str]:
    sets = entry.get("requirements_by_set", {})
    pool = set()
    for key in ["set_a", "set_b", "set_c"]:
        block = sets.get(key) or {}
        pool.update(block.get("available_courses", []))
    block_d = sets.get("set_d") or {}
    pool.update(block_d.get("compulsory_courses", []))
    return pool


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit handbook alignment")
    parser.add_argument("--handbook-text", required=True)
    parser.add_argument("--requirements", default="data/IISER-P/major_minor_requirements.json")
    parser.add_argument("--courses", default="data/IISER-P/all_courses.json")
    args = parser.parse_args()

    handbook_text = Path(args.handbook_text).read_text(encoding="utf-8").lower()
    requirements = _load_json(Path(args.requirements))
    all_courses = _load_json(Path(args.courses)).get("all_courses", [])

    course_by_code = {c.get("course_code"): c for c in all_courses if c.get("course_code")}
    by_key = _entry_map(requirements)
    failures: list[str] = []

    # Check handbook phrases exist in extracted text.
    required_phrases = [
        "major: at least 15 courses in biology",
        "minor: at least 8 courses in biology",
        "major: at least 18 courses in chemistry",
        "minor: at least 6 courses in chemistry",
        "major: a total of 15 courses",
        "minor: at least 6 theory courses in ecs",
        "major: not applicable",
        "minor: minimum 6 courses in hss",
        "major: minimum 15 courses in mathematics",
        "minor: minimum 8 courses in mathematics",
        "major: at least 18 courses in physics",
        "minor: at least 8 courses in physics",
    ]
    for phrase in required_phrases:
        _assert_true(phrase in handbook_text, f"Missing phrase in extracted text: {phrase}", failures)

    # Core expected values.
    expected = {
        ("Biology", "Major"): {"offered": True, "min_courses": 15},
        ("Biology", "Minor"): {"offered": True, "min_courses": 8},
        ("Chemistry", "Major"): {"offered": True, "min_courses": 18, "mandatory": 12},
        ("Chemistry", "Minor"): {"offered": True, "min_courses": 6},
        ("Data Science", "Major"): {"offered": False},
        ("Data Science", "Minor"): {"offered": False},
        ("Earth and Climate Science", "Major"): {"offered": True, "min_courses": 15, "mandatory": 3},
        ("Earth and Climate Science", "Minor"): {"offered": True, "min_courses": 6},
        ("Humanities and Social Sciences", "Major"): {"offered": False},
        ("Humanities and Social Sciences", "Minor"): {"offered": True, "min_courses": 6},
        ("Mathematics", "Major"): {"offered": True, "min_courses": 15, "mandatory": 9},
        ("Mathematics", "Minor"): {"offered": True, "min_courses": 8},
        ("Physics", "Major"): {"offered": True, "min_courses": 18, "mandatory": 14},
        ("Physics", "Minor"): {"offered": True, "min_courses": 8},
        ("Science Education", "Major"): {"offered": False},
        ("Science Education", "Minor"): {"offered": False},
    }

    for key, exp in expected.items():
        _assert_true(key in by_key, f"Missing requirement entry: {key}", failures)
        if key not in by_key:
            continue
        entry = by_key[key]
        md = entry.get("program_metadata", {})
        _assert_true(md.get("subject") == key[0], f"Wrong subject metadata for {key}", failures)
        _assert_true(md.get("major_or_minor") == key[1], f"Wrong program metadata for {key}", failures)

        if "offered" in exp:
            _assert_true(entry.get("is_offered") == exp["offered"], f"Offered mismatch for {key}", failures)
        if "min_courses" in exp:
            got = entry.get("overall_requirements", {}).get("minimum_total_courses")
            _assert_true(got == exp["min_courses"], f"minimum_total_courses mismatch for {key}: got {got}", failures)
        if "mandatory" in exp:
            got = len((entry.get("requirements_by_set", {}).get("set_d") or {}).get("compulsory_courses", []))
            _assert_true(got == exp["mandatory"], f"mandatory count mismatch for {key}: got {got}", failures)

    # Specific policy checks.
    biology_major = by_key[("Biology", "Major")]
    biology_set_a = biology_major.get("requirements_by_set", {}).get("set_a") or {}
    _assert_true(
        biology_set_a.get("minimum_required_from_set") == 8,
        "Biology major should require minimum 8 four-credit courses in set_a",
        failures,
    )
    for code in biology_set_a.get("available_courses", []):
        credits = int((course_by_code.get(code) or {}).get("credits", -1))
        _assert_true(credits == 4, f"Biology set_a course is not 4-credit: {code}", failures)

    chemistry_minor = by_key[("Chemistry", "Minor")]
    chem_set_b = chemistry_minor.get("requirements_by_set", {}).get("set_b") or {}
    _assert_true(chem_set_b.get("maximum_allowed_from_set") == 1, "Chemistry minor lab cap should be 1", failures)
    _assert_true(
        set(chem_set_b.get("available_courses", [])) == {"CH3163", "CH3253", "CH4153"},
        "Chemistry minor advanced lab list mismatch",
        failures,
    )

    ecs_major = by_key[("Earth and Climate Science", "Major")]
    ecs_set_b = ecs_major.get("requirements_by_set", {}).get("set_b") or {}
    ecs_set_b_courses = ecs_set_b.get("available_courses", [])
    _assert_true(ecs_set_b.get("maximum_allowed_from_set") == 1, "ECS major project cap should be 1", failures)
    for code in ecs_set_b_courses:
        kind = (course_by_code.get(code) or {}).get("kind")
        _assert_true(kind == "semester_project", f"ECS major set_b should contain only semester_project courses: {code}", failures)

    ecs_minor = by_key[("Earth and Climate Science", "Minor")]
    ecs_minor_pool = _countable_pool(ecs_minor)
    for code in ecs_minor_pool:
        kind = (course_by_code.get(code) or {}).get("kind")
        _assert_true(kind == "normal", f"ECS minor should contain only theory/normal courses: {code} ({kind})", failures)

    hss_minor = by_key[("Humanities and Social Sciences", "Minor")]
    hss_set_b = hss_minor.get("requirements_by_set", {}).get("set_b") or {}
    _assert_true(hss_set_b.get("maximum_allowed_from_set") == 1, "HSS minor project cap should be 1", failures)

    physics_minor = by_key[("Physics", "Minor")]
    _assert_true(
        physics_minor.get("prerequisites_policy") == "advisory",
        "Physics minor prerequisites_policy should be advisory",
        failures,
    )

    if failures:
        print("AUDIT_FAILED")
        for msg in failures:
            print(f"- {msg}")
        raise SystemExit(1)

    print("AUDIT_OK")
    print(f"entries={len(requirements)}")


if __name__ == "__main__":
    main()
