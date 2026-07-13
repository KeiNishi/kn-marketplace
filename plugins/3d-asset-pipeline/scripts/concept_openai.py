from __future__ import annotations

import argparse
import base64
import os
import shutil
from pathlib import Path
from typing import Any

try:
    from . import _codex_backend, _common, _credentials, _manifest
except ImportError:
    import _codex_backend  # type: ignore
    import _common  # type: ignore
    import _credentials  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("concept_openai")
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "auto"
ENDPOINT = "https://api.openai.com/v1/images/generations"
ANGLES: dict[str, str] = {
    "front": "front view, full body or full object visible, neutral pose, facing camera",
    "three-quarter": "three-quarter view from camera-left, slight downward camera tilt, neutral pose",
    "side": "left side view, full silhouette visible, neutral pose",
    "back": "back view, full body or full object visible, neutral pose",
}
ANGLE_ALIASES = {
    "3q": "three-quarter",
    "three-quarter": "three-quarter",
    "three_quarter": "three-quarter",
    "threequarter": "three-quarter",
}

# 1x1 PNG used for dry-run output. Real-looking fixtures can be added later without
# changing the manifest contract.
DRY_RUN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class ModerationBlocked(RuntimeError):
    """OpenAI rejected the image request for moderation reasons."""


def _normalize_angle(angle: str) -> str:
    value = angle.strip().lower()
    value = ANGLE_ALIASES.get(value, value)
    if value not in ANGLES:
        allowed = ", ".join(ANGLES)
        raise ValueError(f"Invalid canonical angle: {angle}. Expected one of: {allowed}")
    return value


def _base_dir(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _rel(asset_dir: Path, path: Path) -> str:
    return path.relative_to(asset_dir).as_posix()


def build_prompts(manifest: dict[str, Any], style: str, reference_notes: list[str]) -> dict[str, str]:
    name = str(manifest.get("name") or manifest["slug"])
    description = str(manifest.get("description") or "").strip()
    asset_type = str(manifest.get("assetType") or "asset")
    references = ""
    if reference_notes:
        references = "Reference notes: " + "; ".join(reference_notes) + "\n"

    anchor = (
        f"Create production concept art for a Godot 4 3D game asset named {name}.\n"
        f"Asset type: {asset_type}.\n"
        f"Description: {description}\n"
        f"{references}"
        f"Style anchor: {style}. Keep the same character, creature, or prop design across all views. "
        "Use clean readable forms, material and color consistency, neutral studio lighting, a plain background, "
        "and no text labels, callouts, watermark, UI, or signature."
    )

    return {
        angle: f"{anchor}\nCamera requirement: {clause}."
        for angle, clause in ANGLES.items()
    }


def _extract_png_bytes(response_json: dict[str, Any], api_key: str) -> bytes:
    data = response_json.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("OpenAI image response did not include data")

    first = data[0]
    if not isinstance(first, dict):
        raise RuntimeError("OpenAI image response data item was not an object")

    encoded = first.get("b64_json")
    if isinstance(encoded, str) and encoded:
        return base64.b64decode(encoded)

    url = first.get("url")
    if isinstance(url, str) and url:
        import requests

        result = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
        )
        if result.status_code >= 400:
            raise RuntimeError(f"OpenAI image download failed with HTTP {result.status_code}")
        return result.content

    raise RuntimeError("OpenAI image response did not include b64_json or url")


def _request_image(api_key: str, prompt: str, *, model: str, size: str, quality: str) -> tuple[bytes, str | None]:
    import requests

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "output_format": "png",
    }
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    request_id = response.headers.get("x-request-id") or response.headers.get("openai-request-id")
    if response.status_code >= 400:
        try:
            body = response.json()
        except ValueError:
            body = {}
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict) and error.get("code") == "moderation_blocked":
            message = str(error.get("message") or "OpenAI image generation was blocked by moderation")
            raise ModerationBlocked(message.replace(api_key, "<redacted>"))
        detail = response.text[:500].replace(api_key, "<redacted>")
        raise RuntimeError(f"OpenAI image generation failed with HTTP {response.status_code}: {detail}")
    return _extract_png_bytes(response.json(), api_key), request_id


