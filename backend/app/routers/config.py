import os

import yaml
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel

from ..config import settings
from ..dependencies import verify_api_key

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
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return dict(DEFAULT_CONFIG)


def _write_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


@router.get("/")
async def get_config():
    return _read_config()


@router.get("/yaml")
async def get_config_yaml():
    config = _read_config()
    return {"yaml": yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)}


@router.put("/yaml")
async def put_config_yaml(body: dict = Body(...)):
    raw = body.get("yaml", "")
    try:
        config = yaml.safe_load(raw)
        if not isinstance(config, dict):
            return {"error": "YAML must be a mapping"}
        _write_config(config)
        return {"status": "ok", "config": config}
    except yaml.YAMLError as e:
        return {"error": f"Invalid YAML: {e}"}


@router.post("/reset")
async def reset_config():
    _write_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG
