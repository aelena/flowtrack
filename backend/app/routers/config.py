import copy
import os

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException

from ..config import settings
from ..dependencies import verify_api_key
from ..passwords import MIN_LENGTH, hash_password, verify_password
from ..redaction import redact_secrets, restore_secrets

router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(verify_api_key)])

CONFIG_PATH = os.path.join(settings.storage_path, "flowtrack.yaml")

DEFAULT_CONFIG = {
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


# --- The UI lock -----------------------------------------------------------
#
# A password asked for when the tool is opened. It gets its own endpoints rather
# than riding on the YAML editor, because a password has to be hashed on the way
# in and the editor round-trips whatever it is given.
#
# Read app/passwords.py before extending this. In short: it gates the interface,
# not the data. Every route here is behind the API key, and the MCP server, the
# extension and the launcher all hold that key.


def _security(config: dict) -> dict:
    section = config.get("security")
    return section if isinstance(section, dict) else {}


@router.get("/lock")
async def get_lock():
    """Whether a password is set, and nothing else.

    Deliberately does not report the hash, the algorithm or the length. The
    client needs one bit to decide whether to show the prompt.
    """
    security = _security(_read_config())
    return {
        "enabled": bool(security.get("password_hash")),
        "lock_on_open": bool(security.get("lock_on_open", True)),
    }


@router.post("/lock/verify")
async def verify_lock(body: dict = Body(...)):
    security = _security(_read_config())
    stored = security.get("password_hash")

    if not stored:
        # No lock set. Say so rather than returning ok, or a client that got out
        # of step would report a successful unlock for any input at all.
        raise HTTPException(409, "No password is set")

    if not verify_password(body.get("password", ""), stored):
        raise HTTPException(401, "Incorrect password")

    return {"status": "ok"}


@router.put("/lock/password")
async def set_lock_password(body: dict = Body(...)):
    """Set or change the password.

    Changing one requires the current password. Otherwise the lock is decorative:
    anyone at the open interface could set a new one and lock the owner out.
    """
    new = body.get("new_password", "")
    if len(new) < MIN_LENGTH:
        raise HTTPException(422, f"The password must be at least {MIN_LENGTH} characters")

    config = _read_config()
    security = dict(_security(config))
    stored = security.get("password_hash")

    if stored and not verify_password(body.get("current_password", ""), stored):
        raise HTTPException(401, "Incorrect current password")

    security["password_hash"] = hash_password(new)
    security.setdefault("lock_on_open", True)
    config["security"] = security
    _write_config(config)

    return {"status": "ok", "enabled": True, "lock_on_open": security["lock_on_open"]}


@router.delete("/lock/password")
async def delete_lock_password(body: dict = Body(default={})):
    """Remove the lock. Requires the current password."""
    config = _read_config()
    security = dict(_security(config))
    stored = security.get("password_hash")

    if not stored:
        return {"status": "ok", "enabled": False}

    if not verify_password(body.get("current_password", ""), stored):
        raise HTTPException(401, "Incorrect password")

    security.pop("password_hash", None)
    config["security"] = security
    _write_config(config)

    return {"status": "ok", "enabled": False}


@router.put("/lock/settings")
async def set_lock_settings(body: dict = Body(...)):
    """Turn the prompt on or off without discarding the password.

    Separate from setting the password so that turning the lock off for an
    afternoon does not mean choosing a new one to turn it back on.
    """
    config = _read_config()
    security = dict(_security(config))
    security["lock_on_open"] = bool(body.get("lock_on_open", True))
    config["security"] = security
    _write_config(config)

    return {
        "status": "ok",
        "enabled": bool(security.get("password_hash")),
        "lock_on_open": security["lock_on_open"],
    }
