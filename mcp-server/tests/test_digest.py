"""Tests for the shaping logic — the part that is ours rather than the SDK's."""

from datetime import UTC, datetime, timedelta

import pytest

from flowtrack_mcp import server


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def _project(**over):
    base = {
        "id": "00000000-0000-4000-8000-000000000001",
        "work_name": "A project",
        "final_name": None,
        "status": "active",
        "star_rating": 3,
        "subjective_completion": 50,
        "task_completion": 50.0,
        "updated_at": _iso(1),
        "desired_end_date": None,
        "tags": [],
        "area_id": None,
    }
    base.update(over)
    return base


class FakeClient:
    def __init__(self, projects, areas=None):
        self._projects = projects
        self._areas = areas or [{"id": "a1", "name": "Software"}]

    async def list_projects(self, *, archived=False, **params):
        rows = [p for p in self._projects if p.get("archived", False) == archived]
        if params.get("status"):
            rows = [p for p in rows if p["status"] == params["status"]]
        if params.get("area_id"):
            rows = [p for p in rows if p.get("area_id") == params["area_id"]]
        return rows

    async def list_areas(self):
        return self._areas


@pytest.fixture
def fake(monkeypatch):
    def _install(projects, areas=None):
        client = FakeClient(projects, areas)
        monkeypatch.setattr(server, "_client", lambda: client)
        return client

    return _install


async def test_digest_counts_by_status(fake):
    fake(
        [
            _project(status="active"),
            _project(status="active"),
            _project(status="on_hold"),
            _project(status="deprecated", archived=True),
        ]
    )
    d = await server.portfolio_digest()
    assert d["totals"]["tracked"] == 3  # archived excluded
    assert d["totals"]["active"] == 2
    assert d["totals"]["on_hold"] == 1


async def test_digest_flags_wip_over_the_limit(fake):
    fake([_project() for _ in range(5)])
    d = await server.portfolio_digest(wip_limit=3)
    assert d["wip"] == {"limit": 3, "active": 5, "over_by": 2}


async def test_digest_wip_is_not_negative_when_under(fake):
    fake([_project()])
    assert (await server.portfolio_digest(wip_limit=3))["wip"]["over_by"] == 0


async def test_digest_orders_stale_by_how_long_untouched(fake):
    fake(
        [
            _project(work_name="recent", updated_at=_iso(2)),
            _project(work_name="old", updated_at=_iso(90)),
            _project(work_name="middling", updated_at=_iso(45)),
        ]
    )
    d = await server.portfolio_digest(stale_days=30)
    assert [p["name"] for p in d["stale"]] == ["old", "middling"]


async def test_digest_ignores_stale_projects_that_are_on_hold(fake):
    """Freezing something is a decision. It should stop nagging."""
    fake([_project(status="on_hold", updated_at=_iso(200))])
    assert (await server.portfolio_digest())["stale"] == []


async def test_digest_finds_overdue(fake):
    past = (datetime.now(UTC) - timedelta(days=10)).date().isoformat()
    future = (datetime.now(UTC) + timedelta(days=10)).date().isoformat()
    fake(
        [
            _project(work_name="late", desired_end_date=past),
            _project(work_name="fine", desired_end_date=future),
            _project(work_name="undated"),
        ]
    )
    d = await server.portfolio_digest()
    assert [p["name"] for p in d["overdue"]] == ["late"]


async def test_digest_surfaces_the_widest_completion_gap(fake):
    fake(
        [
            _project(work_name="honest", subjective_completion=50, task_completion=50.0),
            _project(work_name="deluded", subjective_completion=90, task_completion=0.0),
            _project(work_name="modest", subjective_completion=10, task_completion=80.0),
        ]
    )
    d = await server.portfolio_digest()
    gaps = d["widest_completion_gaps"]
    assert gaps[0]["name"] == "deluded"
    assert gaps[0]["gap"] == 90
    # Negative gaps matter too: tasks done but you do not believe it is finished.
    assert any(g["name"] == "modest" and g["gap"] == -70 for g in gaps)


async def test_list_projects_filters_and_sorts_by_stars(fake):
    fake(
        [
            _project(work_name="two", star_rating=2),
            _project(work_name="five", star_rating=5),
            _project(work_name="four", star_rating=4),
        ]
    )
    out = await server.list_projects(min_stars=4)
    assert [p["name"] for p in out["projects"]] == ["five", "four"]
    assert out["count"] == 2


async def test_list_projects_reports_an_unknown_area_helpfully(fake):
    fake([_project()], areas=[{"id": "a1", "name": "Software"}])
    out = await server.list_projects(area="Nonexistent")
    assert "error" in out
    assert out["areas"] == ["Software"]


async def test_list_projects_prefers_the_final_name(fake):
    fake([_project(work_name="working title", final_name="Real Name")])
    out = await server.list_projects()
    assert out["projects"][0]["name"] == "Real Name"


async def test_set_project_state_rejects_bad_input(fake):
    fake([_project()])
    assert "error" in await server.set_project_state("id", status="bogus")
    assert "error" in await server.set_project_state("id", star_rating=9)
    assert "error" in await server.set_project_state("id", subjective_completion=150)


async def test_update_task_status_rejects_bad_input(fake):
    fake([_project()])
    assert "error" in await server.update_task_status("p", "t", "finished")


def test_days_since_handles_missing_and_malformed():
    assert server._days_since(None) is None
    assert server._days_since("not a date") is None
    assert server._days_since(_iso(7)) == 7


def test_prompts_are_not_empty_and_mention_the_decision():
    reckoning = server.reckoning_prompt()
    assert "abandonment_criteria" in reckoning
    for word in ("continue", "freeze", "kill"):
        assert word in reckoning.lower()

    assert "WIP" in server.next_prompt() or "wip" in server.next_prompt()
    assert "salvag" in server.close_out_prompt("some-id")
