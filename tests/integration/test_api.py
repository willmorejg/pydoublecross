# SPDX-FileCopyrightText: 2026 James G Willmore
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for the REST API and web UI, sharing one FastAPI TestClient."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from pydoublecross.core.runner import ValidationRunner
from pydoublecross.web.app import create_app


@pytest.fixture
def client(runner: ValidationRunner) -> Iterator[TestClient]:
    app = create_app(runner)
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_validations(client: TestClient) -> None:
    resp = client.get("/api/validations")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()]
    assert "customer_check" in names


def test_run_and_fetch_result(client: TestClient) -> None:
    run_resp = client.post("/api/validations/customer_check/run")
    assert run_resp.status_code == 200
    body = run_resp.json()
    assert body["status"] == "failed"
    run_id = body["run_id"]

    result_resp = client.get(f"/api/validations/customer_check/results/{run_id}")
    assert result_resp.status_code == 200
    assert result_resp.json()["run_id"] == run_id


def test_run_unknown_validation_404(client: TestClient) -> None:
    resp = client.post("/api/validations/does_not_exist/run")
    assert resp.status_code == 404


def test_export_report(client: TestClient) -> None:
    run_resp = client.post("/api/validations/customer_check/run")
    run_id = run_resp.json()["run_id"]
    resp = client.get(f"/api/reports/customer_check/{run_id}", params={"format": "excel"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_datasource_crud(client: TestClient) -> None:
    resp = client.get("/api/datasources")
    assert resp.status_code == 200
    names = {ds["name"] for ds in resp.json()}
    assert {"src", "tgt"} <= names

    resp = client.get("/api/datasources/src")
    assert resp.status_code == 200

    resp = client.get("/api/datasources/does_not_exist")
    assert resp.status_code == 404


def test_datasource_delete_blocked_when_referenced(client: TestClient) -> None:
    resp = client.delete("/api/datasources/src")
    assert resp.status_code == 409


def test_datasource_upsert_and_delete(client: TestClient, tmp_path) -> None:
    new_db = tmp_path / "extra.db"
    new_db.touch()
    payload = {"type": "sqlite", "path": str(new_db), "cache": {"enabled": False}}
    resp = client.put("/api/datasources/extra", json=payload)
    assert resp.status_code == 200

    resp = client.get("/api/datasources/extra")
    assert resp.status_code == 200
    assert resp.json()["type"] == "sqlite"

    resp = client.delete("/api/datasources/extra")
    assert resp.status_code == 200

    resp = client.get("/api/datasources/extra")
    assert resp.status_code == 404


def test_datasource_via_url_is_masked_in_responses(client: TestClient, tmp_path) -> None:
    db_path = tmp_path / "via_url.db"
    db_path.touch()
    payload = {
        "type": "sqlite",
        "url": f"sqlite:///{db_path}",
        "cache": {"enabled": False},
    }
    resp = client.put("/api/datasources/via_url", json=payload)
    assert resp.status_code == 200
    assert resp.json()["url"] == "***"

    resp = client.get("/api/datasources/via_url")
    assert resp.status_code == 200
    assert resp.json()["url"] == "***"

    resp = client.get("/api/datasources")
    entry = next(ds for ds in resp.json() if ds["name"] == "via_url")
    assert entry["uses_url"] is True


def test_validation_item_update_persists(client: TestClient) -> None:
    resp = client.get("/api/validations/customer_check")
    item = resp.json()
    item["numeric_tolerance"] = 0.5

    resp = client.put("/api/validations/customer_check", json=item)
    assert resp.status_code == 200
    assert resp.json()["numeric_tolerance"] == pytest.approx(0.5)


def test_cache_clear_endpoint(client: TestClient) -> None:
    client.post("/api/validations/customer_check/run")
    resp = client.delete("/api/cache", params={"data_source": "src"})
    assert resp.status_code == 200
    assert resp.json()["removed"] >= 1


def test_web_dashboard_renders(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "customer_check" in resp.text


def test_web_datasources_page_renders(client: TestClient) -> None:
    resp = client.get("/datasources")
    assert resp.status_code == 200


def test_web_validation_new_form_renders(client: TestClient) -> None:
    resp = client.get("/validations/new")
    assert resp.status_code == 200


def test_web_validation_edit_form_renders(client: TestClient) -> None:
    resp = client.get("/validations/customer_check/edit")
    assert resp.status_code == 200


def test_web_datasource_url_create_and_preserve_on_edit(client: TestClient, tmp_path) -> None:
    db_path = tmp_path / "web_via_url.db"
    db_path.touch()

    create_resp = client.post(
        "/datasources",
        data={
            "name": "web_via_url",
            "type": "sqlite",
            "url": f"sqlite:///{db_path}",
        },
        follow_redirects=False,
    )
    assert create_resp.status_code == 303

    resp = client.get("/api/datasources/web_via_url")
    assert resp.json()["url"] == "***"

    # Re-save via the web form without retyping the url - it must survive unchanged.
    edit_resp = client.post(
        "/datasources/web_via_url",
        data={"type": "sqlite", "cache_ttl_seconds": "60"},
        follow_redirects=False,
    )
    assert edit_resp.status_code == 303

    resp = client.get("/api/datasources/web_via_url")
    assert resp.json()["url"] == "***"


def test_web_run_then_view_result(client: TestClient) -> None:
    resp = client.post("/validations/customer_check/run", follow_redirects=False)
    assert resp.status_code == 303
    location = resp.headers["location"]
    result_resp = client.get(location)
    assert result_resp.status_code == 200
