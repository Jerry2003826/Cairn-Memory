"""OpenCode capture engine registration.

C-2 OpenCode v0 has no hook installer or background capture process. It only
names the engine used by human-invoked transcript ingest.
"""

from __future__ import annotations

from omni.capture import CaptureEngine, register


register(
    CaptureEngine(
        name="opencode",
        ingest_events=frozenset(),
        run_engine="opencode",
        parse_engine="opencode",
    )
)
