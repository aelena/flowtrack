import pytest

from .conftest import HEADERS

FLOWTRACK_IMPORT = {
    "version": "1.0",
    "exported_at": "2026-03-15T12:00:00",
    "areas": [
        {
            "id": "a1b2c3d4-0001-4000-8000-000000000001",
            "name": "Software Products",
            "created_at": "2026-03-15T10:00:00",
        }
    ],
    "projects": [
        {
            "id": "f10a1b2c-0001-4000-8000-000000000001",
            "work_name": "FlowTrack",
            "final_name": "FlowTrack",
            "description": "A personal project tracking tool.",
            "vision": "A minimalistic zen-style tool.",
            "goal": "Build a personal tool to track ideas.",
            "completion_criteria": "All core features working.",
            "abandonment_criteria": None,
            "desired_end_date": "2026-04-30",
            "github_repo": None,
            "website": None,
            "star_rating": 5,
            "subjective_completion": 75,
            "local_dir": "C:/Users/anton/projects/flowtrack",
            "area_id": "a1b2c3d4-0001-4000-8000-000000000001",
            "archived": False,
            "status": "active",
            "collaborators": [{"name": "Claude", "role": "AI"}],
            "created_at": "2026-03-15T10:00:00",
            "updated_at": "2026-03-15T12:00:00",
            "tasks": [
                {
                    "id": "e1e1e1e1-0001-4000-8000-000000000001",
                    "title": "Set up FastAPI backend",
                    "description": "Models and routers.",
                    "status": "done",
                    "created_at": "2026-03-15T10:05:00",
                    "updated_at": "2026-03-15T10:30:00",
                },
                {
                    "id": "e1e1e1e1-0002-4000-8000-000000000002",
                    "title": "Build SvelteKit frontend",
                    "description": None,
                    "status": "done",
                    "created_at": "2026-03-15T10:10:00",
                    "updated_at": None,
                },
                {
                    "id": "e1e1e1e1-0003-4000-8000-000000000003",
                    "title": "Wire up real LLM calls",
                    "description": None,
                    "status": "new",
                    "created_at": "2026-03-15T12:30:00",
                    "updated_at": None,
                },
            ],
            "notes": [
                {
                    "id": "a0a0a0a0-0001-4000-8000-000000000001",
                    "content": "# Architecture\n\nNo Tailwind, plain CSS.",
                    "task_id": None,
                    "created_at": "2026-03-15T10:00:00",
                    "updated_at": None,
                },
            ],
        }
    ],
    "snippets": [],
}


@pytest.mark.asyncio
async def test_import_full_payload(client):
    """Import the FlowTrack-style payload and verify all entities are created."""
    resp = await client.post("/api/backup/import", json=FLOWTRACK_IMPORT, headers=HEADERS)
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert body["status"] == "ok"
    assert body["imported"]["areas"] == 1
    assert body["imported"]["projects"] == 1
    assert body["imported"]["tasks"] == 3
    assert body["imported"]["notes"] == 1
    assert body["imported"]["snippets"] == 0

    # Verify project was created
    resp = await client.get("/api/projects/f10a1b2c-0001-4000-8000-000000000001", headers=HEADERS)
    assert resp.status_code == 200
    project = resp.json()
    assert project["work_name"] == "FlowTrack"
    assert project["star_rating"] == 5
    assert project["area_id"] == "a1b2c3d4-0001-4000-8000-000000000001"

    # Verify tasks
    resp = await client.get("/api/projects/f10a1b2c-0001-4000-8000-000000000001/tasks/", headers=HEADERS)
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 3
    done_tasks = [t for t in tasks if t["status"] == "done"]
    assert len(done_tasks) == 2

    # Verify notes
    resp = await client.get("/api/notes/?project_id=f10a1b2c-0001-4000-8000-000000000001", headers=HEADERS)
    assert resp.status_code == 200
    notes = resp.json()
    assert len(notes) == 1
    assert "Architecture" in notes[0]["content"]


@pytest.mark.asyncio
async def test_import_idempotent(client):
    """Importing the same data twice should not duplicate records."""
    resp1 = await client.post("/api/backup/import", json=FLOWTRACK_IMPORT, headers=HEADERS)
    assert resp1.status_code == 200

    resp2 = await client.post("/api/backup/import", json=FLOWTRACK_IMPORT, headers=HEADERS)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["imported"]["areas"] == 0
    assert body2["imported"]["projects"] == 0
    assert body2["imported"]["tasks"] == 0
    assert body2["imported"]["notes"] == 0


