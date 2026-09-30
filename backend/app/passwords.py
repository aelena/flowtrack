"""Hashing for the UI lock password.

Standard library only. scrypt is in hashlib, so this adds no dependency, and a
tool that runs on one machine has no business pulling in a crypto library for
one screen.

What this protects, stated plainly, because a lock that is misunderstood is
worse than none: the password gates the FlowTrack **interface**, not the data.
Every API route is behind the API key, and the MCP server, the browser
extension and the launcher all hold that key. Anyone who can read the API key
can read the projects with curl, password or no password. This is a lock on the
front door of the UI, for the case the tool is actually built to handle:
somebody sitting down at an unlocked machine with the browser already open.

Making it a real boundary would mean putting a session in front of every route,
which breaks all three of those clients. That is a different feature, and it
should be a deliberate decision rather than a side effect of adding a prompt.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

# 2**14 with r=8 needs 128 * 8 * 16384 = 16 MB, which fits inside OpenSSL's
# default 32 MB cap. maxmem is still passed explicitly: relying on the default
# is how this breaks on some other build of OpenSSL rather than here.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024

SALT_BYTES = 16
KEY_BYTES = 32

PREFIX = "scrypt"
MIN_LENGTH = 6


def hash_password(password: str) -> str:
    """Return an encoded hash carrying its own parameters.

    The parameters travel with the hash so that raising them later does not
    invalidate what is already stored.
    """
    salt = os.urandom(SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM,
        dklen=KEY_BYTES,
    )
    return "$".join(
        [
            PREFIX,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(key).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str | None) -> bool:
    """Check a password against an encoded hash.

    Never raises. A stored value that is empty, truncated, or written by hand
    into the YAML file has to come back False rather than blow up in a request
    handler, because the way out of a corrupted hash is the documented recovery
    path, not a 500.
    """
    if not encoded or not password:
        return False

    parts = encoded.split("$")
    if len(parts) != 6 or parts[0] != PREFIX:
        return False

    try:
        _, n, r, p, salt_b64, key_b64 = parts
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(key_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=SCRYPT_MAXMEM,
            dklen=len(expected),
        )
    except (ValueError, TypeError, MemoryError):
        return False

    return hmac.compare_digest(actual, expected)
