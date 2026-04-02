"""Major/minor validation helpers.

This module validates a student's chosen courses against a major/minor rule set.
It supports:
- subject + program type (Major/Minor) criteria selection
- flat or nested pathways
- set-wise checks (A/B/D)
- total credits/courses checks
- prerequisite completeness checks
"""

from __future__ import annotations

from collections.abc import Iterable


def build_course_maps(all_courses: list[dict]) -> tuple[dict[str, int], dict[str, set[str]]]:
    """Build quick lookup maps from all_courses data."""
    credit_map: dict[str, int] = {}
    prereq_map: dict[str, set[str]] = {}

    for c in all_courses:
        code = c.get("course_code")
        if not code:
            continue
        credit_map[code] = int(c.get("credits", 0) or 0)
        prereq_map[code] = set(c.get("prerequisites", []))

    return credit_map, prereq_map


def normalize_pathway(pathway) -> list[str]:
    """Normalize pathway into a de-duplicated list of course codes.

    Accepts:
    - ["BI1113", "CH1113"]
    - [["BI1113"], ["CH1113", "PH1113"]]
    - {"semester_1": ["BI1113"], "semester_2": ["CH1113"]}
    """

    def _walk(value):
        if value is None:
            return
        if isinstance(value, str):
            yield value
            return
        if isinstance(value, dict):
            for item in value.values():
                yield from _walk(item)
            return
        if isinstance(value, Iterable):
            for item in value:
                yield from _walk(item)

    seen = set()
    result = []
    for code in _walk(pathway):
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result


def select_criteria(all_criteria: list[dict], subject: str, major_or_minor: str) -> dict:
    """Pick the criteria block matching subject and Major/Minor."""
    target_type = (major_or_minor or "").strip().lower()
    for criteria in all_criteria:
        metadata = criteria.get("program_metadata", {})
        if metadata.get("subject") != subject:
            continue
        if (metadata.get("major_or_minor", "").strip().lower()) == target_type:
            return criteria
    raise ValueError(f"No criteria found for subject='{subject}', type='{major_or_minor}'")

def validate_major_minor_pathway(pathway, criteria, course_credits_map):

    errors = []
    pathway_set = set(pathway)

    sets = criteria.get("requirements_by_set", {})

    #SET D: Compulsory must-haves
    set_d = sets.get("set_d")
    if set_d and set_d.get("compulsory_courses"):
        compulsory_list = set(set_d["compulsory_courses"])
        for course in compulsory_list:
            if course not in pathway_set:
                errors.append(f"Missing mandatory course: {course}")

    #SET A: Minimum Required (Choice-based)
    set_a = sets.get("set_a")
    if set_a:
        available_a = set(set_a.get("available_courses", []))
        taken_a = pathway_set.intersection(available_a)

        min_req = set_a.get("minimum_required_from_set", 0)
        if len(taken_a) < min_req:
            errors.append(
                f"Insufficient Set A courses. Need: {min_req}, Found: {len(taken_a)}"
            )

    #SET B: Maximum Allowed (Capped)
    set_b = sets.get("set_b")
    if set_b:
        available_b = set(set_b.get("available_courses", []))
        taken_b = pathway_set.intersection(available_b)

        max_allowed = set_b.get("maximum_allowed_from_set")
        if max_allowed is not None and len(taken_b) > max_allowed:
            errors.append(
                f"Exceeded Set B limit. Max: {max_allowed}, Found: {len(taken_b)}"
            )

    #SET C: Supplementary
    #No major constraints here

    #Overall Requirements
    #Course Number check
    overall = criteria.get("overall_requirements", {})
    min_courses = overall.get("minimum_total_courses")
    if min_courses is not None and len(pathway_set) < min_courses:
        errors.append(
            f"Total courses ({len(pathway_set)}) < minimum required ({min_courses})"
        )

    #Course credit check
    min_credits = overall.get("minimum_total_credits")
    total_credits = sum(course_credits_map.get(c, 0) for c in pathway_set)

    if min_credits is not None and total_credits < min_credits:
        errors.append(
            f"Total credits ({total_credits}) < minimum required ({min_credits})"
        )

    return {
        "is_valid": len(errors) == 0,
        "subject": criteria.get("program_metadata", {}).get("subject"),
        "type": criteria.get("program_metadata", {}).get("major_or_minor"),
        "errors": errors,
        "total_credits": total_credits,
        "total_courses": len(pathway_set),
    }


def validate_with_prerequisites(pathway, criteria, all_courses: list[dict]) -> dict:
    """End-to-end validation including prerequisite completeness."""
    course_credits_map, prereq_map = build_course_maps(all_courses)
    normalized_pathway = normalize_pathway(pathway)

    result = validate_major_minor_pathway(
        normalized_pathway,
        criteria,
        course_credits_map,
    )

    pathway_set = set(normalized_pathway)
    prereq_errors = []
    for code in pathway_set:
        for prereq in prereq_map.get(code, set()):
            if prereq not in pathway_set:
                prereq_errors.append(f"{code} is missing prerequisite {prereq}")

    if prereq_errors:
        result["is_valid"] = False
        result["errors"] = result.get("errors", []) + sorted(prereq_errors)

    return result