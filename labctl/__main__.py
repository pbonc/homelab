from __future__ import annotations

import argparse
from typing import Sequence

from .doctor import run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labctl",
        description="Homelab utility CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run local homelab environment checks.",
        description="Run local homelab environment checks.",
    )
    doctor_parser.set_defaults(handler=lambda _args: run_doctor())

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "handler"):
        return int(args.handler(args))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