def select_canonical(slug: str, angle: str, *, base: Path | None = None) -> dict[str, Any]:
    selected = _normalize_angle(angle)
    asset_dir = _common.output_dir(slug, base)
    concept_dir = asset_dir / "concept"
    source = concept_dir / f"{selected}.png"
    if not source.exists():
        raise FileNotFoundError(f"Concept image not found for angle {selected}: {source}")

    target = concept_dir / "canonical.png"
    shutil.copyfile(source, target)

    manifest = _manifest.read(slug, base)
    concept = dict(manifest["stages"]["concept"])
    files = dict(concept.get("files") or {})
    files["canonical"] = _rel(asset_dir, target)
    files["canonicalSource"] = files.get(selected, _rel(asset_dir, source))

    return _manifest.update_stage(
        slug,
        "concept",
        {
            "status": "done",
            "files": files,
            "canonicalAngle": selected,
            "completedAt": _common.iso_now(),
        },
        base,
    )


def generate(
    slug: str,
    *,
    base: Path | None,
    style: str,
    model: str,
    size: str,
    quality: str,
    references: list[str],
    canonical: str | None,
    backend: str | None = None,
) -> dict[str, Any]:
    manifest = _manifest.read(slug, base)
    asset_dir = _common.output_dir(slug, base)
    concept_dir = asset_dir / "concept"
    concept_dir.mkdir(parents=True, exist_ok=True)
    reference_notes = [Path(path).name for path in references]
    prompts = build_prompts(manifest, style, reference_notes)

    # Backend resolution has real-world side effects (spawns `codex login
    # status`) and must not run in dry-run mode, so today's dry-run output
    # (vendor/endpoint always "openai") stays byte-for-byte identical.
    resolved_backend = "openai"
    if not _common.is_dry_run():
        resolved_backend, backend_detail = _codex_backend.resolve_backend(backend)
        LOGGER.info("Concept backend resolved to %s (%s)", resolved_backend, backend_detail)

    vendor = f"openai:{model}" if resolved_backend == "openai" else "codex:gpt-image-2"
    endpoint = ENDPOINT if resolved_backend == "openai" else "codex-cli"

    _manifest.update_stage(
        slug,
        "concept",
        {
            "status": "in_progress",
            "vendor": vendor,
            "endpoint": endpoint,
            "prompts": prompts,
            "references": references,
            "dryRun": _common.is_dry_run(),
            "startedAt": _common.iso_now(),
        },
        base,
    )

    request_ids: list[str] = []
    files: dict[str, str] = {}
    if _common.is_dry_run():
        LOGGER.info("PIPELINE_DRY_RUN=1; writing placeholder concept PNGs")
        for angle in ANGLES:
            path = concept_dir / f"{angle}.png"
            _common.atomic_write_bytes(path, DRY_RUN_PNG)
            files[angle] = _rel(asset_dir, path)
    elif resolved_backend == "codex":
        for angle, prompt in prompts.items():
            LOGGER.info("Generating %s concept view with Codex CLI", angle)
            path = concept_dir / f"{angle}.png"
            _codex_backend.generate_image(prompt, path)
            files[angle] = _rel(asset_dir, path)
    else:
        credentials = _credentials.require("OPENAI_API_KEY")
        api_key = credentials["OPENAI_API_KEY"]
        for angle, prompt in prompts.items():
            LOGGER.info("Generating %s concept view with OpenAI", angle)
            png, request_id = _request_image(api_key, prompt, model=model, size=size, quality=quality)
            path = concept_dir / f"{angle}.png"
            _common.atomic_write_bytes(path, png)
            files[angle] = _rel(asset_dir, path)
            if request_id:
                request_ids.append(request_id)

    _manifest.update_stage(
        slug,
        "concept",
        {
            "status": "in_progress" if canonical is None else "done",
            "vendor": vendor,
            "requestIds": request_ids,
            "prompts": prompts,
            "files": files,
            "dryRun": _common.is_dry_run(),
        },
        base,
    )

    if canonical is not None:
        return select_canonical(slug, canonical, base=base)

    return _manifest.read(slug, base)


