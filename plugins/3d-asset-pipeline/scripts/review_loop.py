from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from . import _common, _manifest
except ImportError:
    import _common  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("review_loop")


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _review_dir(slug: str, base: Path | None) -> Path:
    return _common.output_dir(slug, base) / "review"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    return None


def _last_iteration_from_dirs(review_dir: Path) -> int:
    values = []
    for path in review_dir.glob("iter-*"):
        if path.is_dir():
            suffix = path.name.removeprefix("iter-")
            if suffix.isdigit():
                values.append(int(suffix))
    return max(values, default=0)


def _manifest_iterations(manifest: dict[str, Any]) -> int:
    review = manifest.get("stages", {}).get("review", {})
    try:
        return int(review.get("iterations", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _next_iteration(slug: str, base: Path | None, manifest: dict[str, Any]) -> int:
    review_dir = _review_dir(slug, base)
    return max(_manifest_iterations(manifest), _last_iteration_from_dirs(review_dir)) + 1


def _approved_verdict(slug: str, base: Path | None, iteration: int) -> dict[str, Any] | None:
    if iteration < 1:
        return None
    verdict = _read_json(_review_dir(slug, base) / f"iter-{iteration}" / "verdict.json")
    if verdict and verdict.get("approved") is True:
        return verdict
    return None


def _verdict_iteration(path: Path) -> int | None:
    suffix = path.parent.name.removeprefix("iter-")
    if suffix.isdigit():
        return int(suffix)
    return None


def _latest_verdict(slug: str, base: Path | None) -> tuple[int, Path, dict[str, Any]] | None:
    candidates: list[tuple[int, Path]] = []
    for path in _review_dir(slug, base).glob("iter-*/verdict.json"):
        iteration = _verdict_iteration(path)
        if iteration is not None:
            candidates.append((iteration, path))

    if not candidates:
        return None

    iteration, path = max(candidates, key=lambda item: item[0])
    verdict = _read_json(path)
    if verdict is None:
        raise ValueError(f"Latest verdict is not a JSON object: {path}")
    return iteration, path, verdict


def _finalize(slug: str, base: Path | None) -> int:
    latest = _latest_verdict(slug, base)
    if latest is None:
        print(f"No verdict.json found for {slug}")
        return _common.EXIT_REVIEW_UNRESOLVED

    iteration, path, verdict = latest
    if verdict.get("approved") is not True:
        print(f"Latest verdict at iter-{iteration} is not approved")
        return _common.EXIT_REVIEW_UNRESOLVED

    manifest = _manifest.read(slug, base)
    review = manifest.get("stages", {}).get("review", {})
    _manifest.update_stage(
        slug,
        "review",
        {
            "status": "done",
            "approved": True,
            "iterations": iteration,
            "loopEnabled": review.get("loopEnabled", True),
            "completedAt": _common.iso_now(),
        },
        base,
    )
    print(f"Review finalized for {slug} from {path.parent.name}")
    return _common.EXIT_OK


def _print_status(slug: str, base: Path | None) -> int:
    manifest = _manifest.read(slug, base)
    review = manifest.get("stages", {}).get("review", {})
    last_iter = max(_manifest_iterations(manifest), _last_iteration_from_dirs(_review_dir(slug, base)))
    verdict = _read_json(_review_dir(slug, base) / f"iter-{last_iter}" / "verdict.json") if last_iter else None
    print(f"review.status={review.get('status', 'pending')}")
    print(f"review.approved={review.get('approved', False)}")
    print(f"review.iterations={last_iter}")
    print(f"review.nextIter={last_iter + 1}")
    if verdict is not None:
        print(f"lastVerdict.approved={verdict.get('approved')}")
        print(f"lastVerdict.remaining={verdict.get('remaining')}")
    return _common.EXIT_OK


def _capture_command(args: argparse.Namespace, iteration: int) -> list[str]:
    script = Path(__file__).resolve().with_name("godot_capture.py")
    command = [
        sys.executable,
        str(script),
        args.slug,
        "--project",
        args.project,
        "--iter",
        str(iteration),
    ]
    if args.godot:
        command.extend(["--godot", args.godot])
    if args.apply_fixes:
        command.extend(["--apply-fixes", args.apply_fixes])
    if args.base:
        command.extend(["--base", args.base])
    return command


def run(args: argparse.Namespace) -> int:
    base = _base_dir(args.base)
    manifest = _manifest.read(args.slug, base)
    review = manifest.get("stages", {}).get("review", {})

    last_iter = max(_manifest_iterations(manifest), _last_iteration_from_dirs(_review_dir(args.slug, base)))
    if review.get("approved") is True:
        print(f"Review already approved for {args.slug} at iter {last_iter}")
        return _common.EXIT_OK
    if _approved_verdict(args.slug, base, last_iter):
        _manifest.update_stage(
            args.slug,
            "review",
            {
                "status": "done",
                "approved": True,
                "iterations": last_iter,
                "maxIters": args.max_iters,
                "loopEnabled": not args.no_loop,
                "completedAt": _common.iso_now(),
            },
            base,
        )
        print(f"Review already approved for {args.slug} at iter {last_iter}")
        return _common.EXIT_OK

    iteration = args.iter or _next_iteration(args.slug, base, manifest)
    if iteration > args.max_iters and not args.no_loop:
        LOGGER.error("Review loop reached --max-iters=%s before approval", args.max_iters)
        return _common.EXIT_REVIEW_UNRESOLVED

    command = _capture_command(args, iteration)
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode

    manifest = _manifest.read(args.slug, base)
    review = manifest.get("stages", {}).get("review", {})
    _manifest.update_stage(
        args.slug,
        "review",
        {
            "status": review.get("status", "in_progress"),
            "iterations": max(iteration, int(review.get("iterations", 0) or 0)),
            "maxIters": args.max_iters,
            "loopEnabled": not args.no_loop,
        },
        base,
    )
    print(f"CAPTURED slug={args.slug} iter={iteration} loopEnabled={not args.no_loop}")
    return _common.EXIT_OK


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive Stage 6 Godot capture iterations")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--project", help="absolute path to a Godot project root")
    parser.add_argument("--iter", type=int, help="explicit review iteration number")
    parser.add_argument("--max-iters", type=int, default=5, help="maximum review-loop iterations")
    parser.add_argument("--no-loop", action="store_true", help="capture once and do not request another iteration")
    parser.add_argument("--apply-fixes", help="fix-instructions.json to apply before capture")
    parser.add_argument("--godot", help="path to Godot executable")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--status", action="store_true", help="print loop status and exit")
    parser.add_argument("--finalize", action="store_true", help="finalize an already-approved verdict")
    args = parser.parse_args(argv)
    if not args.status and not args.finalize and not args.project:
        parser.error("--project is required unless --status or --finalize is used")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = _base_dir(args.base)
    try:
        if args.finalize:
            return _finalize(args.slug, base)
        if args.status:
            return _print_status(args.slug, base)
        return run(args)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
