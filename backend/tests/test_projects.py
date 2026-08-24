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


@pytest.mark.asyncio
async def test_last_activity_follows_tasks_not_the_project_row(client):
    """Touching a task has to count as activity on its project.

    Editing a task bumps the task's updated_at and leaves the project row alone,
    so a list ordered by Project.updated_at showed projects nobody had opened in
    a week above ones edited minutes ago.
    """
    resp = await client.post("/api/projects/", json={"work_name": "Quiet"}, headers=HEADERS)
    quiet_id = resp.json()["id"]
    resp = await client.post("/api/projects/", json={"work_name": "Busy"}, headers=HEADERS)
    busy_id = resp.json()["id"]

    # Only the second project gets any work done on it, and none of that work is
    # an edit to the project itself.
    resp = await client.post(
        f"/api/projects/{busy_id}/tasks/", json={"content": "Do the thing"}, headers=HEADERS
    )
    assert resp.status_code in (200, 201)

    listed = {p["id"]: p for p in (await client.get("/api/projects/", headers=HEADERS)).json()}

    busy = listed[busy_id]
    quiet = listed[quiet_id]
    assert busy["last_activity_at"] is not None
    assert quiet["last_activity_at"] is not None

    # The project row itself was never edited after creation, so the task is the
    # only thing that can have moved this.
    assert busy["last_activity_at"] > busy["updated_at"]
    assert quiet["last_activity_at"] == quiet["updated_at"]
    assert busy["last_activity_at"] > quiet["last_activity_at"]


@pytest.mark.asyncio
async def test_sort_by_last_activity(client):
    resp = await client.post("/api/projects/", json={"work_name": "Older"}, headers=HEADERS)
    older_id = resp.json()["id"]
    resp = await client.post("/api/projects/", json={"work_name": "Newer"}, headers=HEADERS)
    newer_id = resp.json()["id"]

    await client.post(f"/api/projects/{older_id}/tasks/", json={"content": "first"}, headers=HEADERS)
    await client.post(f"/api/projects/{newer_id}/tasks/", json={"content": "second"}, headers=HEADERS)

    resp = await client.get("/api/projects/?sort_by=last_activity_at&sort_order=desc", headers=HEADERS)
    assert resp.status_code == 200
    order = [p["id"] for p in resp.json()]
    assert order.index(newer_id) < order.index(older_id)

    resp = await client.get("/api/projects/?sort_by=last_activity_at&sort_order=asc", headers=HEADERS)
    order = [p["id"] for p in resp.json()]
    assert order.index(older_id) < order.index(newer_id)


@pytest.mark.asyncio
async def test_unknown_sort_key_still_falls_back(client):
    """An unrecognised sort_by must not 500 now that the sort has three branches."""
    resp = await client.get("/api/projects/?sort_by=; DROP TABLE projects", headers=HEADERS)
    assert resp.status_code == 200
