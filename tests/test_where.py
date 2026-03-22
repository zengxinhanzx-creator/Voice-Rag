from voice_rag.stores.chroma_store import build_where


def test_where_disabled_only() -> None:
    w = build_where(include_disabled=False, tenant_id=None, strict_tenant=False)
    assert w == {"disabled": False}


def test_where_tenant_loose() -> None:
    w = build_where(include_disabled=False, tenant_id="t1", strict_tenant=False)
    assert w == {
        "$and": [
            {"disabled": False},
            {"$or": [{"tenant_id": "t1"}, {"tenant_id": ""}]},
        ]
    }


def test_where_tenant_strict() -> None:
    w = build_where(include_disabled=False, tenant_id="t1", strict_tenant=True)
    assert w == {"$and": [{"disabled": False}, {"tenant_id": "t1"}]}


def test_where_include_disabled() -> None:
    w = build_where(include_disabled=True, tenant_id=None, strict_tenant=False)
    assert w is None
