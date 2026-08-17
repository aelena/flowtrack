import pytest
import yaml

from app.redaction import REDACTED
from app.routers.config import _read_config

from .conftest import HEADERS

REAL_KEY = "sk-a-real-looking-key-0123456789"


def _config_with_key(key: str = REAL_KEY) -> str:
    return yaml.dump(
        {
            "llm_providers": [
                {"name": "OpenAI", "type": "openai", "api_key": key, "enabled": False},
                {"name": "Ollama", "type": "ollama", "base_url": "http://localhost:11434"},
            ],
            "cli": {"claude_command": "claude"},
        }
    )


@pytest.mark.asyncio
async def test_get_config_redacts_secrets(client):
    await client.put("/api/config/yaml", json={"yaml": _config_with_key()}, headers=HEADERS)

    resp = await client.get("/api/config/", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()

    assert body["llm_providers"][0]["api_key"] == REDACTED
    assert REAL_KEY not in resp.text
    # Non-secret fields are untouched.
    assert body["llm_providers"][1]["base_url"] == "http://localhost:11434"


@pytest.mark.asyncio
async def test_get_config_yaml_redacts_secrets(client):
    await client.put("/api/config/yaml", json={"yaml": _config_with_key()}, headers=HEADERS)

    resp = await client.get("/api/config/yaml", headers=HEADERS)
    assert REAL_KEY not in resp.json()["yaml"]
    assert REDACTED in resp.json()["yaml"]


@pytest.mark.asyncio
async def test_saving_the_redacted_placeholder_keeps_the_stored_key(client):
    """The settings page round-trips the whole document. Without this, saving
    any unrelated change would overwrite the real key with the placeholder."""
    await client.put("/api/config/yaml", json={"yaml": _config_with_key()}, headers=HEADERS)

    redacted_yaml = (await client.get("/api/config/yaml", headers=HEADERS)).json()["yaml"]
    edited = yaml.safe_load(redacted_yaml)
    edited["cli"]["claude_command"] = "claude-next"  # an unrelated edit

    resp = await client.put("/api/config/yaml", json={"yaml": yaml.dump(edited)}, headers=HEADERS)
    assert resp.status_code == 200

    on_disk = _read_config()
    assert on_disk["llm_providers"][0]["api_key"] == REAL_KEY
    assert on_disk["cli"]["claude_command"] == "claude-next"


@pytest.mark.asyncio
async def test_a_new_key_replaces_the_stored_one(client):
    await client.put("/api/config/yaml", json={"yaml": _config_with_key()}, headers=HEADERS)
    await client.put("/api/config/yaml", json={"yaml": _config_with_key("sk-brand-new")}, headers=HEADERS)

    assert _read_config()["llm_providers"][0]["api_key"] == "sk-brand-new"


@pytest.mark.asyncio
async def test_clearing_a_key_is_respected(client):
    await client.put("/api/config/yaml", json={"yaml": _config_with_key()}, headers=HEADERS)
    await client.put("/api/config/yaml", json={"yaml": _config_with_key("")}, headers=HEADERS)

    assert _read_config()["llm_providers"][0]["api_key"] == ""


@pytest.mark.asyncio
async def test_invalid_yaml_is_rejected(client):
    resp = await client.put("/api/config/yaml", json={"yaml": "foo: [unclosed"}, headers=HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_yaml_must_be_a_mapping(client):
    resp = await client.put("/api/config/yaml", json={"yaml": "- a\n- b"}, headers=HEADERS)
    assert resp.status_code == 422
