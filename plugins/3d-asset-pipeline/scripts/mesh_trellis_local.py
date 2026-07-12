from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _common, _local_backend, _manifest
except ImportError:
    import _common  # type: ignore
    import _local_backend  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("mesh_trellis_local")
VENDOR = "local:trellis2-spz"
BACKEND = "trellis2-stableprojectorz"
RESOLUTION_BY_MODE = {"rapid": 1024, "pro": 1536}
DEFAULT_MESH_SIMPLIFY = 50
EXIT_INTERNAL_ERROR = 4


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _asset_dir(slug: str, base: Path | None) -> Path:
    return _common.output_dir(slug, base)


def _rel(asset_dir: Path, path: Path) -> str:
    return path.relative_to(asset_dir).as_posix()


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _concept_image(manifest: dict[str, Any], asset_dir: Path) -> Path:
    concept = manifest.get("stages", {}).get("concept", {})
    files = concept.get("files") or {}
    canonical = files.get("canonical")
    if not canonical:
        raise ValueError("Concept stage is done but files.canonical is missing")
    path = asset_dir / str(canonical)
    if not path.exists():
        raise FileNotFoundError(f"Canonical concept image not found: {path}")
    return path


def _mesh_simplify_thousands(target_polys: int | None) -> int:
    if target_polys is None:
        return DEFAULT_MESH_SIMPLIFY
    thousands = round(target_polys / 1000)
    return max(10, min(1000, thousands))


def _sanitize(message: str, *, limit: int = 300) -> str:
    return message.strip()[:limit]


def _mark_failed(slug: str, base: Path | None, category: str, detail: str | None = None) -> None:
    error = category if not detail else f"{category}: {detail}"
    try:
        _manifest.update_stage(
            slug,
            "mesh",
            {"status": "failed", "error": error, "failedAt": _common.iso_now()},
            base,
        )
    except Exception:
        LOGGER.debug("Could not mark mesh stage as failed", exc_info=True)


def _validate_manifest(slug: str, base: Path | None) -> tuple[dict[str, Any], Path, Path]:
    manifest = _manifest.read(slug, base)
    concept = manifest.get("stages", {}).get("concept", {})
    if concept.get("status") != "done":
        raise ValueError("Stage 2 requires stages.concept.status == done before mesh generation")
    if not _manifest.concept_approved(manifest):
        raise ValueError(
            "Concept stage must be approved before mesh generation. "
            "Run /3d-pipeline:approve <slug> after reviewing concept/canonical.png."
        )
    asset_dir = _asset_dir(slug, base)
    return manifest, asset_dir, _concept_image(manifest, asset_dir)


def _copy_dry_run(slug: str, base: Path | None, asset_dir: Path) -> dict[str, Any]:
    mesh_dir = asset_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    source = _plugin_root() / "scripts" / "fixtures" / "mesh" / "dryrun.glb"
    target = mesh_dir / f"{slug}.glb"
    shutil.copyfile(source, target)
    files = {"glb": _rel(asset_dir, target)}
    return _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "done",
            "vendor": VENDOR,
            "backend": BACKEND,
            "local": True,
            "dryRun": True,
            "files": files,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)

    if args.input == "text":
        raise ValueError("local vendor requires image input")

    if args.style:
        LOGGER.warning(
            "The local TRELLIS.2 vendor ignores --style text; the concept image drives appearance"
        )

    manifest, asset_dir, image_path = _validate_manifest(slug, base)
    resolution = RESOLUTION_BY_MODE[args.mode]

    _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "in_progress",
            "vendor": VENDOR,
            "backend": BACKEND,
            "local": True,
            "mode": args.mode,
            "resolution": resolution,
            "input": args.input,
            "targetPolys": args.target_polys,
            "pbr": args.pbr,
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying local TRELLIS.2 GLB placeholder")
        return _copy_dry_run(slug, base, asset_dir)

    base_url = _local_backend.resolve_url(args.url)
    home = _local_backend.resolve_home(args.spz_home)

    try:
        _local_backend.ensure_server(base_url, home)
    except _local_backend.BackendUnreachable as exc:
        _mark_failed(slug, base, "backend_unreachable", str(exc))
        raise

    mesh_simplify_thousands = _mesh_simplify_thousands(args.target_polys)

    try:
        import requests

        glb_bytes = _local_backend.generate(
            base_url,
            image_path,
            resolution=resolution,
            mesh_simplify_thousands=mesh_simplify_thousands,
            texture_size=args.texture_size,
            apply_texture=bool(args.pbr),
            seed=args.seed,
        )
    except _local_backend.BackendBusy as exc:
        _mark_failed(slug, base, "backend_busy", str(exc))
        raise
    except _local_backend.BackendUnreachable as exc:
        _mark_failed(slug, base, "backend_unreachable", str(exc))
        raise
    except _local_backend.GenerationFailed as exc:
        _mark_failed(slug, base, "generation_failed", _sanitize(str(exc)))
        raise
    except (requests.exceptions.Timeout, TimeoutError) as exc:
        detail = _sanitize(str(exc))
        _mark_failed(slug, base, "local_timeout", detail)
        raise TimeoutError(detail) from exc
    except Exception as exc:
        _mark_failed(slug, base, "generation_failed", _sanitize(str(exc)))
        raise

    mesh_dir = asset_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    glb_path = mesh_dir / f"{slug}.glb"
    _common.atomic_write_bytes(glb_path, glb_bytes)

    return _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "done",
            "vendor": VENDOR,
            "backend": BACKEND,
            "local": True,
            "mode": args.mode,
            "files": {"glb": _rel(asset_dir, glb_path)},
            "resolution": resolution,
            "seed": args.seed,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Stage 2 mesh with the local TRELLIS.2 (trellis2-stableprojectorz) backend"
    )
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--mode", choices=("rapid", "pro"), default="rapid")
    parser.add_argument("--input", choices=("text", "image"), default="image")
    parser.add_argument("--target-polys", type=int)
    parser.add_argument("--pbr", dest="pbr", action="store_true", default=True)
    parser.add_argument("--no-pbr", dest="pbr", action="store_false")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--style")
    parser.add_argument("--texture-size", type=int, default=2048)
    parser.add_argument("--url", help="local TRELLIS.2 backend base URL; overrides TRELLIS2_SPZ_URL")
    parser.add_argument(
        "--spz-home",
        help="TRELLIS.2-stableprojectorz install directory; overrides TRELLIS2_SPZ_HOME and enables auto-start",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = generate(args.slug, args)
    except (FileNotFoundError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except TimeoutError as exc:
        LOGGER.error("%s", exc)
        return EXIT_INTERNAL_ERROR
    except Exception as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_API_ERROR

    mesh = manifest["stages"]["mesh"]
    print(f"Mesh stage {mesh['status']} for {args.slug}")
    print(f"vendor: {mesh.get('vendor')}")
    for label, path in sorted((mesh.get("files") or {}).items()):
        print(f"{label}: {path}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
