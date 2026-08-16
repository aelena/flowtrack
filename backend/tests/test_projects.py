import pytest

from .conftest import HEADERS


@pytest.mark.asyncio
async def test_create_project(client):
    resp = await client.post(
        "/api/projects/",
        json={"work_name": "My App", "description": "A cool app", "star_rating": 4},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["work_name"] == "My App"
    assert data["star_rating"] == 4
    assert data["archived"] is False


@pytest.mark.asyncio
async def test_list_and_search_projects(client):
    await client.post("/api/projects/", json={"work_name": "Alpha"}, headers=HEADERS)
    await client.post("/api/projects/", json={"work_name": "Beta"}, headers=HEADERS)

    resp = await client.get("/api/projects/", headers=HEADERS)
    assert len(resp.json()) >= 2

    resp = await client.get("/api/projects/?search=Alpha", headers=HEADERS)
    assert all("Alpha" in p["work_name"] for p in resp.json())


@pytest.mark.asyncio
async def test_update_project(client):
    resp = await client.post("/api/projects/", json={"work_name": "V1"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.put(
        f"/api/projects/{pid}", json={"work_name": "V2", "star_rating": 5}, headers=HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["work_name"] == "V2"


@pytest.mark.asyncio
async def test_archive_project(client):
    resp = await client.post("/api/projects/", json={"work_name": "Archive Me"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/archive", headers=HEADERS)
    assert resp.json()["archived"] is True


@pytest.mark.asyncio
async def test_unarchive_project(client):
    resp = await client.post("/api/projects/", json={"work_name": "Round Trip"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/archive", headers=HEADERS)
    assert resp.json()["archived"] is True

    resp = await client.post(f"/api/projects/{pid}/unarchive", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["archived"] is False

    # And it shows up again in the default (non-archived) listing.
    resp = await client.get("/api/projects/", headers=HEADERS)
    assert any(p["id"] == pid for p in resp.json())


@pytest.mark.asyncio
async def test_invalid_status_is_rejected_with_422(client):
    resp = await client.post("/api/projects/", json={"work_name": "Bad Status"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.put(f"/api/projects/{pid}", json={"status": "bogus"}, headers=HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_task_completion_percentage(client):
    resp = await client.post("/api/projects/", json={"work_name": "Tasked"}, headers=HEADERS)
    pid = resp.json()["id"]

    await client.post(f"/api/projects/{pid}/tasks/", json={"content": "- Task A\n- Task B"}, headers=HEADERS)

    # Mark one task done
    tasks_resp = await client.get(f"/api/projects/{pid}/tasks/", headers=HEADERS)
    tid = tasks_resp.json()[0]["id"]
    await client.put(f"/api/projects/{pid}/tasks/{tid}", json={"status": "done"}, headers=HEADERS)

    resp = await client.get(f"/api/projects/{pid}", headers=HEADERS)
    assert resp.json()["task_completion"] == 50.0


@pytest.mark.asyncio
async def test_pending_endpoint(client):
    resp = await client.post("/api/projects/", json={"work_name": "Pending Test"}, headers=HEADERS)
    pid = resp.json()["id"]
    await client.post(f"/api/projects/{pid}/tasks/", json={"content": "Do something"}, headers=HEADERS)

    resp = await client.get(f"/api/projects/{pid}/pending", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["pending_tasks"]) == 1


@pytest.mark.asyncio
async def test_export_project(client):
    resp = await client.post("/api/projects/", json={"work_name": "Export Me"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.get(f"/api/projects/{pid}/export", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
