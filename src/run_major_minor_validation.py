"""Run major/minor validation from project JSON files.

Example:
python src/run_major_minor_validation.py \
  --subject Biology \
  --program Major \
  --pathway BI1113 BI1213 BI2113 BI2213 BI3134
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_major_minor import select_criteria, validate_with_prerequisites


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate major/minor pathway")
    parser.add_argument("--subject", required=True, help="e.g. Biology")
    parser.add_argument("--program", required=True, help="Major or Minor")
    parser.add_argument(
        "--requirements",
        default="data/IISER-P/major_minor_requirements.json",
        help="Path to major/minor requirements JSON",
    )
    parser.add_argument(
        "--courses",
        default="data/IISER-P/all_courses.json",
        help="Path to all_courses JSON",
    )
    parser.add_argument(
        "--pathway",
        nargs="+",
        required=True,
        help="List of course codes selected by student",
    )
    args = parser.parse_args()

    requirements_path = Path(args.requirements)
    courses_path = Path(args.courses)

    all_criteria = _load_json(requirements_path)
    all_courses = _load_json(courses_path).get("all_courses", [])

    criteria = select_criteria(all_criteria, args.subject, args.program)
    result = validate_with_prerequisites(args.pathway, criteria, all_courses)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
