"""QwenCode capture engine registration.

QwenCode v0 has no hook installer or background capture process. It only names
the engine used by human-invoked transcript ingest.
"""

from __future__ import annotations

from omni.capture import CaptureEngine, register


register(
    CaptureEngine(
        name="qwen",
        ingest_events=frozenset(),
        run_engine="qwen",
    )
)
