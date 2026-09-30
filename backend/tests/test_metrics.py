from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Task, TaskStatus

from .conftest import HEADERS
from .conftest import test_session as session_factory


async def _project(client, name="Metrics Project") -> str:
    resp = await client.post("/api/projects/", json={"work_name": name}, headers=HEADERS)
    return resp.json()["id"]


async def _closed_task(client, pid: str, days_ago: float, *, estimated: bool = False) -> None:
    """A done task whose completion date is placed by hand.

    days_ago is a float so the awkward cases can be expressed: 0 means a few
    seconds ago, 0.9 means earlier today.
    """
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]

    async with session_factory() as session:
        task = await session.get(Task, task_id)
        task.status = TaskStatus.done
        task.completed_at = datetime.now(UTC) - timedelta(days=days_ago)
        task.completed_at_estimated = estimated
        await session.commit()


async def _throughput(client, weeks: int = 12) -> dict:
    resp = await client.get(f"/api/metrics/throughput?weeks={weeks}", headers=HEADERS)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_no_tasks_gives_zeros_and_no_trend(client):
    body = await _throughput(client)
    assert body["last_7_days"] == 0
    assert body["previous_7_days"] == 0
    assert body["trend"] == "flat"
    assert body["total_counted"] == 0


@pytest.mark.asyncio
async def test_a_task_closed_moments_ago_is_counted(client):
    """The regression the live run caught and the unit tests had not.

    Buckets were aligned to midnight *this morning*, so anything completed since
    then sat at a negative offset and was dropped. On the real database 64 tasks
    had a completion date and 45 were counted; the missing 19 had all been closed
    that day.
    """
    pid = await _project(client)
    await _closed_task(client, pid, days_ago=0)
    await _closed_task(client, pid, days_ago=0.9)

    body = await _throughput(client)
    assert body["last_7_days"] == 2
    assert body["total_counted"] == 2


@pytest.mark.asyncio
async def test_last_week_and_the_week_before_are_separate(client):
    pid = await _project(client)
    await _closed_task(client, pid, days_ago=1)
    await _closed_task(client, pid, days_ago=3)
    await _closed_task(client, pid, days_ago=9)

    body = await _throughput(client)
    assert body["last_7_days"] == 2
    assert body["previous_7_days"] == 1
    assert body["change"] == 1


@pytest.mark.asyncio
async def test_work_older_than_the_window_is_excluded(client):
    pid = await _project(client)
    await _closed_task(client, pid, days_ago=3)
    await _closed_task(client, pid, days_ago=200)

    body = await _throughput(client, weeks=4)
    assert body["total_counted"] == 1


@pytest.mark.asyncio
async def test_a_done_task_with_no_completion_date_is_not_counted(client):
    """Nothing should create one, but the column is nullable and the config for
    this tool is a file people edit. Counting a NULL as today would put invented
    work in the chart."""
    pid = await _project(client)
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]

    async with session_factory() as session:
        task = await session.get(Task, task_id)
        task.status = TaskStatus.done
        task.completed_at = None
        await session.commit()

    assert (await _throughput(client))["total_counted"] == 0


@pytest.mark.asyncio
async def test_estimated_completions_are_counted_and_declared(client):
    """The backfilled rows still count, and the response says how many of them
    there are, so a chart can mark the part of itself that is a guess."""
    pid = await _project(client)
    await _closed_task(client, pid, days_ago=1, estimated=True)
    await _closed_task(client, pid, days_ago=2, estimated=False)

    body = await _throughput(client)
    assert body["total_counted"] == 2
    assert body["estimated_counted"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "this_week,last_week,expected",
    [
        (0, 0, "flat"),
        (1, 0, "flat"),  # inside the dead band
        (3, 0, "up"),
        (0, 3, "down"),
        (5, 4, "flat"),  # a difference of one is not a trend
        (7, 3, "up"),
    ],
)
async def test_the_trend_has_a_dead_band(client, this_week, last_week, expected):
    """On a tracker used by one person, weeks have three tasks in them.
    Reporting a direction for a difference of one would be arithmetic pretending
    to be information."""
    pid = await _project(client)
    for _ in range(this_week):
        await _closed_task(client, pid, days_ago=2)
    for _ in range(last_week):
        await _closed_task(client, pid, days_ago=9)

    assert (await _throughput(client))["trend"] == expected


@pytest.mark.asyncio
async def test_the_series_is_oldest_first_and_the_length_asked_for(client):
    body = await _throughput(client, weeks=6)
    assert len(body["weeks"]) == 6
    starts = [w["week_start"] for w in body["weeks"]]
    assert starts == sorted(starts)


@pytest.mark.asyncio
@pytest.mark.parametrize("weeks", [0, -1, 53, 500])
async def test_an_out_of_range_window_is_rejected(client, weeks):
    resp = await client.get(f"/api/metrics/throughput?weeks={weeks}", headers=HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_metrics_needs_the_api_key(client):
    resp = await client.get("/api/metrics/throughput")
    assert resp.status_code in (401, 422)


# --- completed_at is maintained by the task endpoint -----------------------


@pytest.mark.asyncio
async def test_marking_a_task_done_records_when(client):
    pid = await _project(client)
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]
    assert resp.json()[0]["completed_at"] is None

    resp = await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "done"}, headers=HEADERS)
    assert resp.json()["completed_at"] is not None
    assert resp.json()["completed_at_estimated"] is False


@pytest.mark.asyncio
async def test_editing_a_finished_task_does_not_move_its_completion_date(client):
    """This is the whole reason the column exists. On updated_at, renaming a
    closed task would count as another completion in the weekly numbers."""
    pid = await _project(client)
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]

    first = (
        await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "done"}, headers=HEADERS)
    ).json()["completed_at"]

    again = (
        await client.put(
            f"/api/projects/{pid}/tasks/{task_id}",
            json={"title": "renamed", "status": "done"},
            headers=HEADERS,
        )
    ).json()["completed_at"]

    assert again == first


@pytest.mark.asyncio
async def test_reopening_a_task_clears_its_completion_date(client):
    """A reopened task has not been completed. Keeping the old date would leave
    work on the chart that is back on the pile."""
    pid = await _project(client)
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]

    await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "done"}, headers=HEADERS)
    reopened = (
        await client.put(
            f"/api/projects/{pid}/tasks/{task_id}", json={"status": "in_progress"}, headers=HEADERS
        )
    ).json()
    assert reopened["completed_at"] is None

    assert (await _throughput(client))["total_counted"] == 0


@pytest.mark.asyncio
async def test_closing_a_reopened_task_records_the_new_date(client):
    pid = await _project(client)
    resp = await client.post(f"/api/projects/{pid}/tasks/", json={"content": "t"}, headers=HEADERS)
    task_id = resp.json()[0]["id"]

    await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "done"}, headers=HEADERS)
    await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "new"}, headers=HEADERS)
    closed_again = (
        await client.put(f"/api/projects/{pid}/tasks/{task_id}", json={"status": "done"}, headers=HEADERS)
    ).json()

    assert closed_again["completed_at"] is not None
    async with session_factory() as session:
        stored = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one()
        assert stored.completed_at is not None
