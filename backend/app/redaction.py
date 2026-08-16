"""Redaction of secret values on the way out of the API.

The YAML config and the LLM provider records both hold API keys, and both were
returned in clear by GET endpoints — to the browser, into a settings textarea,
and to anything else that could reach the API.

Redaction alone is not enough for an editable document: the settings page reads
the whole config, the user edits part of it, and writes it all back. Without
`restore_secrets`, saving would overwrite the real key with the placeholder.
"""

REDACTED = "***REDACTED***"

SECRET_KEYS = frozenset({"api_key", "apikey", "token", "secret", "password"})


def is_secret(key: str) -> bool:
    return key.lower() in SECRET_KEYS


def redact_secrets(node):
    """Return a copy with every non-empty secret value replaced by REDACTED.

    Empty values are left alone so the settings page can still show which
    providers have no key configured.
    """
    if isinstance(node, dict):
        return {k: (REDACTED if is_secret(k) and v else redact_secrets(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [redact_secrets(item) for item in node]
    return node


def restore_secrets(incoming, stored):
    """Put back any secret the caller left as the placeholder.

    Walks incoming and stored in parallel. Lists are matched by position, which
    is what the settings page produces. Reordering a provider list therefore
    loses the placeholder value and the key has to be retyped — the safe
    direction to fail, since the alternative is silently writing one provider's
    key onto another.
    """
    if isinstance(incoming, dict) and isinstance(stored, dict):
        out = {}
        for k, v in incoming.items():
            if is_secret(k) and v == REDACTED:
                out[k] = stored.get(k, "")
            else:
                out[k] = restore_secrets(v, stored.get(k))
        return out
    if isinstance(incoming, list) and isinstance(stored, list):
        return [restore_secrets(v, stored[i] if i < len(stored) else None) for i, v in enumerate(incoming)]
    return incoming
