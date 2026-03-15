import pytest
from .conftest import HEADERS


@pytest.mark.asyncio
async def test_create_and_list_notes(client):
    resp = await client.post("/api/projects/", json={"work_name": "Note Project"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(
        "/api/notes/",
        json={"project_id": pid, "content": "# My Note\nSome **markdown** content"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    note = resp.json()
    assert "markdown" in note["content"]

    resp = await client.get(f"/api/notes/?project_id={pid}", headers=HEADERS)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_note(client):
    resp = await client.post("/api/projects/", json={"work_name": "Update Note Proj"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post("/api/notes/", json={"project_id": pid, "content": "Old"}, headers=HEADERS)
    nid = resp.json()["id"]

    resp = await client.put(f"/api/notes/{nid}", json={"content": "Updated content"}, headers=HEADERS)
    assert resp.json()["content"] == "Updated content"


@pytest.mark.asyncio
async def test_delete_note(client):
    resp = await client.post("/api/projects/", json={"work_name": "Del Note Proj"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post("/api/notes/", json={"project_id": pid, "content": "Temp"}, headers=HEADERS)
    nid = resp.json()["id"]

    resp = await client.delete(f"/api/notes/{nid}", headers=HEADERS)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_note_on_task(client):
    resp = await client.post("/api/projects/", json={"work_name": "Task Note Proj"}, headers=HEADERS)
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "A task"}, headers=HEADERS)
    tid = resp.json()[0]["id"]

    resp = await client.post(
        "/api/notes/",
        json={"task_id": tid, "content": "Note on task"},
        headers=HEADERS,
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/notes/?task_id={tid}", headers=HEADERS)
    assert len(resp.json()) >= 1
