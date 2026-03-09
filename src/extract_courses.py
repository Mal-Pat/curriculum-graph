'''
This file will make PDF's to a graph readable format -> JSON

DEPENDENCIES -  pymupdf pandas networkx

'''

import os
import fitz
import re
import json

PDF_FOLDER = "data/IISER_P_official_data/2026 January Semester/Course Contents"
OUTPUT_FILE = "data/processed/courses.json"


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text()

    return text


def parse_course(text):

    code = re.search(r'Course Code\s*(\w+)', text)
    title = re.search(r'Course title\s*(.*)', text)
    credits = re.search(r'Credit\s*(\d+)', text)
    prereq = re.search(r'Pre-requisites\s*(.*)', text)

    return {
        "course_code": code.group(1) if code else None,
        "title": title.group(1).strip() if title else None,
        "credits": int(credits.group(1)) if credits else None,
        "prerequisites": prereq.group(1).strip() if prereq else "None"
    }


def main():

    courses = []

    for file in os.listdir(PDF_FOLDER):

        if file.endswith(".pdf"):

            path = os.path.join(PDF_FOLDER, file)

            text = extract_text(path)

            course = parse_course(text)

            course["file"] = file

            courses.append(course)

            print(f"Extracted {course['course_code']}")

    os.makedirs("data/processed", exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(courses, f, indent=4)

    print("\nSaved courses to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()