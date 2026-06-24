import os
import sys

import requests


BASE_URL = os.getenv("PROJECTMIND_BASE_URL", "http://127.0.0.1:5174").rstrip("/")


def check(name, method, path, **kwargs):
    url = f"{BASE_URL}{path}"
    response = requests.request(method, url, timeout=20, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{name} failed: HTTP {response.status_code} {response.text[:300]}")
    print(f"[ok] {name}")
    return response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text


def main():
    print(f"Checking ProjectMind AI at {BASE_URL}")

    dashboard = check("dashboard page", "GET", "/")
    if "ProjectMind AI" not in dashboard:
        raise RuntimeError("Dashboard page did not render the ProjectMind AI app.")

    health = check("health endpoint", "GET", "/api/v1/health")
    if health.get("status") not in {"ok", "degraded"}:
        raise RuntimeError(f"Unexpected health status: {health}")

    stats = check("dashboard stats", "GET", "/api/v1/dashboard/stats")
    if stats.get("contributors", 0) == 0 or stats.get("files", 0) == 0:
        raise RuntimeError("Demo data is not ready. Run: python demo_seed.py")

    check(
        "code understanding",
        "POST",
        "/api/v1/code/explain",
        json={"file_path": "backend/auth.py"},
    )
    check("task assignment", "GET", "/api/v1/tasks/assign/24")
    check("documentation health", "GET", "/api/v1/docs/health")

    print("")
    print("ProjectMind AI smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[fail] {exc}")
        sys.exit(1)
