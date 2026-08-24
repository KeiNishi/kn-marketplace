"""Create the manifest for one audio asset.

Writes `audio-pipeline-output/<slug>/pipeline.json` with schema 1.0 defaults for
the asset type, then prints where it landed. Every later stage reads this file.

Usage:
    python init_asset.py door-open --type se --mode manual --prompt "wooden door creaking open, interior, close mic"
    python init_asset.py boss-theme --type bgm --mode auto --duration 90 --bpm 140
    python init_asset.py whoosh-b --type se --reference ./refs/whoosh.wav --reference-strength 0.9

(On Windows, use `py -3` if `python3` is not available.)
"""

from __future__ import annotations

import argparse
import pathlib
import sys

try:
    from . import _common, _manifest
except ImportError:  # executed as a script, not as a package module
    import _common  # type: ignore
    import _manifest  # type: ignore


LOGGER = _common.setup_logger("audio-init")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the manifest for one audio asset")
    parser.add_argument("slug", help="asset slug, e.g. 'door-open' (lowercase, digits, hyphens)")
    parser.add_argument(
        "--type",
        dest="asset_type",
        choices=_manifest.ASSET_TYPES,
        required=True,
        help="se for a sound effect, bgm for background music",
    )
    parser.add_argument(
        "--mode",
        choices=_manifest.MODES,
        default="manual",
        help="manual generates several candidates to choose from, auto takes the first (default: manual)",
    )
    parser.add_argument("--prompt", default=None, help="what the sound should be")
    parser.add_argument("--duration", type=float, default=None, help="target length in seconds")
    parser.add_argument("--reference", default=None, help="path to a reference audio file")
    parser.add_argument(
        "--reference-strength",
        type=float,
        default=None,
        help="0.0-1.0; higher stays closer to the reference (default: 0.7)",
    )
    parser.add_argument("--bpm", type=int, default=None, help="tempo, for BGM")
    parser.add_argument(
        "--loop",
        dest="loop",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="whether the asset must loop seamlessly (default: on for bgm, off for se)",
    )
    parser.add_argument(
        "--vocals",
        dest="vocals",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="whether the asset should contain vocals (default: off)",
    )
    parser.add_argument(
        "--lyrics",
        default=None,
        help="lyrics for a vocal track; required by the music backend when --vocals is set",
    )
    parser.add_argument("--base", default=None, help="workspace to hold audio-pipeline-output/")
    args = parser.parse_args(argv)

    base = pathlib.Path(args.base).expanduser().resolve() if args.base else None

    # Only pass what the user actually set, so the per-type defaults still apply.
    requirement = {
        key: value
        for key, value in (
            ("prompt", args.prompt),
            ("durationSeconds", args.duration),
            ("referenceAudio", args.reference),
            ("referenceStrength", args.reference_strength),
            ("bpm", args.bpm),
            ("loop", args.loop),
            ("vocals", args.vocals),
            ("lyrics", args.lyrics),
        )
        if value is not None
    }

    try:
        manifest = _manifest.init(args.slug, args.asset_type, args.mode, requirement, base)
    except FileExistsError as exc:
        LOGGER.error("%s Edit it directly, or pick another slug.", exc)
        return _common.EXIT_USER_ERROR
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR

    path = _manifest.manifest_path(args.slug, base)
    need = manifest["requirement"]
    print(f"Created {path.as_posix()}")
    print(
        f"  {manifest['assetType']} / {manifest['mode']} mode, "
        f"{need['durationSeconds']:g}s, loop={need['loop']}"
    )
    print(f"  prompt: {need['prompt'] or '(none yet - set requirement.prompt before generating)'}")
    if need["referenceAudio"]:
        print(f"  reference: {need['referenceAudio']} (strength {need['referenceStrength']:g})")
    print("Next: run the generate stage for this slug.")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
