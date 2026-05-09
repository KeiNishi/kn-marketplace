from __future__ import annotations

try:
    from . import _common, _credentials, _manifest
    from . import concept_openai
except ImportError:
    import _common, _credentials, _manifest  # type: ignore
    import concept_openai  # type: ignore

import argparse
import json
import logging
from pathlib import Path


LOGGER: logging.Logger = _common.setup_logger("approve_concept")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approve or reject Stage 1 concept art")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--approve", action="store_true")
    action.add_argument("--reject", action="store_true")
    parser.add_argument(
        "--canonical",
        choices=("front", "three-quarter", "side", "back", "3q", "three_quarter", "threequarter"),
    )
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = Path(args.base).resolve() if args.base else None

    try:
        if args.canonical:
            concept_openai.select_canonical(args.slug, args.canonical, base=base)

        manifest = _manifest.read(args.slug, base)
        concept = manifest.get("stages", {}).get("concept", {})

        if args.reject:
            _manifest.update_stage(
                args.slug,
                "concept",
                {"approved": False, "approvedAt": None, "approvedBy": None},
                base,
            )
            print(
                f"Concept rejected for {args.slug}. "
                "Re-run /3d-pipeline:concept (with --description if needed) or change canonical."
            )
            return _common.EXIT_OK

        if concept.get("status") != "done":
            print(
                f"Cannot approve: stages.concept.status is {concept.get('status')!r}, "
                "expected 'done'. Run /3d-pipeline:concept <slug> first."
            )
            return _common.EXIT_USER_ERROR

        manifest = _manifest.update_stage(
            args.slug,
            "concept",
            {"approved": True, "approvedAt": _common.iso_now(), "approvedBy": "user"},
            base,
        )
        concept = manifest["stages"]["concept"]
        print(f"Concept approved for {args.slug}")
        print(f"approvedAt: {concept.get('approvedAt')}")
        print(f"canonicalAngle: {concept.get('canonicalAngle')}")
        return _common.EXIT_OK

    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
