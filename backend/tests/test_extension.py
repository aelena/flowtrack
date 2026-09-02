import pytest

from .conftest import HEADERS


async def _project(client, name, **extra):
    resp = await client.post("/api/projects/", json={"work_name": name, **extra}, headers=HEADERS)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── GET /api/extension/projects ───────────────────────────


@pytest.mark.asyncio
async def test_projects_returns_id_and_name_only(client):
    await _project(client, "Clipper Target")

    resp = await client.get("/api/extension/projects", headers=HEADERS)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert set(rows[0].keys()) == {"id", "name"}
    assert rows[0]["name"] == "Clipper Target"


@pytest.mark.asyncio
async def test_projects_sorted_by_name_and_excludes_archived(client):
    await _project(client, "Zeta")
    await _project(client, "Alpha")
    archived = await _project(client, "Beta")

    resp = await client.post(f"/api/projects/{archived}/archive", headers=HEADERS)
    assert resp.status_code == 200, resp.text

    names = [p["name"] for p in (await client.get("/api/extension/projects", headers=HEADERS)).json()]
    assert names == ["Alpha", "Zeta"]


@pytest.mark.asyncio
async def test_projects_requires_api_key(client):
    resp = await client.get("/api/extension/projects")
    # A missing header is rejected by Header(...) before the dependency runs, so
    # this is 422 rather than 401. Asserted as "not 200" because the distinction
    # is an API-wide quirk, not this endpoint's contract.
    assert resp.status_code in (401, 422)

    resp = await client.get("/api/extension/projects", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


# ── POST /api/extension/snippet ───────────────────────────


@pytest.mark.asyncio
async def test_save_snippet_keeps_source_url(client):
    pid = await _project(client, "Snip Proj")

    resp = await client.post(
        "/api/extension/snippet",
        json={
            "project_id": pid,
            "type": "snippet",
            "content": "the clipped sentence",
            "source_url": "https://example.com/article",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["snippet_type"] == "snippet"
    assert body["content"] == "the clipped sentence"
    # The regression this covers: both clients used to omit source_url, so every
    # clip lost the page it came from.
    assert body["source_url"] == "https://example.com/article"


@pytest.mark.asyncio
async def test_save_url_snippet(client):
    pid = await _project(client, "Url Proj")

    resp = await client.post(
        "/api/extension/snippet",
        json={
            "project_id": pid,
            "type": "url",
            "content": "https://example.com/page",
            "source_url": "https://example.com/page",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["snippet_type"] == "url"


@pytest.mark.asyncio
async def test_source_url_is_optional(client):
    pid = await _project(client, "No Source Proj")

    resp = await client.post(
        "/api/extension/snippet",
        json={"project_id": pid, "type": "snippet", "content": "typed by hand"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["source_url"] is None


@pytest.mark.asyncio
async def test_unknown_project_is_404_not_500(client):
    resp = await client.post(
        "/api/extension/snippet",
        json={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "type": "snippet",
            "content": "orphan",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_snippet_requires_api_key(client):
    pid = await _project(client, "Auth Proj")
    payload = {"project_id": pid, "type": "snippet", "content": "x"}

    resp = await client.post("/api/extension/snippet", json=payload)
    assert resp.status_code in (401, 422)

    resp = await client.post("/api/extension/snippet", json=payload, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


# ── The inbox: clipping before the idea has a home ────────


@pytest.mark.asyncio
async def test_inbox_is_reported_absent_before_first_clip(client):
    resp = await client.get("/api/extension/inbox", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"id": None, "name": "Inbox", "exists": False}


@pytest.mark.asyncio
async def test_null_project_creates_the_inbox_and_files_the_clip(client):
    resp = await client.post(
        "/api/extension/snippet",
        json={"type": "snippet", "content": "an idea, no home yet"},
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["project_id"]

    inbox = (await client.get("/api/extension/inbox", headers=HEADERS)).json()
    assert inbox["exists"] is True
    assert inbox["id"] == project_id
    assert inbox["name"] == "Inbox"


@pytest.mark.asyncio
async def test_repeated_unfiled_clips_reuse_one_inbox(client):
    for i in range(3):
        resp = await client.post(
            "/api/extension/snippet",
            json={"type": "snippet", "content": f"idea {i}"},
            headers=HEADERS,
        )
        assert resp.status_code == 201

    projects = (await client.get("/api/extension/projects", headers=HEADERS)).json()
    assert [p["name"] for p in projects] == ["Inbox"]

    clips = (await client.get("/api/snippets/", headers=HEADERS)).json()
    assert len(clips) == 3
    assert len({c["project_id"] for c in clips}) == 1


@pytest.mark.asyncio
async def test_existing_inbox_is_matched_case_insensitively(client):
    resp = await client.post("/api/projects/", json={"work_name": "inbox"}, headers=HEADERS)
    existing = resp.json()["id"]

    resp = await client.post(
        "/api/extension/snippet",
        json={"type": "snippet", "content": "reuses the lowercase one"},
        headers=HEADERS,
    )
    assert resp.json()["project_id"] == existing


@pytest.mark.asyncio
async def test_an_explicit_project_still_wins_over_the_inbox(client):
    pid = await _project(client, "Deliberate Home")

    resp = await client.post(
        "/api/extension/snippet",
        json={"project_id": pid, "type": "snippet", "content": "filed on purpose"},
        headers=HEADERS,
    )
    assert resp.json()["project_id"] == pid

    inbox = (await client.get("/api/extension/inbox", headers=HEADERS)).json()
    assert inbox["exists"] is False


@pytest.mark.asyncio
async def test_a_clip_can_be_moved_out_of_the_inbox(client):
    """The point of the inbox: capture now, decide later."""
    real = await _project(client, "Real Home")
    resp = await client.post(
        "/api/extension/snippet",
        json={"type": "snippet", "content": "triage me"},
        headers=HEADERS,
    )
    clip_id = resp.json()["id"]
    inbox_id = resp.json()["project_id"]

    resp = await client.put(f"/api/snippets/{clip_id}", json={"project_id": real}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["project_id"] == real

    assert (await client.get(f"/api/snippets/?project_id={inbox_id}", headers=HEADERS)).json() == []


# ── Creating a project from the clipper ───────────────────


@pytest.mark.asyncio
async def test_create_project_from_the_clipper(client):
    resp = await client.post("/api/extension/project", json={"name": "Found On The Web"}, headers=HEADERS)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body.keys()) == {"id", "name"}
    assert body["name"] == "Found On The Web"

    # It must show up in the picker straight away, or the clip cannot be filed.
    names = [p["name"] for p in (await client.get("/api/extension/projects", headers=HEADERS)).json()]
    assert names == ["Found On The Web"]


@pytest.mark.asyncio
async def test_created_project_can_take_a_clip_immediately(client):
    pid = (await client.post("/api/extension/project", json={"name": "Brand New"}, headers=HEADERS)).json()[
        "id"
    ]

    resp = await client.post(
        "/api/extension/snippet",
        json={"project_id": pid, "type": "snippet", "content": "the idea that started it"},
        headers=HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["project_id"] == pid


@pytest.mark.asyncio
async def test_create_project_trims_and_rejects_blank_names(client):
    resp = await client.post("/api/extension/project", json={"name": "  Padded  "}, headers=HEADERS)
    assert resp.json()["name"] == "Padded"

    assert (
        await client.post("/api/extension/project", json={"name": ""}, headers=HEADERS)
    ).status_code == 422
    assert (
        await client.post("/api/extension/project", json={"name": "   "}, headers=HEADERS)
    ).status_code == 422
    assert (await client.post("/api/extension/project", json={}, headers=HEADERS)).status_code == 422


@pytest.mark.asyncio
async def test_create_project_requires_api_key(client):
    payload = {"name": "Unauthorised"}
    assert (await client.post("/api/extension/project", json=payload)).status_code in (401, 422)
    resp = await client.post("/api/extension/project", json=payload, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
