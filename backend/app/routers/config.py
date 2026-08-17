import copy
import os

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException

from ..config import settings
from ..dependencies import verify_api_key
from ..redaction import redact_secrets, restore_secrets

router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(verify_api_key)])

CONFIG_PATH = os.path.join(settings.storage_path, "flowtrack.yaml")

DEFAULT_CONFIG = {
    "llm_providers": [
        {
            "name": "OpenAI",
            "type": "openai",
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o",
            "enabled": False,
        },
        {
            "name": "Anthropic",
            "type": "anthropic",
            "api_key": "",
            "model": "claude-sonnet-4-20250514",
            "enabled": False,
        },
        {
            "name": "Ollama (local)",
            "type": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama3",
            "enabled": False,
        },
    ],
    "ides": [
        {
            "name": "Cursor",
            "command": "cursor",
            "args": ["{project_dir}"],
        },
        {
            "name": "VS Code",
            "command": "code",
            "args": ["{project_dir}"],
        },
        {
            "name": "WebStorm",
            "command": "webstorm",
            "args": ["{project_dir}"],
        },
    ],
    "cli": {
        "claude_command": "claude",
    },
}


def _read_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    # deepcopy, not dict(): a shallow copy shares the nested provider and IDE
    # dicts with DEFAULT_CONFIG, so any caller mutating one would corrupt the
    # defaults for the lifetime of the process.
    return copy.deepcopy(DEFAULT_CONFIG)


def _write_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


@router.get("/")
async def get_config():
    return redact_secrets(_read_config())


@router.get("/yaml")
async def get_config_yaml():
    config = redact_secrets(_read_config())
    return {"yaml": yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)}


@router.put("/yaml")
async def put_config_yaml(body: dict = Body(...)):
    raw = body.get("yaml", "")
    try:
        config = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        # Fail with a status code. Returning 200 with an {"error": ...} body
        # broke the problem+json contract the rest of the API follows and left
        # the client unable to tell success from failure.
        raise HTTPException(422, f"Invalid YAML: {e}") from e

    if not isinstance(config, dict):
        raise HTTPException(422, "YAML must be a mapping at the top level")

    config = restore_secrets(config, _read_config())
    _write_config(config)
    return {"status": "ok", "config": redact_secrets(config)}


@router.post("/reset")
async def reset_config():
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    _write_config(defaults)
    return redact_secrets(defaults)
