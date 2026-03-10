"""
Extract IISER course information from PDFs and save as JSON
"""

import os
import re
import json
import fitz  # PyMuPDF


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PDF_FOLDER = "data/IISER_P_official_data/2026 January Semester/Course Contents"
OUTPUT_FILE = "data/processed/courses.json"


# --------------------------------------------------
# CLEAN TEXT
# --------------------------------------------------

def clean_text(text):
    """Remove PDF artifacts and extra spaces"""

    if not text:
        return None

    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'IISER Pune - Course Content', '', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# --------------------------------------------------
# EXTRACT TEXT FROM PDF
# --------------------------------------------------

def extract_text(pdf_path):
    """Read all text from a PDF"""

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text


# --------------------------------------------------
# EXTRACT SECTION BETWEEN HEADERS
# --------------------------------------------------

def extract_section(text, start, end):
    """Extract text between two headings"""

    pattern = start + r"(.*?)" + end

    match = re.search(pattern, text, re.DOTALL)

    if match:
        return clean_text(match.group(1))

    return None


# --------------------------------------------------
# PARSE COURSE INFORMATION
# --------------------------------------------------

def parse_course(text):

    code = re.search(r'Course Code\s*(\w+)', text)
    title = re.search(r'Course title\s*(.*)', text)
    semester = re.search(r'Open to Semester\s*(\d+)', text)
    nature = re.search(r'Nature of Course\s*(.*)', text)
    credits = re.search(r'Credit\s*(\d+)', text)

    prereq = extract_section(text, "Pre-requisites", "Objectives")

    objectives = extract_section(text, "Objectives", "Course content")

    content = extract_section(text, "Course content", "Evaluation")

    evaluation = extract_section(text, "Evaluation", "Suggested readings")

    readings = extract_section(text, "Suggested readings", "When Next")

    return {

        "course_code": code.group(1) if code else None,

        "title": clean_text(title.group(1)) if title else None,

        "semester": int(semester.group(1)) if semester else None,

        "nature": clean_text(nature.group(1)) if nature else None,

        "credits": int(credits.group(1)) if credits else None,

        "prerequisites": prereq,

        "objectives": objectives,

        "course_content": content,

        "evaluation": evaluation,

        "readings": readings
    }


# --------------------------------------------------
# MAIN SCRIPT
# --------------------------------------------------

def main():

    courses = []

    for file in os.listdir(PDF_FOLDER):

        if file.endswith(".pdf"):

            path = os.path.join(PDF_FOLDER, file)

            print("Processing:", file)

            text = extract_text(path)

            course = parse_course(text)

            course["file"] = file

            courses.append(course)

    os.makedirs("data/processed", exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(courses, f, indent=4)

    print("\nSaved", len(courses), "courses to", OUTPUT_FILE)


# --------------------------------------------------

if __name__ == "__main__":
    main()