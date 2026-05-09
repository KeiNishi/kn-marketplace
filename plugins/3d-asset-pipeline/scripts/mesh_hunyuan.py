from __future__ import annotations

import argparse
import base64
import mimetypes
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _common, _credentials, _manifest
except ImportError:
    import _common  # type: ignore
    import _credentials  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("mesh_hunyuan")
VENDOR = "replicate:hunyuan-3d-3.1"
MODEL = "tencent/hunyuan-3d-3.1"
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


def _description(manifest: dict[str, Any], style: str | None) -> str:
    description = str(manifest.get("description") or manifest.get("name") or manifest["slug"]).strip()
    if style:
        return f"{description}. Style guidance: {style.strip()}"
    return description


def _prediction_value(prediction: Any, key: str, default: Any = None) -> Any:
    if isinstance(prediction, dict):
        return prediction.get(key, default)
    return getattr(prediction, key, default)


def _extract_url(output: Any) -> str:
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    if isinstance(output, list):
        for item in output:
            try:
                return _extract_url(item)
            except ValueError:
                continue
    if isinstance(output, dict):
        for key in ("glb", "model", "model_url", "url", "output"):
            value = output.get(key)
            try:
                return _extract_url(value)
            except ValueError:
                continue
    raise ValueError("Replicate prediction output did not include a downloadable GLB URL")


def _sanitize(message: str, token: str | None = None) -> str:
    cleaned = message
    if token:
        cleaned = cleaned.replace(token, "<redacted>")
    return cleaned[:500]


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
    asset_dir = _asset_dir(slug, base)
    return manifest, asset_dir, _concept_image(manifest, asset_dir)


def _copy_dry_run(slug: str, base: Path | None, asset_dir: Path, edition: str) -> dict[str, Any]:
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
            "edition": edition,
            "predictionId": None,
            "dryRun": True,
            "files": files,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(slug: str, args: argparse.Namespace) -> dict[str, Any]:
    base = _base_dir(args.base)
    manifest, asset_dir, image_path = _validate_manifest(slug, base)
    edition = "Pro" if args.mode == "pro" else "Rapid"
    prompt = _description(manifest, args.style)

    _manifest.update_stage(
        slug,
        "mesh",
        {
            "status": "in_progress",
            "vendor": VENDOR,
            "edition": edition,
            "input": args.input,
            "targetPolys": args.target_polys,
            "pbr": args.pbr,
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; copying Hunyuan GLB placeholder")
        return _copy_dry_run(slug, base, asset_dir, edition)

    try:
        credentials = _credentials.require("REPLICATE_API_TOKEN")
    except ValueError as exc:
        _mark_failed(slug, base, "missing_credentials", str(exc))
        raise
    token = credentials["REPLICATE_API_TOKEN"]

    try:
        import replicate
        import requests

        client = replicate.Client(api_token=token)
        # Hunyuan 3D 3.1 accepts either `image` or `prompt`, not both.
        if args.input == "text":
            payload: dict[str, Any] = {"prompt": prompt, "edition": edition}
        else:
            mime, _ = mimetypes.guess_type(image_path.name)
            if not mime:
                mime = "image/png"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            payload = {"image": f"data:{mime};base64,{encoded}", "edition": edition}
        prediction = client.predictions.create(model=MODEL, input=payload)
        prediction_id = str(_prediction_value(prediction, "id") or "")
        if not prediction_id:
            raise RuntimeError("Replicate prediction did not include an id")

        def refresh() -> dict[str, Any]:
            current = client.predictions.get(prediction_id)
            return {
                "status": str(_prediction_value(current, "status", "")),
                "prediction": current,
            }

        result = _common.poll(
            refresh,
            interval=5,
            timeout=600,
            status_done={"succeeded"},
            status_failed={"failed", "canceled"},
        )
        output_url = _extract_url(_prediction_value(result["prediction"], "output"))
        response = requests.get(output_url, timeout=120)
        if response.status_code >= 400:
            raise RuntimeError(f"GLB download failed with HTTP {response.status_code}")

        mesh_dir = asset_dir / "mesh"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        glb_path = mesh_dir / f"{slug}.glb"
        _common.atomic_write_bytes(glb_path, response.content)

        return _manifest.update_stage(
            slug,
            "mesh",
            {
                "status": "done",
                "vendor": VENDOR,
                "edition": edition,
                "predictionId": prediction_id,
                "files": {"glb": _rel(asset_dir, glb_path)},
                "completedAt": _common.iso_now(),
            },
            base,
        )
    except TimeoutError as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "replicate_timeout", detail)
        raise
    except Exception as exc:
        detail = _sanitize(str(exc), token)
        _mark_failed(slug, base, "replicate_api_failed", detail)
        raise


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Stage 2 mesh with Hunyuan 3D 3.1 on Replicate")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--mode", choices=("rapid", "pro"), default="rapid")
    parser.add_argument("--input", choices=("text", "image"), default="image")
    parser.add_argument("--target-polys", type=int)
    parser.add_argument("--pbr", dest="pbr", action="store_true", default=True)
    parser.add_argument("--no-pbr", dest="pbr", action="store_false")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--style")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = _base_dir(args.base)
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
