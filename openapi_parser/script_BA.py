import requests
import json
import yaml
from datetime import datetime

AIRFLOW_URL = "https://raw.githubusercontent.com/apache/airflow/2.10.5/airflow/api_connexion/openapi/v1.yaml"
ROLES = ["admin_se", "user_se"]
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


def fetch_openapi_yaml():
    resp = requests.get(AIRFLOW_URL, auth=("admin", "admin"))
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_empty_spec(openapi_spec):
    result = {
        "last_created": datetime.now().strftime("%d.%m.%Y"),
        "roles": {}
    }

    paths = openapi_spec.get("paths", {})

    for role in ROLES:
        role_entry = {"title": {}}

        for path, methods in paths.items():
            category = path.strip("/").split("/")[0].capitalize() or "Root"
            role_entry["title"].setdefault(category, {})

            for method in methods.keys():
                if method.lower() not in HTTP_METHODS:
                    continue

                endpoint_key = f"{method.upper()} {path}"
                role_entry["title"][category][endpoint_key] = {
                    "status_code": None,  # Аналитик потом заполнит
                    "description": ""  # Аналитик потом заполнит
                }

        result["roles"][role] = role_entry

    return result


if __name__ == "__main__":
    spec = fetch_openapi_yaml()
    empty_matrix = build_empty_spec(spec)

    with open("airflow_access_template.json", "w", encoding="utf-8") as f:
        json.dump(empty_matrix, f, indent=2, ensure_ascii=False)