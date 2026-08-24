"""Manifest helpers for audio-pipeline-output/<slug>/pipeline.json (schema 1.0).

Same surface as the 3d-asset-pipeline manifest module: init / read / save /
update_stage / validate plus an approval check. The manifest is a plain JSON
document written atomically; it never stores secrets (no tokens, no absolute
home paths beyond the artifacts the stages produce).

Self-check: `python _manifest.py --selftest`.
"""

from __future__ import annotations

import pathlib
from typing import Any

try:
    from . import _common
except ImportError:  # executed as a script, not as a package module
    import _common  # type: ignore


SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
ASSET_TYPES = ("bgm", "se")
MODES = ("auto", "manual")
STAGES = ("requirement", "generate", "post", "review")
STATUSES = {"pending", "in_progress", "done", "failed", "skipped"}

# Defaults tuned for game BGM; the SE overrides below shorten and un-loop them.
_REQUIREMENT_DEFAULTS: dict[str, Any] = {
    "prompt": "",
    "referenceAudio": None,
    "referenceStrength": 0.3,
    "durationSeconds": 60.0,
    "loop": True,
    "vocals": False,
    "lyrics": None,
    "bpm": 120,
    "timeSignature": "4/4",
    "styleTags": [],
    "targetLufs": -16.0,  # common game-music integrated loudness target
    "formats": ["wav", "ogg"],
}
_SE_OVERRIDES: dict[str, Any] = {
    "durationSeconds": 3.0,
    "loop": False,
    "bpm": None,
}


def manifest_path(slug: str, base: pathlib.Path | None = None) -> pathlib.Path:
    return _common.output_dir(slug, base) / "pipeline.json"


def default_requirement(asset_type: str) -> dict[str, Any]:
    requirement = dict(_REQUIREMENT_DEFAULTS)
    requirement["styleTags"] = []
    requirement["formats"] = list(_REQUIREMENT_DEFAULTS["formats"])
    if asset_type == "se":
        requirement.update(_SE_OVERRIDES)
    return requirement


def _stage_skeleton() -> dict[str, dict[str, Any]]:
    return {
        "requirement": {"status": "pending"},
        "generate": {
            "status": "pending",
            "backend": None,
            "attempts": 0,
            "candidates": [],
            "selected": None,
            "approved": False,
            "approvedAt": None,
            "approvedBy": None,
            "failureKind": None,
        },
        "post": {"status": "pending", "loopProcessing": None, "normalize": None, "outputs": []},
        "review": {"status": "pending", "checks": None, "clapScore": None, "verdict": None},
    }


def _check_backend(backend: Any, field: str) -> None:
    if backend not in _common.STACKS:
        raise ValueError(f"{field} must be one of {list(_common.STACKS)}, got {backend!r}")


