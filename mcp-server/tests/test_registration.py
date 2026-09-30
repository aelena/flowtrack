"""Tests for the three tools that write a project's identity."""

import pytest

from flowtrack_mcp import server


class FakeClient:
    def __init__(self, areas=None):
        self.areas = areas or [{"id": "a1", "name": "Software"}]
        self.created = []
        self.updated = []
        self.archived = []

    async def list_areas(self):
        return self.areas

    async def create_area(self, name):
        area = {"id": f"a{len(self.areas) + 1}", "name": name}
        self.areas.append(area)
        return area

    async def create_project(self, **fields):
        fields = {k: v for k, v in fields.items() if v is not None}  # as the real client does
        self.created.append(fields)
        return {
            "id": "p1",
            "work_name": fields["work_name"],
            "status": fields.get("status", "active"),
            **fields,
        }

    async def update_project(self, project_id, **fields):
        fields = {k: v for k, v in fields.items() if v is not None}
        self.updated.append((project_id, fields))
        return {"id": project_id, "work_name": "X", "status": "active", **fields}

    async def archive_project(self, project_id, *, archived=True):
        self.archived.append((project_id, archived))
        return {"id": project_id, "work_name": "X", "status": "deprecated", "archived": archived}


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(server, "_client", lambda: client)
    return client


async def test_create_project_resolves_area_by_name_and_splits_tags(fake):
    out = await server.create_project(
        "Serrin", area="software", tags="python, cli ,, data", abandonment_criteria="no users by March"
    )
    assert out["id"] == "p1"
    sent = fake.created[0]
    assert sent["area_id"] == "a1"
    assert sent["tags"] == ["python", "cli", "data"]
    assert sent["abandonment_criteria"] == "no users by March"
    assert "final_name" not in sent  # None fields are not sent


async def test_create_project_makes_a_missing_area(fake):
    await server.create_project("Essays", area="Writing")
    assert [a["name"] for a in fake.areas] == ["Software", "Writing"]
    assert fake.created[0]["area_id"] == "a2"


async def test_create_project_exact_area_match_beats_substring(fake):
    fake.areas = [{"id": "a1", "name": "Software tools"}, {"id": "a2", "name": "Software"}]
    await server.create_project("X", area="software")
    assert fake.created[0]["area_id"] == "a2"


async def test_create_project_rejects_bad_state(fake):
    assert "error" in await server.create_project("X", status="paused")
    assert "error" in await server.create_project("X", star_rating=6)
    assert "error" in await server.create_project("X", subjective_completion=101)
    assert fake.created == []


async def test_describe_project_sends_only_what_was_passed(fake):
    await server.describe_project("p9", vision="one honest picture", tags="a,b")
    project_id, fields = fake.updated[0]
    assert project_id == "p9"
    assert fields == {"vision": "one honest picture", "tags": ["a", "b"]}


async def test_describe_project_empty_tags_clears_the_list(fake):
    await server.describe_project("p9", tags="")
    assert fake.updated[0][1] == {"tags": []}


async def test_archive_and_unarchive(fake):
    out = await server.archive_project("p9")
    assert out["archived"] is True
    out = await server.archive_project("p9", archived=False)
    assert out["archived"] is False
    assert fake.archived == [("p9", True), ("p9", False)]
