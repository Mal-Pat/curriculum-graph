# Data Format

```
data-folder-name/
├── courses.json
├── major_minor_requirements.json
└── college_constraints.json
```

## Courses

Format of `courses.csv`:

```json
[
  {
    "course_codes" : ["string"],
    "subjects" : ["string"],
    "course_name" : "string",
    "credits" : "number",
    "prerequisites" : ["string"]
  }
]
```

## Major & Minor Requirements

Format of `major_minor_requirements.json`:

```json
[
  {
    "subject" : "string",
    "credits" : "number",
    "num_courses" : "number",
    "compulsory" : ["string"]
  }
]
```

## College Constraints

Format of `college_constraints.json`:

```json
{
  "degree_credits" : "number",
  "num_semesters" : "number",
  "min_credits_per_sem" : "number",
  "max_credits_per_sem" : "number"
}
```