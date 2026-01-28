from moex_futures_db.serializer import canonical_dumps, canonical_hash


def test_canonical_stable():
    data = {"b": 2, "a": 1}
    first = canonical_dumps(data)
    second = canonical_dumps(data)
    assert first == second


def test_canonical_hash_stable():
    data = {"b": 2, "a": 1}
    assert canonical_hash(data) == canonical_hash({"a": 1, "b": 2})
