from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

BASE = os.environ.get("SUPERSET_PUBLIC_URL", "http://127.0.0.1:8088").rstrip("/")
USERNAME = os.environ.get("SUPERSET_ADMIN_USERNAME", "admin")
PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
DATABASE_NAME = "LedgerFlow DuckDB"
OUTPUT = Path("/app/pythonpath/generated_dashboards.json")
ALLOWED_DOMAINS = [item.strip() for item in os.environ.get("LEDGERFLOW_ALLOWED_DOMAINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if item.strip()]

ASSETS = {
    "executive": ("Executive command centre", "superset_department_metrics"),
    "finance": ("Finance and accounting", "superset_finance_records"),
    "tax": ("Tax and compliance", "superset_tax_records"),
    "marketing": ("Growth and marketing", "superset_marketing_records"),
    "operations": ("Operations and supply", "superset_operations_records"),
    "people": ("People and payroll", "superset_people_records"),
    "market": ("Market and competitors", "superset_market_records"),
}


def wait_for_server() -> None:
    for _ in range(120):
        try:
            if requests.get(f"{BASE}/health", timeout=3).ok:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("Superset did not become healthy")


def login() -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    response = session.post(
        f"{BASE}/api/v1/security/login",
        json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
        timeout=15,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    csrf = session.get(f"{BASE}/api/v1/security/csrf_token/", headers=headers, timeout=15)
    if csrf.ok:
        headers["X-CSRFToken"] = csrf.json().get("result", "")
    return session, headers


def list_resource(session: requests.Session, headers: dict[str, str], resource: str) -> list[dict[str, Any]]:
    response = session.get(f"{BASE}/api/v1/{resource}/?q=(page:0,page_size:100)", headers=headers, timeout=30)
    response.raise_for_status()
    return list(response.json().get("result") or [])


def get_or_create_dataset(session: requests.Session, headers: dict[str, str], database_id: int, table_name: str) -> int | None:
    for item in list_resource(session, headers, "dataset"):
        if item.get("table_name") == table_name:
            return int(item["id"])
    response = session.post(
        f"{BASE}/api/v1/dataset/",
        headers=headers,
        json={"database": database_id, "schema": "main", "table_name": table_name},
        timeout=30,
    )
    if not response.ok:
        print(f"Dataset creation skipped for {table_name}: {response.status_code} {response.text[:300]}")
        return None
    return int(response.json().get("id") or response.json().get("result", {}).get("id"))


def get_or_create_dashboard(session: requests.Session, headers: dict[str, str], key: str, title: str) -> dict[str, Any]:
    slug = f"ledgerflow-{key}"
    for item in list_resource(session, headers, "dashboard"):
        if item.get("slug") == slug or item.get("dashboard_title") == title:
            return item
    response = session.post(
        f"{BASE}/api/v1/dashboard/",
        headers=headers,
        json={"dashboard_title": title, "slug": slug, "published": True},
        timeout=30,
    )
    response.raise_for_status()
    dashboard_id = response.json().get("id") or response.json().get("result", {}).get("id")
    return {"id": dashboard_id, "slug": slug, "dashboard_title": title}


def ensure_table_chart(session: requests.Session, headers: dict[str, str], key: str, title: str, dataset_id: int | None, dashboard_id: int) -> None:
    if not dataset_id:
        return
    chart_title = f"{title} — governed records"
    for item in list_resource(session, headers, "chart"):
        if item.get("slice_name") == chart_title:
            return
    params = {
        "viz_type": "table",
        "datasource": f"{dataset_id}__table",
        "all_columns": [],
        "row_limit": 100,
        "order_desc": True,
        "adhoc_filters": [],
    }
    payload = {
        "slice_name": chart_title,
        "viz_type": "table",
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "dashboards": [dashboard_id],
        "params": json.dumps(params),
    }
    response = session.post(f"{BASE}/api/v1/chart/", headers=headers, json=payload, timeout=30)
    if not response.ok:
        print(f"Starter chart creation skipped for {key}: {response.status_code} {response.text[:300]}")


def enable_embedding(session: requests.Session, headers: dict[str, str], dashboard_id: int) -> str:
    response = session.post(
        f"{BASE}/api/v1/dashboard/{dashboard_id}/embedded",
        headers=headers,
        json={"allowed_domains": ALLOWED_DOMAINS},
        timeout=30,
    )
    if response.status_code not in (200, 201, 422):
        print(f"Embedding config returned {response.status_code}: {response.text[:300]}")
    response = session.get(f"{BASE}/api/v1/dashboard/{dashboard_id}/embedded", headers=headers, timeout=30)
    if response.ok:
        result = response.json().get("result") or {}
        return str(result.get("uuid") or result.get("id") or "")
    return ""


def bootstrap_once() -> tuple[dict[str, Any], list[str]]:
    session, headers = login()
    databases = list_resource(session, headers, "database")
    database = next((item for item in databases if item.get("database_name") == DATABASE_NAME), None)
    if not database:
        raise RuntimeError(f"{DATABASE_NAME} connection was not created")
    database_id = int(database["id"])
    generated: dict[str, Any] = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "dashboards": {}}
    missing: list[str] = []
    for key, (title, table_name) in ASSETS.items():
        dataset_id = get_or_create_dataset(session, headers, database_id, table_name)
        dashboard = get_or_create_dashboard(session, headers, key, title)
        dashboard_id = int(dashboard["id"])
        ensure_table_chart(session, headers, key, title, dataset_id, dashboard_id)
        uuid_value = enable_embedding(session, headers, dashboard_id)
        if not dataset_id:
            missing.append(key)
        generated["dashboards"][key] = {
            "dashboard_id": dashboard_id,
            "uuid": uuid_value,
            "slug": dashboard.get("slug") or f"ledgerflow-{key}",
            "dataset_id": dataset_id,
            "table_name": table_name,
        }
    OUTPUT.write_text(json.dumps(generated, indent=2), encoding="utf-8")
    return generated, missing


def main() -> None:
    wait_for_server()
    for attempt in range(30):
        generated, missing = bootstrap_once()
        if not missing:
            print(f"LedgerFlow Superset assets written to {OUTPUT}")
            return
        print(f"Waiting for LedgerFlow analytics tables: {', '.join(missing)}")
        time.sleep(10)
    print(f"Superset starter dashboards were created, but some datasets are still pending. Restart Superset after LedgerFlow finishes importing files. Output: {OUTPUT}")


if __name__ == "__main__":
    main()
