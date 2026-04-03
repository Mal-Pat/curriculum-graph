"""Build major/minor requirement JSON from handbook rules + course catalog.

This keeps the final JSON maintainable:
- Course lists are derived from all_courses.json
- Handbook numbers/mandatory lists are defined once here
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _first_semester(course: dict) -> int:
    semesters = course.get("semesters", [])
    return min(semesters) if semesters else 99


def _subject_codes(
    all_courses: list[dict],
    subject: str,
    *,
    min_semester: int = 4,
    min_credits: int | None = None,
    max_credits: int | None = None,
    include_kinds: set[str] | None = None,
    exclude_kinds: set[str] | None = None,
    exclude_codes: set[str] | None = None,
) -> list[str]:
    codes = []
    for c in all_courses:
        if c.get("subject") != subject:
            continue
        if _first_semester(c) < min_semester:
            continue

        credits = int(c.get("credits", 0) or 0)
        if min_credits is not None and credits < min_credits:
            continue
        if max_credits is not None and credits > max_credits:
            continue

        kind = c.get("kind", "normal")
        if include_kinds and kind not in include_kinds:
            continue
        if exclude_kinds and kind in exclude_kinds:
            continue

        code = c.get("course_code")
        if not code:
            continue
        if exclude_codes and code in exclude_codes:
            continue
        codes.append(code)

    return sorted(set(codes))


def _set_a(minimum: int, courses: list[str]) -> dict:
    return {
        "minimum_required_from_set": minimum,
        "available_courses": sorted(set(courses)),
    }


def _set_b(maximum: int, courses: list[str]) -> dict:
    return {
        "maximum_allowed_from_set": maximum,
        "available_courses": sorted(set(courses)),
    }


def _set_c(courses: list[str]) -> dict:
    return {"available_courses": sorted(set(courses))}


def _set_d(courses: list[str]) -> dict:
    return {"compulsory_courses": sorted(set(courses))}


def _entry(
    subject: str,
    program: str,
    *,
    offered: bool,
    complete: bool,
    prerequisites_policy: str = "strict",
    min_courses: int | None,
    min_credits: int | None,
    set_a: dict | None,
    set_b: dict | None,
    set_c: dict | None,
    set_d: dict | None,
    notes: list[str] | None = None,
) -> dict:
    return {
        "program_metadata": {
            "subject": subject,
            "major_or_minor": program,
        },
        "is_offered": offered,
        "is_complete": complete,
        "prerequisites_policy": prerequisites_policy,
        "overall_requirements": {
            "minimum_total_courses": min_courses,
            "minimum_total_credits": min_credits,
        },
        "requirements_by_set": {
            "set_a": set_a,
            "set_b": set_b,
            "set_c": set_c,
            "set_d": set_d,
        },
        "notes": notes or [],
    }


def build_requirements(all_courses: list[dict]) -> list[dict]:
    requirements: list[dict] = []

    # Biology
    biology_pool = _subject_codes(all_courses, "Biology", min_semester=4)
    biology_four_credit_pool = _subject_codes(
        all_courses,
        "Biology",
        min_semester=4,
        min_credits=4,
        max_credits=4,
    )

    requirements.append(
        _entry(
            "Biology",
            "Major",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=15,
            min_credits=None,
            set_a=_set_a(8, biology_four_credit_pool),
            set_b=None,
            set_c=_set_c(biology_pool),
            set_d=None,
            notes=[
                "At least 15 Biology courses.",
                "At least 8 courses must be 4-credit Biology courses.",
                "Semester Project courses count toward major requirements.",
            ],
        )
    )
    requirements.append(
        _entry(
            "Biology",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=8,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(biology_pool),
            set_d=None,
            notes=[
                "At least 8 Biology courses from the approved list.",
                "Semester Project courses count toward minor requirements.",
            ],
        )
    )

    # Chemistry
    chemistry_pool = _subject_codes(
        all_courses,
        "Chemistry",
        min_semester=4,
        exclude_kinds={"semester_project"},
    )
    chemistry_major_mandatory = [
        "CH2213",
        "CH2223",
        "CH2233",
        "CH3114",
        "CH3124",
        "CH3154",
        "CH3163",
        "CH4153",
        "CH3214",
        "CH3224",
        "CH3234",
        "CH3253",
    ]
    chemistry_advanced_labs = ["CH3163", "CH3253", "CH4153"]

    requirements.append(
        _entry(
            "Chemistry",
            "Major",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=18,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(chemistry_pool),
            set_d=_set_d(chemistry_major_mandatory),
            notes=["At least 18 courses, of which 12 are mandatory."],
        )
    )
    requirements.append(
        _entry(
            "Chemistry",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=6,
            min_credits=None,
            set_a=None,
            set_b=_set_b(1, chemistry_advanced_labs),
            set_c=_set_c(chemistry_pool),
            set_d=None,
            notes=["At least 6 Chemistry courses; only one advanced lab can count."],
        )
    )

    # Data Science (not offered)
    for program in ["Major", "Minor"]:
        requirements.append(
            _entry(
                "Data Science",
                program,
                offered=False,
                complete=True,
                prerequisites_policy="off",
                min_courses=None,
                min_credits=None,
                set_a=None,
                set_b=None,
                set_c=None,
                set_d=None,
                notes=["Data Science currently does not offer a major or minor."],
            )
        )

    # Earth and Climate Science
    ec_pool = _subject_codes(all_courses, "Earth and Climate Science", min_semester=4)
    ec_project_courses = _subject_codes(
        all_courses,
        "Earth and Climate Science",
        min_semester=4,
        include_kinds={"semester_project"},
    )
    ec_minor_theory = _subject_codes(
        all_courses,
        "Earth and Climate Science",
        min_semester=4,
        exclude_kinds={"semester_project", "lab"},
        exclude_codes={"EC4243"},
    )
    ec_major_mandatory = ["EC2213", "EC3164", "EC3414"]

    requirements.append(
        _entry(
            "Earth and Climate Science",
            "Major",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=15,
            min_credits=None,
            set_a=None,
            set_b=_set_b(1, ec_project_courses),
            set_c=_set_c(ec_pool),
            set_d=_set_d(ec_major_mandatory),
            notes=["At most one semester project can count toward major."],
        )
    )
    requirements.append(
        _entry(
            "Earth and Climate Science",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=6,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(ec_minor_theory),
            set_d=None,
            notes=["Minor requires at least 6 theory ECS courses."],
        )
    )

    # Humanities and Social Sciences
    hss_pool = _subject_codes(all_courses, "Humanities and Social Sciences", min_semester=5)
    hss_projects = _subject_codes(
        all_courses,
        "Humanities and Social Sciences",
        min_semester=5,
        include_kinds={"semester_project"},
    )

    requirements.append(
        _entry(
            "Humanities and Social Sciences",
            "Major",
            offered=False,
            complete=True,
            prerequisites_policy="off",
            min_courses=None,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=None,
            set_d=None,
            notes=["HSS major is not applicable."],
        )
    )
    requirements.append(
        _entry(
            "Humanities and Social Sciences",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=6,
            min_credits=None,
            set_a=None,
            set_b=_set_b(1, hss_projects),
            set_c=_set_c(hss_pool),
            set_d=None,
            notes=["No more than one semester project can count for HSS minor."],
        )
    )

    # Mathematics
    mt_pool = _subject_codes(all_courses, "Mathematics", min_semester=4)
    mt_major_mandatory = [
        "MT2213",
        "MT2223",
        "MT2233",
        "MT3114",
        "MT3124",
        "MT3134",
        "MT3144",
        "MT3154",
        "MT3214",
    ]
    requirements.append(
        _entry(
            "Mathematics",
            "Major",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=15,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(mt_pool),
            set_d=_set_d(mt_major_mandatory),
            notes=["At least 15 Math courses; 9 mandatory."],
        )
    )
    requirements.append(
        _entry(
            "Mathematics",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=8,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(mt_pool),
            set_d=None,
            notes=["At least 8 Math courses."],
        )
    )

    # Physics
    ph_pool = _subject_codes(
        all_courses,
        "Physics",
        min_semester=4,
        exclude_kinds={"semester_project"},
    )
    ph_major_mandatory = [
        "PH2213",
        "PH2223",
        "PH2233",
        "PH3114",
        "PH3124",
        "PH3134",
        "PH3144",
        "PH4144",
        "PH4154",
        "PH3214",
        "PH3224",
        "PH3234",
        "PH3244",
        "PH4224",
    ]
    requirements.append(
        _entry(
            "Physics",
            "Major",
            offered=True,
            complete=True,
            prerequisites_policy="strict",
            min_courses=18,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(ph_pool),
            set_d=_set_d(ph_major_mandatory),
            notes=["At least 18 Physics courses; 14 mandatory. Semester projects do not count."],
        )
    )
    requirements.append(
        _entry(
            "Physics",
            "Minor",
            offered=True,
            complete=True,
            prerequisites_policy="advisory",
            min_courses=8,
            min_credits=None,
            set_a=None,
            set_b=None,
            set_c=_set_c(ph_pool),
            set_d=None,
            notes=["At least 8 Physics courses. Semester projects do not count."],
        )
    )

    # Science Education (not offered)
    for program in ["Major", "Minor"]:
        requirements.append(
            _entry(
                "Science Education",
                program,
                offered=False,
                complete=True,
                prerequisites_policy="off",
                min_courses=None,
                min_credits=None,
                set_a=None,
                set_b=None,
                set_c=None,
                set_d=None,
                notes=["Science Education currently does not offer a major or minor."],
            )
        )

    return requirements


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate major/minor requirements JSON")
    parser.add_argument(
        "--courses",
        default="data/IISER-P/all_courses.json",
        help="Path to all_courses.json",
    )
    parser.add_argument(
        "--out",
        default="data/IISER-P/major_minor_requirements.json",
        help="Path to write major_minor_requirements.json",
    )
    args = parser.parse_args()

    with open(args.courses, "r", encoding="utf-8") as f:
        all_courses = json.load(f).get("all_courses", [])

    requirements = build_requirements(all_courses)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(requirements, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(requirements)} requirement entries to {out_path}")


if __name__ == "__main__":
    main()
