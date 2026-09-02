import pytest

from .conftest import HEADERS


async def _project(client, name):
    resp = await client.post("/api/projects/", json={"work_name": name}, headers=HEADERS)
    return resp.json()["id"]


async def _clip(client, pid, content, source_url=None, type_="snippet"):
    resp = await client.post(
        "/api/extension/snippet",
        json={"project_id": pid, "type": type_, "content": content, "source_url": source_url},
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── Listing ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_clips_for_a_project(client):
    pid = await _project(client, "Clip Read Proj")
    await _clip(client, pid, "an idea", "https://example.com/a")

    resp = await client.get(f"/api/snippets/?project_id={pid}", headers=HEADERS)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["content"] == "an idea"
    assert rows[0]["source_url"] == "https://example.com/a"


@pytest.mark.asyncio
async def test_list_filters_by_project(client):
    a = await _project(client, "Proj A")
    b = await _project(client, "Proj B")
    await _clip(client, a, "belongs to A")
    await _clip(client, b, "belongs to B")

    rows = (await client.get(f"/api/snippets/?project_id={a}", headers=HEADERS)).json()
    assert [r["content"] for r in rows] == ["belongs to A"]

    # Unfiltered is the cross-project inbox.
    everything = (await client.get("/api/snippets/", headers=HEADERS)).json()
    assert len(everything) == 2


@pytest.mark.asyncio
async def test_list_is_newest_first(client):
    pid = await _project(client, "Order Proj")
    await _clip(client, pid, "first")
    await _clip(client, pid, "second")

    rows = (await client.get("/api/snippets/", headers=HEADERS)).json()
    assert [r["content"] for r in rows] == ["second", "first"]


@pytest.mark.asyncio
async def test_list_respects_limit_and_rejects_absurd_ones(client):
    pid = await _project(client, "Limit Proj")
    for i in range(3):
        await _clip(client, pid, f"clip {i}")

    assert len((await client.get("/api/snippets/?limit=2", headers=HEADERS)).json()) == 2
    assert (await client.get("/api/snippets/?limit=0", headers=HEADERS)).status_code == 422
    assert (await client.get("/api/snippets/?limit=99999", headers=HEADERS)).status_code == 422


@pytest.mark.asyncio
async def test_list_requires_api_key(client):
    assert (await client.get("/api/snippets/")).status_code in (401, 422)
    assert (await client.get("/api/snippets/", headers={"X-API-Key": "no"})).status_code == 401


# ── Re-filing ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_move_clip_to_another_project(client):
    a = await _project(client, "From Proj")
    b = await _project(client, "To Proj")
    cid = await _clip(client, a, "filed in a hurry")

    resp = await client.put(f"/api/snippets/{cid}", json={"project_id": b}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["project_id"] == b

    assert (await client.get(f"/api/snippets/?project_id={a}", headers=HEADERS)).json() == []
    assert len((await client.get(f"/api/snippets/?project_id={b}", headers=HEADERS)).json()) == 1


@pytest.mark.asyncio
async def test_move_to_unknown_project_is_404(client):
    pid = await _project(client, "Move Src")
    cid = await _clip(client, pid, "x")

    resp = await client.put(
        f"/api/snippets/{cid}",
        json={"project_id": "00000000-0000-0000-0000-000000000000"},
        headers=HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_move_unknown_clip_is_404(client):
    pid = await _project(client, "Move Dst")
    resp = await client.put(
        "/api/snippets/00000000-0000-0000-0000-000000000000",
        json={"project_id": pid},
        headers=HEADERS,
    )
    assert resp.status_code == 404


# ── Deleting ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_clip(client):
    pid = await _project(client, "Del Clip Proj")
    cid = await _clip(client, pid, "used up")

    assert (await client.delete(f"/api/snippets/{cid}", headers=HEADERS)).status_code == 204
    assert (await client.get("/api/snippets/", headers=HEADERS)).json() == []


@pytest.mark.asyncio
async def test_delete_unknown_clip_is_404(client):
    resp = await client.delete("/api/snippets/00000000-0000-0000-0000-000000000000", headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_archiving_a_project_keeps_its_clips(client):
    """Projects are archive-only — there is no DELETE route for one.

    So a clip outlives its project's active life, and archiving does not hide it
    from the cross-project inbox. Asserted rather than assumed, because the
    alternative (archived clips vanishing) is a defensible design too and this
    records which one is in force.
    """
    pid = await _project(client, "Archive Clip Proj")
    await _clip(client, pid, "outlives the archive")

    assert (await client.post(f"/api/projects/{pid}/archive", headers=HEADERS)).status_code == 200

    rows = (await client.get("/api/snippets/", headers=HEADERS)).json()
    assert [r["content"] for r in rows] == ["outlives the archive"]
