from __future__ import annotations

import hashlib

# Until a profile store is populated, derive a stable, human-readable handle from the
# userId so the UI shows a consistent author. Replaced by real profile display names later.
_ADJECTIVES = (
    "quiet", "amber", "cobalt", "nimble", "cedar", "lunar", "brisk", "ember",
    "ivory", "marsh", "onyx", "sable", "tidal", "vivid", "wren", "zephyr",
)
_NOUNS = (
    "otter", "finch", "maple", "harbor", "quartz", "willow", "falcon", "sparrow",
    "cypress", "lantern", "meadow", "pebble", "thistle", "walrus", "beacon", "comet",
)


def author_handle(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode()).digest()
    adj = _ADJECTIVES[digest[0] % len(_ADJECTIVES)]
    noun = _NOUNS[digest[1] % len(_NOUNS)]
    num = digest[2] % 100
    return f"{adj}-{noun}{num:02d}"
