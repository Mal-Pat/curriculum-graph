"""
validate_major_minor.py

Validates whether a student's course pathway satisfies
the requirements for a given Major or Minor.

Inputs come from:
    - major_minor_requirements.json  → passed in as `criteria`
    - all_courses.json               → used to build `course_credits_map`
    - pathway                        → runtime input

Usage:
    course_credits_map = {c["course_code"]: c["credits"] for c in all_courses}
    result = validate_major_minor_pathway(pathway, criteria, course_credits_map)

# pathway (list[str]): Flat list of course codes.
# If the app passes a course tree instead, a flattening
# step will need to be added here.

"""

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