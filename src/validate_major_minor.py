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


def _countable_course_pool(criteria: dict) -> set[str]:
    """Union of all courses that can contribute to requirement counting."""
    sets = criteria.get("requirements_by_set", {})
    pool: set[str] = set()

    set_a = sets.get("set_a") or {}
    pool.update(set_a.get("available_courses", []))

    set_b = sets.get("set_b") or {}
    pool.update(set_b.get("available_courses", []))

    set_c = sets.get("set_c") or {}
    pool.update(set_c.get("available_courses", []))

    set_d = sets.get("set_d") or {}
    pool.update(set_d.get("compulsory_courses", []))

    return pool


def validate_major_minor_pathway(pathway, criteria, course_credits_map):
    def _to_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    normalized_pathway = normalize_pathway(pathway)
    pathway_set = set(normalized_pathway)

    offered = criteria.get("is_offered", True)
    complete = criteria.get("is_complete", True)
    prereq_policy = criteria.get("prerequisites_policy", "strict")

    if not offered:
        return {
            "is_valid": False,
            "subject": criteria.get("program_metadata", {}).get("subject"),
            "type": criteria.get("program_metadata", {}).get("major_or_minor"),
            "errors": ["This subject does not currently offer the selected Major/Minor."],
            "total_credits": 0,
            "total_courses": 0,
            "counted_courses": [],
            "input_total_courses": 0,
            "input_total_credits": 0,
            "excluded_by_set_e": [],
            "set_breakdown": {},
            "is_offered": False,
            "is_complete": complete,
            "prerequisites_policy": prereq_policy,
            "warnings": [],
            "unknown_courses": [],
        }

    if not complete:
        return {
            "is_valid": False,
            "subject": criteria.get("program_metadata", {}).get("subject"),
            "type": criteria.get("program_metadata", {}).get("major_or_minor"),
            "errors": ["Criteria exists but is marked incomplete. Please finalize handbook rules first."],
            "total_credits": 0,
            "total_courses": 0,
            "counted_courses": [],
            "input_total_courses": 0,
            "input_total_credits": 0,
            "excluded_by_set_e": [],
            "set_breakdown": {},
            "is_offered": offered,
            "is_complete": False,
            "prerequisites_policy": prereq_policy,
            "warnings": [],
            "unknown_courses": [],
        }

    errors = []
    sets = criteria.get("requirements_by_set", {})

    set_a_rule = sets.get("set_a") or {}
    set_b_rule = sets.get("set_b") or {}
    set_c_rule = sets.get("set_c") or {}
    set_d_rule = sets.get("set_d") or {}
    set_e_rule = sets.get("set_e") or {}

    available_a = set(set_a_rule.get("available_courses", []) or [])
    available_b = set(set_b_rule.get("available_courses", []) or [])
    available_c = set(set_c_rule.get("available_courses", []) or [])
    compulsory_d = set(set_d_rule.get("compulsory_courses", []) or [])
    not_counted_e = set(set_e_rule.get("not_counted_courses", []) or [])

    taken_a = pathway_set.intersection(available_a)
    taken_b = pathway_set.intersection(available_b)
    taken_c = pathway_set.intersection(available_c)
    taken_d = pathway_set.intersection(compulsory_d)
    excluded_by_set_e = pathway_set.intersection(not_counted_e)

    countable_pool = _countable_course_pool(criteria)
    counted_pathway_set = pathway_set.intersection(countable_pool) if countable_pool else set(pathway_set)
    counted_after_set_e = counted_pathway_set.difference(excluded_by_set_e)

    input_total_credits = sum(_to_int(course_credits_map.get(c, 0), 0) for c in pathway_set)

    #SET D: Compulsory must-haves
    missing_d = sorted(compulsory_d.difference(pathway_set))
    if compulsory_d:
        for course in missing_d:
            errors.append(f"Missing mandatory course: {course}")

    #SET A: Minimum Required (Choice-based)
    min_req = _to_int(set_a_rule.get("minimum_required_from_set"), 0)
    if set_a_rule:
        if len(taken_a) < min_req:
            errors.append(
                f"Insufficient Set A courses. Need: {min_req}, Found: {len(taken_a)}"
            )

    #SET B: Maximum Allowed (Capped)
    raw_max_allowed = set_b_rule.get("maximum_allowed_from_set")
    max_allowed = _to_int(raw_max_allowed) if raw_max_allowed is not None else None
    if set_b_rule:
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
    if min_courses is not None:
        min_courses = _to_int(min_courses, 0)
    if min_courses is not None and len(counted_after_set_e) < min_courses:
        errors.append(
            f"Total counted courses ({len(counted_after_set_e)}) < minimum required ({min_courses})"
        )

    #Course credit check
    min_credits = overall.get("minimum_total_credits")
    if min_credits is not None:
        min_credits = _to_int(min_credits, 0)

    total_credits = sum(_to_int(course_credits_map.get(c, 0), 0) for c in counted_after_set_e)

    if min_credits is not None and total_credits < min_credits:
        errors.append(
            f"Total credits ({total_credits}) < minimum required ({min_credits})"
        )

    set_breakdown = {
        "set_a": {
            "is_configured": bool(set_a_rule),
            "is_satisfied": (len(taken_a) >= min_req) if set_a_rule else True,
            "required_min": min_req,
            "available_count": len(available_a),
            "taken_count": len(taken_a),
            "remaining_to_min": max(0, min_req - len(taken_a)),
            "taken_courses": sorted(taken_a),
            "not_selected_courses": sorted(available_a.difference(pathway_set)),
        },
        "set_b": {
            "is_configured": bool(set_b_rule),
            "is_satisfied": (len(taken_b) <= max_allowed) if max_allowed is not None else True,
            "allowed_max": max_allowed,
            "available_count": len(available_b),
            "taken_count": len(taken_b),
            "over_by": max(0, len(taken_b) - max_allowed) if max_allowed is not None else 0,
            "taken_courses": sorted(taken_b),
            "not_selected_courses": sorted(available_b.difference(pathway_set)),
        },
        "set_c": {
            "is_configured": bool(set_c_rule),
            "is_satisfied": True,
            "available_count": len(available_c),
            "taken_count": len(taken_c),
            "taken_courses": sorted(taken_c),
            "not_selected_courses": sorted(available_c.difference(pathway_set)),
        },
        "set_d": {
            "is_configured": bool(set_d_rule),
            "is_satisfied": len(missing_d) == 0,
            "required_count": len(compulsory_d),
            "taken_count": len(taken_d),
            "missing_required": missing_d,
            "taken_courses": sorted(taken_d),
        },
        "set_e": {
            "is_configured": bool(set_e_rule),
            "is_satisfied": len(excluded_by_set_e) == 0,
            "excluded_count": len(excluded_by_set_e),
            "excluded_courses": sorted(excluded_by_set_e),
        },
    }

    unknown_courses = sorted([code for code in pathway_set if code not in course_credits_map])

    return {
        "is_valid": len(errors) == 0,
        "subject": criteria.get("program_metadata", {}).get("subject"),
        "type": criteria.get("program_metadata", {}).get("major_or_minor"),
        "errors": errors,
        "total_credits": total_credits,
        "total_courses": len(counted_after_set_e),
        "counted_courses": sorted(counted_after_set_e),
        "input_total_courses": len(pathway_set),
        "input_total_credits": input_total_credits,
        "excluded_by_set_e": sorted(excluded_by_set_e),
        "set_breakdown": set_breakdown,
        "is_offered": offered,
        "is_complete": complete,
        "prerequisites_policy": prereq_policy,
        "warnings": [],
        "unknown_courses": unknown_courses,
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

    # If program is not offered or criteria is incomplete, return early.
    if not result.get("is_offered", True) or not result.get("is_complete", True):
        return result

    prereq_policy = result.get("prerequisites_policy", "strict")
    if prereq_policy == "off":
        return result

    pathway_set = set(normalized_pathway)
    prereq_errors = []
    for code in pathway_set:
        for prereq in prereq_map.get(code, set()):
            if prereq not in pathway_set:
                prereq_errors.append(f"{code} is missing prerequisite {prereq}")

    if prereq_errors:
        if prereq_policy == "strict":
            result["is_valid"] = False
            result["errors"] = result.get("errors", []) + sorted(prereq_errors)
        elif prereq_policy == "advisory":
            result["warnings"] = result.get("warnings", []) + sorted(prereq_errors)

    return result