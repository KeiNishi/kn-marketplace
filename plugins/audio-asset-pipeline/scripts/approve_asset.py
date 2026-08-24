"""Record which generated candidate is the one, and whether a human approved it.

Two separate facts, deliberately:

* `stages.generate.selected` says which take the post stage will finish. Auto
  mode sets it by itself (`post_process.auto_select`), so selection alone is not
  a human judgement.
* `stages.generate.approved` says a person listened. Manual-mode assets cannot
  leave the generate stage without it - `post_process.py` refuses.

Usage:
    python approve_asset.py <slug> --select generate/cand-02.wav --approve
    python approve_asset.py <slug> --select generate/cand-03.wav
    python approve_asset.py <slug> --approve
    python approve_asset.py <slug> --reject

Run it from the workspace that contains `audio-pipeline-output/`, or pass
`--base <workspace>`. (On Windows, use `py -3` if `python3` is not available.)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
for _extra in (_SCRIPTS_DIR, _SCRIPTS_DIR / "backends"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import _common  # noqa: E402
import _manifest  # noqa: E402
import _backend_common as backend  # noqa: E402


LOGGER = _common.setup_logger("audio-approve")


def candidate_listing(candidates: list[dict]) -> str:
    lines = []
    for entry in candidates:
        params = entry.get("params") or {}
        lines.append(
            f"  {entry.get('file')}  seed={entry.get('seed')}  "
            f"backend={entry.get('backend')}{backend.silence_note(params)}"
        )
    return "\n".join(lines) or "  (none)"


def resolve_candidate(
    manifest: dict, slug: str, wanted: str, base: pathlib.Path | None
) -> dict:
    """The candidate entry for `wanted`, proven to exist on disk.

    Both halves matter. A file that is not in `candidates` is not something this
    pipeline made, and a manifest entry whose file has been deleted or renamed
    would send the post stage looking for audio that is not there - after the
    approval had already been recorded.
    """
    candidates = [
        entry
        for entry in (manifest["stages"]["generate"].get("candidates") or [])
        if isinstance(entry, dict)
    ]
    relative = _common.relative_artifact_path(wanted, "--select")
    entry = next((item for item in candidates if item.get("file") == relative), None)
    if entry is None:
        raise ValueError(
            f"{wanted!r} is not one of this asset's candidates.\n{candidate_listing(candidates)}"
        )

    path = _common.resolve_inside(_common.output_dir(slug, base), relative, "the candidate")
    if not path.is_file():
        raise ValueError(
            f"{relative} is recorded in the manifest but is not on disk "
            f"({path.as_posix()}). Re-run the generate stage, or pick another candidate.\n"
            + candidate_listing(candidates)
        )
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select and/or approve one generated candidate of an audio asset"
    )
    parser.add_argument("slug", help="asset slug with an existing pipeline.json")
    parser.add_argument(
        "--select",
        default=None,
        metavar="FILE",
        help="candidate to finish, e.g. generate/cand-02.wav (must be a recorded candidate)",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--approve", action="store_true", help="record that a human approved the selection"
    )
    action.add_argument(
        "--reject", action="store_true", help="withdraw a previous approval (keeps the selection)"
    )
    parser.add_argument("--base", default=None, help="workspace holding audio-pipeline-output/")
    args = parser.parse_args(argv)

    if not (args.select or args.approve or args.reject):
        parser.error("nothing to do; pass --select, --approve and/or --reject")

    base = pathlib.Path(args.base).expanduser().resolve() if args.base else None
    try:
        manifest = _manifest.read(args.slug, base)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR
    except (ValueError, json.JSONDecodeError) as exc:
        LOGGER.error("Manifest is not usable: %s", exc)
        return _common.EXIT_MANIFEST_CORRUPT

    generate = manifest["stages"]["generate"]
    fields: dict = {}
    try:
        if args.select:
            resolve_candidate(manifest, args.slug, args.select, base)
            fields["selected"] = _common.relative_artifact_path(args.select, "--select")
            # Moving the selection to a different take invalidates an approval
            # that was given for the old one. `generation_approved` already
            # refuses the mismatch via approvedFile; clearing the flags here as
            # well keeps the manifest from *displaying* a stale "approved: true".
            if not args.approve and fields["selected"] != manifest["stages"]["generate"].get(
                "selected"
            ):
                fields.update(approved=False, approvedAt=None, approvedBy=None, approvedFile=None)

        if args.reject:
            fields.update(approved=False, approvedAt=None, approvedBy=None, approvedFile=None)
        elif args.approve:
            if generate.get("status") != "done":
                raise ValueError(
                    f"cannot approve: stages.generate.status is {generate.get('status')!r}, "
                    "expected 'done'. Run the generate stage first."
                )
            # Approving with no --select only makes sense against a selection
            # that is already there - and it is re-checked on disk here, because
            # it may have been recorded by an earlier run or by auto mode.
            chosen = fields.get("selected") or generate.get("selected")
            if not chosen:
                raise ValueError(
                    "cannot approve: no candidate is selected. Pass "
                    f"--select generate/cand-NN.wav.\n"
                    + candidate_listing(
                        [e for e in (generate.get("candidates") or []) if isinstance(e, dict)]
                    )
                )
            resolve_candidate(manifest, args.slug, chosen, base)
            fields.update(
                approved=True,
                approvedAt=_common.iso_now(),
                approvedBy="user",
                approvedFile=chosen,
            )

        manifest = _manifest.update_stage(args.slug, "generate", fields, base)
    except (ValueError, OSError) as exc:
        LOGGER.error("%s", exc)
        return _common.EXIT_USER_ERROR

    generate = manifest["stages"]["generate"]
    print(f"Asset '{args.slug}' ({manifest['mode']} mode)")
    print(f"  selected   {generate.get('selected') or '(none)'}")
    print(
        f"  approved   {bool(generate.get('approved'))}"
        + (f"  at {generate['approvedAt']} by {generate['approvedBy']}"
           if generate.get("approved") else "")
    )
    if generate.get("approved") and not _manifest.generation_approved(manifest):
        print(
            f"  NOTE     the approval was given for {generate.get('approvedFile')}, "
            "which is not the current selection, so the post stage stays blocked."
        )
    if _manifest.generation_approved(manifest):
        print(f"Next: python post_process.py {args.slug}")
    elif generate.get("selected") and manifest["mode"] == "manual":
        print("Next: re-run with --approve once you have listened to the selected take "
              "(the post stage refuses until then).")
    return _common.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
