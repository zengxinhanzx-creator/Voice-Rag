"""build_where: Chroma filter dict from flags (FR-R7, SPEC §4.4)."""

from __future__ import annotations

from typing import Any

import pytest

from voice_rag.stores.chroma_store import build_where


@pytest.mark.parametrize(
    ("include_disabled", "tenant_id", "strict_tenant", "expected"),
    [
        (False, None, False, {"disabled": False}),
        (True, None, False, None),
        (
            False,
            "t1",
            False,
            {
                "$and": [
                    {"disabled": False},
                    {"$or": [{"tenant_id": "t1"}, {"tenant_id": ""}]},
                ]
            },
        ),
        (
            False,
            "t1",
            True,
            {"$and": [{"disabled": False}, {"tenant_id": "t1"}]},
        ),
        (
            True,
            "t1",
            True,
            {"tenant_id": "t1"},
        ),
    ],
    ids=[
        "disabled_only",
        "no_filter",
        "tenant_loose",
        "tenant_strict",
        "include_disabled_tenant_strict",
    ],
)
def test_build_where_parametrized(
    include_disabled: bool,
    tenant_id: str | None,
    strict_tenant: bool,
    expected: dict[str, Any] | None,
) -> None:
    assert (
        build_where(
            include_disabled=include_disabled,
            tenant_id=tenant_id,
            strict_tenant=strict_tenant,
        )
        == expected
    )
