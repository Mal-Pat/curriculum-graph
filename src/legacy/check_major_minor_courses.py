import json

def extract_courses_from_requirement(requirement):
    courses = set()
    sets = requirement.get("requirements_by_set", {})

    # courses from set_a, set_b, set_c
    for set_name in ["set_a", "set_b", "set_c"]:
        current_set = sets.get(set_name)
        if current_set:
            courses.update(current_set.get("available_courses", []))

    # courses from set_d
    set_d = sets.get("set_d")
    if set_d:
        courses.update(set_d.get("compulsory_courses", []))

    # courses from set_e
    set_e = sets.get("set_e")
    if set_e:
        courses.update(set_e.get("not_counted_courses", []))

    return courses


def check_all_requirements(all_courses_data, requirements_data):
    all_course_codes = {
        course["course_code"]
        for course in all_courses_data["all_courses"]
    }

    missing_courses = set()

    for requirement in requirements_data:
        required_courses = extract_courses_from_requirement(requirement)
        missing_courses.update(required_courses - all_course_codes)

    return missing_courses


if __name__ == "__main__":

    with open("../data/IISER-P/all_courses.json", "r") as f:
      all_courses = json.load(f)

    with open("../data/IISER-P/major_minor_requirements.json", "r") as f:
      requirements = json.load(f)

    missing = check_all_requirements(all_courses, requirements)

    if missing:
        print("Missing courses:")
        for course in sorted(missing):
            print(course)
    else:
        print("All major/minor courses are present in all_courses.json")