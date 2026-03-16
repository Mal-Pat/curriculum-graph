# Data Format

```
data-folder-name/
├── courses.json
├── major_minor_requirements.json
└── college_constraints.json
```

## Courses

Format of `courses.csv`:

Present in `course_schema.json`


## Major & Minor Requirements

Format of `major_minor_requirements.json`:

Present in `major_minor_schema.json`

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