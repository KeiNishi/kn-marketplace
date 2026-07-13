from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from . import _common, _manifest
except ImportError:
    import _common  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("godot_capture")
STATIC_PNGS = ("front.png", "three-quarter.png", "side.png", "back.png")
OPTIONAL_PNGS = ("animation-mid.png",)
TIMEOUT_SECONDS = 120


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _validate_project(project_value: str) -> Path:
    project = Path(project_value)
    if not project.is_absolute():
        raise ValueError("--project must be an absolute path to a Godot project root")
    project = project.resolve()
    if not project.is_dir():
        raise ValueError(f"Godot project root does not exist: {project}")
    if not (project / "project.godot").is_file():
        raise ValueError(f"Godot project root must contain project.godot: {project}")
    return project


def _locate_godot(explicit: str | None) -> str:
    candidates = [explicit, os.environ.get("GODOT_EXECUTABLE"), shutil.which("godot"), shutil.which("godot4")]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    raise FileNotFoundError("Godot executable not found. Pass --godot or set GODOT_EXECUTABLE.")


def _sync_addon(project: Path) -> None:
    """Copy the bundled addon into the project, refreshing files whose content
    differs so plugin updates propagate to projects that already have a copy."""
    source = _plugin_root() / "godot" / "addons" / "3d_pipeline"
    target = project / "addons" / "3d_pipeline"
    if not source.is_dir():
        raise FileNotFoundError(f"Bundled Godot addon not found: {source}")
    for source_file in sorted(source.rglob("*")):
        if source_file.is_dir():
            continue
        target_file = target / source_file.relative_to(source)
        if target_file.exists() and target_file.read_bytes() == source_file.read_bytes():
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, target_file)


def _review_dir(slug: str, base: Path | None) -> Path:
    path = _common.output_dir(slug, base) / "review"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _iter_dir(slug: str, base: Path | None, iteration: int) -> Path:
    path = _review_dir(slug, base) / f"iter-{iteration}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _asset_res_path(manifest: dict[str, Any]) -> str:
    engine = manifest.get("stages", {}).get("engine", {})
    rel_path = engine.get("scenePath") or engine.get("targetPath")
    if not rel_path:
        raise ValueError("Manifest stages.engine must include scenePath or targetPath")
    if str(rel_path).startswith("res://"):
        return str(rel_path)
    return "res://" + str(rel_path).replace("\\", "/").lstrip("/")


def _run_godot(command: list[str]) -> None:
    LOGGER.info("Running %s", " ".join(command))
    completed = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"Godot exited with code {completed.returncode}")


def _run_apply_fixes(godot: str, project: Path, slug: str, fixes: str) -> None:
    fixes_path = Path(fixes).resolve()
    if not fixes_path.is_file():
        raise FileNotFoundError(f"Fix instructions not found: {fixes_path}")
    _run_godot(
        [
            godot,
            "--path",
            str(project),
            "--script",
            "res://addons/3d_pipeline/apply_fixes.gd",
            "--",
            "--fixes",
            str(fixes_path),
            "--asset",
            slug,
        ]
    )


def _run_capture(godot: str, project: Path, slug: str, source: str, output: Path) -> None:
    _run_godot(
        [
            godot,
            "--path",
            str(project),
            "--script",
            "res://addons/3d_pipeline/capture.gd",
            "--",
            "--asset",
            slug,
            "--source",
            source,
            "--output",
            str(output),
        ]
    )


def _copy_dry_run(output: Path, slug: str, source: str) -> None:
    fixture = _plugin_root() / "scripts" / "fixtures" / "screenshots" / "iter-1"
    if not fixture.is_dir():
        raise FileNotFoundError(f"Dry-run screenshot fixture not found: {fixture}")
    output.mkdir(parents=True, exist_ok=True)
    images: list[dict[str, str]] = []
    for name in STATIC_PNGS + OPTIONAL_PNGS:
        shutil.copyfile(fixture / name, output / name)
        images.append({"file": name, "path": str(output / name)})
    _common.atomic_write_json(
        output / "screenshots.json",
        {"asset": slug, "source": source, "output": str(output), "dryRun": True, "images": images},
    )


def _verify_pngs(output: Path) -> list[str]:
    found = []
    for name in STATIC_PNGS:
        path = output / name
        if not path.is_file():
            raise FileNotFoundError(f"Expected screenshot missing: {path}")
        found.append(str(path))
    for name in OPTIONAL_PNGS:
        path = output / name
        if path.is_file():
            found.append(str(path))
    return found


def _merge_history(history: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    merged = [item for item in history if int(item.get("iter", -1)) != int(entry["iter"])]
    merged.append(entry)
    merged.sort(key=lambda item: int(item.get("iter", 0)))
    return merged


def _update_review_stage(slug: str, base: Path | None, iteration: int, output: Path, screenshots: list[str]) -> dict[str, Any]:
    manifest = _manifest.read(slug, base)
    review = manifest.get("stages", {}).get("review", {})
    history = review.get("history", [])
    if not isinstance(history, list):
        history = []
    entry = {
        "iter": iteration,
        "screenshots": [str(Path(path).name) for path in screenshots],
        "outputDir": str(output),
        "capturedAt": _common.iso_now(),
    }
    approved = bool(review.get("approved", False))
    return _manifest.update_stage(
        slug,
        "review",
        {
            "status": "done" if approved else "in_progress",
            "iterations": max(int(review.get("iterations", 0) or 0), iteration),
            "loopEnabled": True,
            "history": _merge_history(history, entry),
        },
        base,
    )


def capture(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    manifest = _manifest.read(slug, base)
    engine = manifest.get("stages", {}).get("engine", {})
    if engine.get("status") != "done":
        raise ValueError("Stage 6 requires stages.engine.status == done before capture")

    project = _validate_project(args.project)
    output = _iter_dir(slug, base, args.iter)
    source = _asset_res_path(manifest)

    if _common.is_dry_run():
        _copy_dry_run(output, slug, source)
    else:
        godot = _locate_godot(args.godot)
        _sync_addon(project)
        if args.apply_fixes:
            _run_apply_fixes(godot, project, slug, args.apply_fixes)
        _run_capture(godot, project, slug, source, output)

    screenshots = _verify_pngs(output)
    return _update_review_stage(slug, base, args.iter, output, screenshots)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Stage 6 Godot review screenshots")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--project", required=True, help="absolute path to a Godot project root")
    parser.add_argument("--iter", required=True, type=int, help="review iteration number")
    parser.add_argument("--godot", help="path to Godot executable")
    parser.add_argument("--apply-fixes", help="fix-instructions.json to apply before capture")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = capture(args.slug, args)
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, RuntimeError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR

    review = manifest["stages"]["review"]
    history = review.get("history") or []
    screenshot_count = len(history[-1].get("screenshots", [])) if history else 0
    print(
        "CAPTURED slug={slug} iter={iteration} status={status} screenshots={count}".format(
            slug=args.slug,
            iteration=args.iter,
            status=review.get("status"),
            count=screenshot_count,
        )
    )
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