def make_candidate(
    file: str,
    seed: int,
    backend: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one entry for stages.generate.candidates."""
    _check_backend(backend, "candidate backend")
    return {
        "file": _common.relative_artifact_path(file, "candidate file"),
        "seed": int(seed),
        "backend": backend,
        "params": dict(params or {}),
        "createdAt": _common.iso_now(),
    }


def init(
    slug: str,
    asset_type: str,
    mode: str,
    requirement: dict[str, Any] | None = None,
    base: pathlib.Path | None = None,
) -> dict[str, Any]:
    _common.validate_slug(slug)
    if asset_type not in ASSET_TYPES:
        raise ValueError(f"Invalid assetType: {asset_type!r}; expected one of {list(ASSET_TYPES)}")
    if mode not in MODES:
        raise ValueError(f"Invalid mode: {mode!r}; expected one of {list(MODES)}")

    path = manifest_path(slug, base)
    if path.exists():
        raise FileExistsError(f"Manifest already exists: {path}")

    merged = default_requirement(asset_type)
    for key, value in (requirement or {}).items():
        if key not in _REQUIREMENT_DEFAULTS:
            raise ValueError(
                f"Unknown requirement field: {key!r}; expected one of "
                f"{sorted(_REQUIREMENT_DEFAULTS)}"
            )
        merged[key] = value

    now = _common.iso_now()
    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "slug": slug,
        "assetType": asset_type,
        "mode": mode,
        "createdAt": now,
        "updatedAt": now,
        "dryRun": _common.is_dry_run(),
        "requirement": merged,
        "stages": _stage_skeleton(),
    }
    validate(manifest)
    _common.atomic_write_json(path, manifest)
    return manifest


def read(slug: str, base: pathlib.Path | None = None) -> dict[str, Any]:
    path = manifest_path(slug, base)
    manifest = _common.read_json(path)
    if manifest is None:
        raise FileNotFoundError(
            f"No manifest at {path}. Initialize the asset before running a stage."
        )
    validate(manifest)
    return manifest


def save(manifest: dict[str, Any], base: pathlib.Path | None = None) -> dict[str, Any]:
    validate(manifest)
    manifest["updatedAt"] = _common.iso_now()
    _common.atomic_write_json(manifest_path(manifest["slug"], base), manifest)
    return manifest


def update_stage(
    slug: str,
    stage: str,
    fields: dict[str, Any],
    base: pathlib.Path | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage!r}; expected one of {list(STAGES)}")
    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"Invalid status: {fields['status']!r}; expected one of {sorted(STATUSES)}")

    manifest = read(slug, base)
    manifest["stages"][stage].update(fields)
    return save(manifest, base)


def update_requirement(
    slug: str,
    fields: dict[str, Any],
    base: pathlib.Path | None = None,
) -> dict[str, Any]:
    unknown = [key for key in fields if key not in _REQUIREMENT_DEFAULTS]
    if unknown:
        raise ValueError(
            f"Unknown requirement fields: {unknown}; expected a subset of "
            f"{sorted(_REQUIREMENT_DEFAULTS)}"
        )
    manifest = read(slug, base)
    manifest["requirement"].update(fields)
    return save(manifest, base)


def validate(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object")
    if manifest.get("schemaVersion") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schemaVersion: {manifest.get('schemaVersion')!r}; "
            f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    _common.validate_slug(manifest.get("slug", ""))
    if manifest.get("assetType") not in ASSET_TYPES:
        raise ValueError(f"Invalid assetType: {manifest.get('assetType')!r}")
    if manifest.get("mode") not in MODES:
        raise ValueError(f"Invalid mode: {manifest.get('mode')!r}")

    requirement = manifest.get("requirement")
    if not isinstance(requirement, dict):
        raise ValueError("Manifest requirement must be an object")
    duration = requirement.get("durationSeconds")
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError(f"requirement.durationSeconds must be a positive number: {duration!r}")
    if not isinstance(requirement.get("formats"), list) or not requirement["formats"]:
        raise ValueError("requirement.formats must be a non-empty list")

    stages = manifest.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("Manifest stages must be an object")
    for stage in STAGES:
        stage_data = stages.get(stage)
        if not isinstance(stage_data, dict):
            raise ValueError(f"Missing or malformed stage: {stage}")
        if stage_data.get("status") not in STATUSES:
            raise ValueError(f"Invalid status for stage {stage}: {stage_data.get('status')!r}")

    _validate_generate(stages["generate"])

    outputs = stages["post"].get("outputs")
    if not isinstance(outputs, list):
        raise ValueError("stages.post.outputs must be a list")
    for index, output in enumerate(outputs):
        if isinstance(output, str):
            _common.relative_artifact_path(output, f"stages.post.outputs[{index}]")


def _validate_generate(generate: dict[str, Any]) -> None:
    """The approval gate lives here, so every field it reads is type-checked.

    A truthy-but-wrong value (the string "false", a stray dict) must never be
    able to pass for an approval.
    """
    approved = generate.get("approved")
    if not isinstance(approved, bool):
        raise ValueError(f"stages.generate.approved must be a boolean, got {approved!r}")

    attempts = generate.get("attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        raise ValueError(f"stages.generate.attempts must be an integer >= 0, got {attempts!r}")

    candidates = generate.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("stages.generate.candidates must be a list")
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"stages.generate.candidates[{index}] must be an object")
        _common.relative_artifact_path(candidate.get("file"), f"candidates[{index}].file")
        _check_backend(candidate.get("backend"), f"candidates[{index}].backend")

    backend = generate.get("backend")
    if backend is not None:
        _check_backend(backend, "stages.generate.backend")

    selected = generate.get("selected")
    if selected is not None:
        _common.relative_artifact_path(selected, "stages.generate.selected")


def generation_approved(manifest: dict[str, Any]) -> bool:
    """True only when an existing candidate is selected AND explicitly approved."""
    generate = manifest.get("stages", {}).get("generate", {})
    if generate.get("approved") is not True:
        return False
    selected = generate.get("selected")
    candidates = generate.get("candidates")
    if not selected or not isinstance(candidates, list):
        return False
    return any(
        isinstance(candidate, dict) and candidate.get("file") == selected
        for candidate in candidates
    )


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        bgm = init("boss-battle-theme", "bgm", "auto", {"prompt": "orchestral boss fight"}, base)
        assert bgm["requirement"]["loop"] is True
        assert bgm["requirement"]["durationSeconds"] == 60.0
        assert bgm["stages"]["generate"]["attempts"] == 0
        assert generation_approved(bgm) is False

        se = init("door-open", "se", "manual", base=base)
        assert se["requirement"]["loop"] is False and se["requirement"]["durationSeconds"] == 3.0

        candidate = make_candidate("generate/cand-01.wav", 123, "acestep", {"steps": 30})
        updated = update_stage(
            "boss-battle-theme",
            "generate",
            {
                "status": "done",
                "backend": "acestep",
                "attempts": 1,
                "candidates": [candidate],
                "selected": candidate["file"],
                "approved": True,
                "approvedAt": _common.iso_now(),
                "approvedBy": "user",
            },
            base,
        )
        assert generation_approved(updated) is True
        assert read("boss-battle-theme", base)["stages"]["generate"]["selected"] == candidate["file"]

        # A selected file that is not among the candidates is not an approval.
        forged = read("boss-battle-theme", base)
        forged["stages"]["generate"]["selected"] = "generate/never-generated.wav"
        assert generation_approved(forged) is False

        for bad in (
            lambda: init("boss-battle-theme", "bgm", "auto", base=base),  # duplicate
            lambda: init("Bad Slug", "bgm", "auto", base=base),
            lambda: init("nul", "bgm", "auto", base=base),  # Windows device name
            lambda: init("x", "sfx", "auto", base=base),
            lambda: init("x", "bgm", "semi", base=base),
            lambda: init("x", "bgm", "auto", {"tempo": 90}, base),
            lambda: update_stage("boss-battle-theme", "mixdown", {}, base),
            lambda: update_stage("boss-battle-theme", "post", {"status": "almost"}, base),
            lambda: update_requirement("boss-battle-theme", {"volume": 1.0}, base),
            lambda: make_candidate("C:/weights/leak.wav", 1, "acestep"),
            lambda: make_candidate("../../escape.wav", 1, "acestep"),
            lambda: make_candidate("/etc/passwd", 1, "acestep"),
            lambda: make_candidate("generate/ok.wav", 1, "suno"),  # unknown backend
        ):
            try:
                bad()
            except (ValueError, FileExistsError):
                continue
            raise AssertionError("expected the invalid manifest operation to raise")

        # Hand-edited manifests must not slip past validate().
        for mutate in (
            lambda m: m["requirement"].__setitem__("durationSeconds", 0),
            lambda m: m["stages"]["generate"].__setitem__("approved", "false"),
            lambda m: m["stages"]["generate"].__setitem__("attempts", -1),
            lambda m: m["stages"]["generate"].__setitem__("attempts", "1"),
            lambda m: m["stages"]["generate"].__setitem__("candidates", ["generate/a.wav"]),
            lambda m: m["stages"]["generate"].__setitem__("selected", "../outside.wav"),
            lambda m: m["stages"]["post"].__setitem__("outputs", ["C:/absolute.ogg"]),
        ):
            broken = read("boss-battle-theme", base)
            mutate(broken)
            try:
                validate(broken)
            except ValueError:
                continue
            raise AssertionError("expected the hand-edited manifest to fail validation")

    print("_manifest selftest: ok")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="audio-pipeline manifest helpers")
    parser.add_argument("--selftest", action="store_true", help="run the built-in assertions")
    args = parser.parse_args()
    if not args.selftest:
        parser.error("nothing to do; pass --selftest (this module is a library)")
    _selftest()
