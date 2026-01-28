import argparse
import logging
import sys

from moex_futures_db.iss_client import ISSClient
from moex_futures_db.selftest import run_selftest
from moex_futures_db.sync import sync_db
from moex_futures_db.validate import validate_db


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="moex_futures_db")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Sync MOEX futures reference data")
    sync_parser.add_argument("--out", required=True, help="Output directory for db")

    validate_parser = subparsers.add_parser("validate", help="Validate a local db")
    validate_parser.add_argument("--db", required=True, help="Database directory")

    selftest_parser = subparsers.add_parser("selftest", help="Run self tests")
    selftest_parser.add_argument(
        "--live",
        action="store_true",
        help="Enable a minimal live request against MOEX ISS",
    )

    args = parser.parse_args()
    _configure_logging(args.verbose)

    if args.command == "sync":
        with ISSClient() as client:
            sync_db(args.out, client)
        return
    if args.command == "validate":
        validate_db(args.db)
        return
    if args.command == "selftest":
        success = run_selftest(live=args.live)
        sys.exit(0 if success else 1)
