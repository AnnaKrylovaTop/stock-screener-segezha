from moex_futures_db.iss_client import paginate


def test_paginate():
    pages = [
        [{"SECID": "A"}, {"SECID": "B"}],
        [{"SECID": "C"}],
        [],
    ]
    calls = []

    def fetch_page(start, limit):
        calls.append((start, limit))
        return pages.pop(0)

    items = list(paginate(fetch_page, page_size=2))
    assert [item["SECID"] for item in items] == ["A", "B", "C"]
    assert calls[0] == (0, 2)
    assert calls[1] == (2, 2)
