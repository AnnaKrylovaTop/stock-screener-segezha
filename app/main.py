from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6 import QtWidgets

from app.ui_main_window import MainWindow


def _setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    _setup_logging(root / "logs")
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(config_dir=root / "app" / "config", cache_dir=root / "cache")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