@pytest.mark.asyncio
async def test_export_then_import_roundtrip(client):
    """Create data, export it, and verify structure."""
    await client.post("/api/areas/", json={"name": "Roundtrip Area"}, headers=HEADERS)
    resp = await client.post("/api/projects/", json={"work_name": "Roundtrip Project"}, headers=HEADERS)
    pid = resp.json()["id"]
    await client.post(f"/api/projects/{pid}/tasks/", json={"content": "- Step 1\n- Step 2"}, headers=HEADERS)
    await client.post("/api/notes/", json={"project_id": pid, "content": "A note"}, headers=HEADERS)

    resp = await client.get("/api/backup/export", headers=HEADERS)
    assert resp.status_code == 200
    backup = resp.json()
    assert "areas" in backup
    assert "projects" in backup
    assert len(backup["projects"]) >= 1

    exported_project = next(p for p in backup["projects"] if p["id"] == pid)
    assert len(exported_project["tasks"]) == 2
    assert len(exported_project["notes"]) == 1


@pytest.mark.asyncio
async def test_import_minimal_payload(client):
    """Import with the bare minimum fields."""
    payload = {
        "version": "1.0",
        "areas": [],
        "projects": [
            {
                "id": "00000000-0000-4000-8000-000000000099",
                "work_name": "Minimal Project",
                "tasks": [],
                "notes": [],
            }
        ],
        "snippets": [],
    }
    resp = await client.post("/api/backup/import", json=payload, headers=HEADERS)
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    assert resp.json()["imported"]["projects"] == 1

    resp = await client.get("/api/projects/00000000-0000-4000-8000-000000000099", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["work_name"] == "Minimal Project"


@pytest.mark.asyncio
async def test_import_with_snippets(client):
    """Import with snippets attached to a project."""
    payload = {
        "version": "1.0",
        "areas": [],
        "projects": [
            {
                "id": "00000000-0000-4000-8000-000000000088",
                "work_name": "Snippet Project",
                "tasks": [],
                "notes": [],
            }
        ],
        "snippets": [
            {
                "id": "00000000-0000-4000-8000-0000000000a1",
                "project_id": "00000000-0000-4000-8000-000000000088",
                "snippet_type": "url",
                "content": "https://example.com",
                "source_url": None,
                "created_at": "2026-03-15T10:00:00",
            }
        ],
    }
    resp = await client.post("/api/backup/import", json=payload, headers=HEADERS)
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    assert resp.json()["imported"]["snippets"] == 1


@pytest.mark.asyncio
async def test_import_empty_payload(client):
    """Import an empty payload should succeed with zero counts."""
    payload = {"version": "1.0", "areas": [], "projects": [], "snippets": []}
    resp = await client.post("/api/backup/import", json=payload, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"]["areas"] == 0
    assert body["imported"]["projects"] == 0


@pytest.mark.asyncio
async def test_import_with_null_optional_fields(client):
    """Import where optional fields are explicitly null."""
    payload = {
        "version": "1.0",
        "areas": [],
        "projects": [
            {
                "id": "00000000-0000-4000-8000-000000000077",
                "work_name": "Null Fields Project",
                "final_name": None,
                "description": None,
                "vision": None,
                "goal": None,
                "completion_criteria": None,
                "abandonment_criteria": None,
                "desired_end_date": None,
                "github_repo": None,
                "website": None,
                "star_rating": None,
                "subjective_completion": 0,
                "local_dir": None,
                "area_id": None,
                "archived": False,
                "status": "active",
                "collaborators": [],
                "created_at": "2026-03-15T10:00:00",
                "updated_at": None,
                "tasks": [
                    {
                        "id": "00000000-0000-4000-8000-000000000078",
                        "title": "A task with null fields",
                        "description": None,
                        "status": "new",
                        "created_at": "2026-03-15T10:00:00",
                        "updated_at": None,
                    }
                ],
                "notes": [
                    {
                        "id": "00000000-0000-4000-8000-000000000079",
                        "content": "A note",
                        "task_id": None,
                        "created_at": "2026-03-15T10:00:00",
                        "updated_at": None,
                    }
                ],
            }
        ],
        "snippets": [],
    }
    resp = await client.post("/api/backup/import", json=payload, headers=HEADERS)
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert body["imported"]["projects"] == 1
    assert body["imported"]["tasks"] == 1
    assert body["imported"]["notes"] == 1
