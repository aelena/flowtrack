import pytest

from .conftest import HEADERS


@pytest.mark.asyncio
async def test_create_single_task(client):
    resp = await client.post("/api/projects/", json={"work_name": "Task Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{pid}/tasks/", json={"content": "Build the thing"}, headers=HEADERS
    )
    assert resp.status_code == 201
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Build the thing"
    assert tasks[0]["status"] == "new"


@pytest.mark.asyncio
async def test_create_bulk_tasks_from_list(client):
    resp = await client.post("/api/projects/", json={"work_name": "Bulk Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    content = "- Design UI\n- Build API\n- Write tests\n- Deploy"
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": content}, headers=HEADERS)
    assert resp.status_code == 201
    tasks = resp.json()
    assert len(tasks) == 4
    assert tasks[0]["title"] == "Design UI"
    assert tasks[3]["title"] == "Deploy"


@pytest.mark.asyncio
async def test_create_bulk_tasks_ordered_list(client):
    resp = await client.post("/api/projects/", json={"work_name": "Ordered Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    content = "1. First\n2. Second\n3. Third"
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": content}, headers=HEADERS)
    tasks = resp.json()
    assert len(tasks) == 3


@pytest.mark.asyncio
async def test_update_task_status(client):
    resp = await client.post("/api/projects/", json={"work_name": "Status Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "Do it"}, headers=HEADERS)
    tid = resp.json()[0]["id"]

    resp = await client.put(
        f"/api/projects/{pid}/tasks/{tid}", json={"status": "in_progress"}, headers=HEADERS
    )
    assert resp.json()["status"] == "in_progress"

    resp = await client.put(f"/api/projects/{pid}/tasks/{tid}", json={"status": "done"}, headers=HEADERS)
    assert resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_delete_task(client):
    resp = await client.post("/api/projects/", json={"work_name": "Delete Task Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "Temp task"}, headers=HEADERS)
    tid = resp.json()[0]["id"]

    resp = await client.delete(f"/api/projects/{pid}/tasks/{tid}", headers=HEADERS)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_list_tasks_filtered_by_status(client):
    resp = await client.post("/api/projects/", json={"work_name": "Filter Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{pid}/tasks/", json={"content": "- one\n- two\n- three"}, headers=HEADERS
    )
    one, two, _three = (t["id"] for t in resp.json())
    await client.put(f"/api/projects/{pid}/tasks/{one}", json={"status": "done"}, headers=HEADERS)
    await client.put(f"/api/projects/{pid}/tasks/{two}", json={"status": "in_progress"}, headers=HEADERS)

    resp = await client.get(f"/api/projects/{pid}/tasks/?status=done", headers=HEADERS)
    assert [t["title"] for t in resp.json()] == ["one"]

    resp = await client.get(f"/api/projects/{pid}/tasks/?status=in_progress", headers=HEADERS)
    assert [t["title"] for t in resp.json()] == ["two"]

    resp = await client.get(f"/api/projects/{pid}/tasks/?status=new", headers=HEADERS)
    assert [t["title"] for t in resp.json()] == ["three"]

    # No filter is still everything, oldest first.
    resp = await client.get(f"/api/projects/{pid}/tasks/", headers=HEADERS)
    assert [t["title"] for t in resp.json()] == ["one", "two", "three"]


@pytest.mark.asyncio
async def test_list_tasks_rejects_unknown_status(client):
    """An unknown status is an error, not an empty list that looks like an answer."""
    resp = await client.post("/api/projects/", json={"work_name": "Bad Filter"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.get(f"/api/projects/{pid}/tasks/?status=finished", headers=HEADERS)
    assert resp.status_code == 422
