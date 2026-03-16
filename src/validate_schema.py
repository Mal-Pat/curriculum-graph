import json
from jsonschema import validate

json_file = ""
json_schema_file = ""

with open(json_file, "r") as file:
  json_contents = json.load(file)

with open(json_schema_file, "r") as file:
  schema_contents = json.load(file)

validate(
    instance=json_contents, schema=schema_contents
)