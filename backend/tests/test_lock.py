import pytest
import yaml

from app.passwords import hash_password, verify_password
from app.redaction import REDACTED
from app.routers.config import _read_config, _write_config

from .conftest import HEADERS

GOOD = "correct horse battery"
OTHER = "something else entirely"


def _set_password(config_password: str) -> None:
    """Put a lock straight into the config, bypassing the endpoint."""
    config = _read_config()
    config["security"] = {"password_hash": hash_password(config_password), "lock_on_open": True}
    _write_config(config)


# --- The hashing itself ----------------------------------------------------


def test_a_password_verifies_against_its_own_hash():
    encoded = hash_password(GOOD)
    assert verify_password(GOOD, encoded) is True


def test_the_wrong_password_does_not():
    assert verify_password(OTHER, hash_password(GOOD)) is False


def test_the_same_password_hashes_differently_each_time():
    """A shared salt would let one hash answer for another."""
    assert hash_password(GOOD) != hash_password(GOOD)


@pytest.mark.parametrize(
    "encoded",
    [
        None,
        "",
        "not-a-hash",
        "scrypt$16384$8$1$onlyfiveparts",
        "bcrypt$16384$8$1$c2FsdA==$a2V5",  # right shape, wrong algorithm
        "scrypt$notanumber$8$1$c2FsdA==$a2V5",
        "scrypt$16384$8$1$!!!notbase64!!!$a2V5",
    ],
)
def test_a_broken_stored_hash_returns_false_rather_than_raising(encoded):
    """The config is a file a person can edit. A half-written hash has to come
    back False, so the way out is the documented recovery, not a 500."""
    assert verify_password(GOOD, encoded) is False


def test_an_empty_password_never_verifies():
    assert verify_password("", hash_password(GOOD)) is False


# --- The endpoints ---------------------------------------------------------


