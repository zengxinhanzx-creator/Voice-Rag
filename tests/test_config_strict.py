"""VoiceRAGConfig: strict_tenant coercion (env-style inputs)."""

from __future__ import annotations

import pytest

from voice_rag.config import VoiceRAGConfig


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (True, True),
        (False, False),
        (0, False),
        (1, True),
        ("0", False),
        ("1", True),
        ("false", False),
        ("true", True),
        ("no", False),
        ("yes", True),
    ],
)
def test_strict_tenant_values(raw: object, expected: bool) -> None:
    c = VoiceRAGConfig(strict_tenant=raw)
    assert c.strict_tenant is expected
