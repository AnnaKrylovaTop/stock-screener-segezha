import logging
from typing import Any

import pytest

from moex_futures_db.iss_client import ISSClient

logger = logging.getLogger(__name__)


def run_selftest(live: bool = False) -> bool:
    exit_code = pytest.main(["-q"])
    if exit_code != 0:
        return False
    if live:
        return _run_live_smoke()
    return True


def _run_live_smoke() -> bool:
    try:
        with ISSClient(page_size=1) as client:
            columns = client.fetch_columns()
            securities = list(client.fetch_securities())
        logger.info(
            "Live smoke test completed",
            extra={"columns": len(columns), "securities": len(securities)},
        )
        return True
    except Exception as exc:  # pragma: no cover - live smoke
        logger.error("Live smoke test failed", extra={"error": str(exc)})
        return False