@pytest.mark.asyncio
async def test_no_lock_by_default(client):
    resp = await client.get("/api/config/lock", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_setting_a_password_enables_the_lock(client):
    resp = await client.put("/api/config/lock/password", json={"new_password": GOOD}, headers=HEADERS)
    assert resp.status_code == 200

    state = (await client.get("/api/config/lock", headers=HEADERS)).json()
    assert state == {"enabled": True, "lock_on_open": True}


@pytest.mark.asyncio
async def test_a_short_password_is_rejected(client):
    resp = await client.put("/api/config/lock/password", json={"new_password": "abc"}, headers=HEADERS)
    assert resp.status_code == 422
    assert (await client.get("/api/config/lock", headers=HEADERS)).json()["enabled"] is False


@pytest.mark.asyncio
async def test_verify_accepts_the_right_password(client):
    _set_password(GOOD)
    resp = await client.post("/api/config/lock/verify", json={"password": GOOD}, headers=HEADERS)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_rejects_the_wrong_one(client):
    _set_password(GOOD)
    resp = await client.post("/api/config/lock/verify", json={"password": OTHER}, headers=HEADERS)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_with_no_lock_set_is_a_conflict_not_a_success(client):
    """Returning ok here would unlock a client that got out of step, for any
    input at all."""
    resp = await client.post("/api/config/lock/verify", json={"password": ""}, headers=HEADERS)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_changing_the_password_needs_the_current_one(client):
    _set_password(GOOD)
    resp = await client.put(
        "/api/config/lock/password",
        json={"new_password": "a new one entirely", "current_password": OTHER},
        headers=HEADERS,
    )
    assert resp.status_code == 401
    # The old one still works, so nothing was half-applied.
    assert (
        await client.post("/api/config/lock/verify", json={"password": GOOD}, headers=HEADERS)
    ).status_code == 200


@pytest.mark.asyncio
async def test_changing_the_password_retires_the_old_one(client):
    _set_password(GOOD)
    resp = await client.put(
        "/api/config/lock/password",
        json={"new_password": OTHER, "current_password": GOOD},
        headers=HEADERS,
    )
    assert resp.status_code == 200

    assert (
        await client.post("/api/config/lock/verify", json={"password": OTHER}, headers=HEADERS)
    ).status_code == 200
    assert (
        await client.post("/api/config/lock/verify", json={"password": GOOD}, headers=HEADERS)
    ).status_code == 401


@pytest.mark.asyncio
async def test_removing_the_lock_needs_the_password(client):
    _set_password(GOOD)
    resp = await client.request(
        "DELETE", "/api/config/lock/password", json={"current_password": OTHER}, headers=HEADERS
    )
    assert resp.status_code == 401
    assert (await client.get("/api/config/lock", headers=HEADERS)).json()["enabled"] is True


@pytest.mark.asyncio
async def test_removing_the_lock_with_the_password_works(client):
    _set_password(GOOD)
    resp = await client.request(
        "DELETE", "/api/config/lock/password", json={"current_password": GOOD}, headers=HEADERS
    )
    assert resp.status_code == 200
    assert (await client.get("/api/config/lock", headers=HEADERS)).json()["enabled"] is False


@pytest.mark.asyncio
async def test_the_prompt_can_be_turned_off_without_losing_the_password(client):
    _set_password(GOOD)
    resp = await client.put("/api/config/lock/settings", json={"lock_on_open": False}, headers=HEADERS)
    assert resp.status_code == 200

    state = (await client.get("/api/config/lock", headers=HEADERS)).json()
    assert state == {"enabled": True, "lock_on_open": False}
    assert (
        await client.post("/api/config/lock/verify", json={"password": GOOD}, headers=HEADERS)
    ).status_code == 200


# --- The hash must not leave the API ---------------------------------------


@pytest.mark.asyncio
async def test_the_hash_is_not_in_the_config_response(client):
    _set_password(GOOD)
    stored = _read_config()["security"]["password_hash"]

    resp = await client.get("/api/config/", headers=HEADERS)
    assert stored not in resp.text
    assert resp.json()["security"]["password_hash"] == REDACTED
    # The non-secret part of the section still comes through.
    assert resp.json()["security"]["lock_on_open"] is True


@pytest.mark.asyncio
async def test_the_hash_is_not_in_the_yaml_response(client):
    _set_password(GOOD)
    stored = _read_config()["security"]["password_hash"]

    resp = await client.get("/api/config/yaml", headers=HEADERS)
    assert stored not in resp.json()["yaml"]


@pytest.mark.asyncio
async def test_saving_the_settings_page_does_not_destroy_the_lock(client):
    """The settings page reads the whole config, edits part of it and writes it
    all back. Before password_hash was treated as a secret, that round trip
    wrote the placeholder over the real hash and the lock could no longer be
    opened by any password at all."""
    _set_password(GOOD)
    stored = _read_config()["security"]["password_hash"]

    redacted = (await client.get("/api/config/yaml", headers=HEADERS)).json()["yaml"]
    edited = yaml.safe_load(redacted)
    edited["cli"] = {"claude_command": "claude-next"}  # an unrelated edit

    resp = await client.put("/api/config/yaml", json={"yaml": yaml.dump(edited)}, headers=HEADERS)
    assert resp.status_code == 200

    assert _read_config()["security"]["password_hash"] == stored
    assert (
        await client.post("/api/config/lock/verify", json={"password": GOOD}, headers=HEADERS)
    ).status_code == 200


@pytest.mark.asyncio
async def test_the_lock_endpoints_need_the_api_key(client):
    _set_password(GOOD)
    for method, path, body in [
        ("GET", "/api/config/lock", None),
        ("POST", "/api/config/lock/verify", {"password": GOOD}),
        ("PUT", "/api/config/lock/password", {"new_password": OTHER}),
        ("PUT", "/api/config/lock/settings", {"lock_on_open": False}),
    ]:
        resp = await client.request(method, path, json=body)
        assert resp.status_code in (401, 422), f"{method} {path} answered {resp.status_code}"
