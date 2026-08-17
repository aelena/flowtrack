import pytest

from .conftest import HEADERS


@pytest.mark.asyncio
async def test_create_and_list_areas(client):
    resp = await client.post("/api/areas/", json={"name": "Software Products"}, headers=HEADERS)
    assert resp.status_code == 201
    area = resp.json()
    assert area["name"] == "Software Products"

    resp = await client.get("/api/areas/", headers=HEADERS)
    assert resp.status_code == 200
    areas = resp.json()
    assert len(areas) >= 1


@pytest.mark.asyncio
async def test_update_area(client):
    resp = await client.post("/api/areas/", json={"name": "Old Name"}, headers=HEADERS)
    area_id = resp.json()["id"]

    resp = await client.put(f"/api/areas/{area_id}", json={"name": "New Name"}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_area_ungroups_projects(client):
    resp = await client.post("/api/areas/", json={"name": "To Delete"}, headers=HEADERS)
    area_id = resp.json()["id"]

    resp = await client.post(
        "/api/projects/",
        json={"work_name": "Test Project", "area_id": area_id},
        headers=HEADERS,
    )
    project_id = resp.json()["id"]

    resp = await client.delete(f"/api/areas/{area_id}", headers=HEADERS)
    assert resp.status_code == 204

    resp = await client.get(f"/api/projects/{project_id}", headers=HEADERS)
    assert resp.json()["area_id"] is None


@pytest.mark.asyncio
async def test_unauthorized_request(client):
    resp = await client.get("/api/areas/")
    assert resp.status_code == 422  # Missing header
    resp = await client.get("/api/areas/", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