def _mark_failed(slug: str, base: Path | None, message: str, *, failure_kind: str = "api_error") -> None:
    try:
        _manifest.update_stage(
            slug,
            "concept",
            {
                "status": "failed",
                "error": message,
                "failureKind": failure_kind,
                "failedAt": _common.iso_now(),
            },
            base,
        )
    except Exception:
        LOGGER.debug("Could not mark concept stage as failed", exc_info=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Stage 1 concept art with OpenAI images")
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument("--base", help="output base directory; defaults to git root or cwd")
    parser.add_argument("--style", default="stylized realistic game concept art with PBR-friendly material cues")
    parser.add_argument(
        "--backend",
        choices=("auto", "codex", "openai"),
        default=None,
        help=(
            "image generation backend: 'codex' uses the Codex CLI's built-in gpt-image-2 tool "
            "(covered by a ChatGPT subscription, no API key), 'openai' uses the OpenAI images API "
            "(requires OPENAI_API_KEY, pay-per-use). Default 'auto' picks codex when a subscription "
            "is active, else falls back to openai. Also configurable via PIPELINE_CONCEPT_BACKEND."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "OpenAI image model; defaults to gpt-image-2 or PIPELINE_OPENAI_IMAGE_MODEL. "
            "Only applies to the openai backend -- the codex backend always uses its built-in gpt-image-2."
        ),
    )
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--reference", action="append", default=[], help="reference note/path recorded in the manifest")
    parser.add_argument("--canonical", default="front", help="canonical angle to copy after generation")
    parser.add_argument("--defer-canonical", action="store_true", help="leave stage in_progress for manual canonical selection")
    parser.add_argument("--select-canonical", help="copy an already generated angle to concept/canonical.png")
    parser.add_argument("--description", help="replace manifest description and reset the concept stage before generating")
    return parser.parse_args(argv)


def _reset_description(slug: str, base: Path | None, description: str) -> None:
    manifest = _manifest.read(slug, base)
    manifest["description"] = description
    manifest["stages"]["concept"] = {"status": "pending"}
    manifest["updatedAt"] = _common.iso_now()
    _manifest.validate(manifest)
    _common.atomic_write_json(_manifest.manifest_path(slug, base), manifest)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = _base_dir(args.base)
    model = args.model or os.environ.get("PIPELINE_OPENAI_IMAGE_MODEL") or DEFAULT_MODEL

    try:
        if args.select_canonical:
            manifest = select_canonical(args.slug, args.select_canonical, base=base)
        else:
            if args.description is not None:
                _reset_description(args.slug, base, args.description)
            canonical = None if args.defer_canonical else args.canonical
            manifest = generate(
                args.slug,
                base=base,
                style=args.style,
                model=model,
                size=args.size,
                quality=args.quality,
                references=args.reference,
                canonical=canonical,
                backend=args.backend,
            )
    except ModerationBlocked as exc:
        LOGGER.error("%s", exc)
        _mark_failed(args.slug, base, str(exc), failure_kind="moderation_blocked")
        return _common.EXIT_API_ERROR
    except _codex_backend.CodexBackendError as exc:
        LOGGER.error("%s", exc)
        failure_kind = "codex_usage_limit" if exc.usage_limit else "codex_error"
        _mark_failed(args.slug, base, str(exc), failure_kind=failure_kind)
        return _common.EXIT_API_ERROR
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        _mark_failed(args.slug, base, str(exc))
        return _common.EXIT_USER_ERROR
    except ValueError as exc:
        LOGGER.error("%s", exc)
        _mark_failed(args.slug, base, str(exc))
        return _common.EXIT_USER_ERROR
    except TimeoutError as exc:
        LOGGER.error("%s", exc)
        _mark_failed(args.slug, base, str(exc))
        return _common.EXIT_TIMEOUT
    except Exception as exc:
        LOGGER.error("%s", exc)
        _mark_failed(args.slug, base, str(exc), failure_kind="api_error")
        return _common.EXIT_API_ERROR

    concept = manifest["stages"]["concept"]
    print(f"Concept stage {concept['status']} for {args.slug}")
    for angle, path in sorted((concept.get("files") or {}).items()):
        print(f"{angle}: {path}")
    return _common.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
