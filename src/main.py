import json


def load_courses(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    courses = load_courses('/Users/ayush/Desktop/curriculum-graph/data/Test_Data/T1.json')
    print('Test Courses for Curriculum Graph:')
    for course in courses:
        minor_info = f", Minor: {course['minor']}" if course['minor'] else ""
        print(f"{course['id']}: {course['name']} [Major: {course['major']}{minor_info}]")

if __name__ == "__main__":
    main()