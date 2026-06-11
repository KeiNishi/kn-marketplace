#!/usr/bin/env python3
"""Install kn-marketplace skills into an OpenAI Codex CLI skills directory.

Codex has no plugin system: it discovers SKILL.md files under its skills
directories (``~/.agents/skills`` on current versions, ``~/.codex/skills`` on
older ones). This script copies the marketplace plugins there so the same
skills work in both Claude Code and Codex. It uses plain copies (no symlinks)
so it works on Windows without Developer Mode.

Usage:
    python3 tools/install-codex-skills.py [--dest PATH] [--plugins NAME ...]
                                          [--flatten] [--dry-run] [--force]

Modes:
    default    Copy each plugin directory as a whole (e.g. dest/3d-asset-
               pipeline/skills/mesh-generation/SKILL.md). Preserves plugin-
               level shared resources such as scripts/. Requires a Codex
               version that discovers SKILL.md recursively.
    --flatten  Copy each skill directory to the destination root (e.g.
               dest/mesh-generation/SKILL.md) for Codex versions that only
               scan one level deep. Plugin-level shared resources (scripts/,
               requirements.txt, ...) are copied into each of that plugin's
               skill directories so relative references keep working.
"""

import argparse
import filecmp
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"

# Claude-Code-only plugin components that are meaningless to Codex.
PLUGIN_LEVEL_EXCLUDES = {".claude-plugin", "commands", "agents", "hooks"}
IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".DS_Store", "*-workspace"
)


def default_dest() -> Path:
    home = Path.home()
    candidates = [home / ".agents" / "skills", home / ".codex" / "skills"]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def load_plugins() -> list:
    if not MARKETPLACE_JSON.is_file():
        sys.exit(f"error: marketplace manifest not found: {MARKETPLACE_JSON}")
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    return data.get("plugins", [])


def copy_tree(src: Path, dst: Path, dry_run: bool, force: bool) -> str:
    """Copy src directory to dst. Returns a status string for reporting."""
    if dst.exists():
        if not force:
            return "skipped (exists; use --force to overwrite)"
        if not dry_run:
            shutil.rmtree(dst)
    if not dry_run:
        shutil.copytree(src, dst, ignore=IGNORE_PATTERNS)
    return "installed"


def shared_resources(plugin_dir: Path) -> list:
    """Plugin-level files/dirs that skills may reference relatively."""
    shared = []
    for entry in plugin_dir.iterdir():
        if entry.name in PLUGIN_LEVEL_EXCLUDES or entry.name == "skills":
            continue
        if entry.name.startswith("."):
            continue
        shared.append(entry)
    return shared


def install_plugin(plugin_dir: Path, dest: Path, flatten: bool,
                   dry_run: bool, force: bool) -> list:
    """Install one plugin. Returns [(target_path, status), ...]."""
    results = []
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return [(plugin_dir.name, "skipped (no skills/ directory)")]

    if not flatten:
        target = dest / plugin_dir.name
        # Copy the plugin wholesale minus Claude-only components, so that
        # plugin-root-relative references (e.g. scripts/) keep working.
        if target.exists():
            if not force:
                return [(target, "skipped (exists; use --force to overwrite)")]
            if not dry_run:
                shutil.rmtree(target)
        if not dry_run:
            shutil.copytree(
                plugin_dir, target,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".DS_Store", "*-workspace",
                    *PLUGIN_LEVEL_EXCLUDES,
                ),
            )
        return [(target, "installed")]

    shared = shared_resources(plugin_dir)
    for skill_dir in sorted(skills_dir.iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        target = dest / skill_dir.name
        status = copy_tree(skill_dir, target, dry_run, force)
        if status == "installed" and not dry_run:
            for resource in shared:
                resource_target = target / resource.name
                if resource_target.exists():
                    continue
                if resource.is_dir():
                    shutil.copytree(resource, resource_target,
                                    ignore=IGNORE_PATTERNS)
                else:
                    shutil.copy2(resource, resource_target)
        results.append((target, status))
    return results


def check_collisions(plugins: list) -> None:
    """Codex does not merge duplicate skill names; fail early if any."""
    seen = {}
    for entry in plugins:
        plugin_dir = (REPO_ROOT / entry["source"]).resolve()
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in skills_dir.iterdir():
            if not (skill_dir / "SKILL.md").is_file():
                continue
            if skill_dir.name in seen:
                sys.exit(
                    f"error: duplicate skill name '{skill_dir.name}' in "
                    f"plugins '{seen[skill_dir.name]}' and '{entry['name']}'. "
                    "Codex does not merge duplicates; rename one skill."
                )
            seen[skill_dir.name] = entry["name"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install kn-marketplace skills for OpenAI Codex CLI.")
    parser.add_argument("--dest", type=Path, default=None,
                        help="skills directory (default: ~/.agents/skills, "
                             "or ~/.codex/skills if only that exists)")
    parser.add_argument("--plugins", nargs="+", metavar="NAME",
                        help="install only these plugins (default: all "
                             "registered in marketplace.json)")
    parser.add_argument("--flatten", action="store_true",
                        help="copy skill dirs to the destination root for "
                             "Codex versions without recursive discovery")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would happen without copying")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing installs")
    args = parser.parse_args()

    dest = (args.dest or default_dest()).expanduser()
    plugins = load_plugins()
    if args.plugins:
        known = {p["name"] for p in plugins}
        unknown = set(args.plugins) - known
        if unknown:
            sys.exit(f"error: unknown plugin(s): {', '.join(sorted(unknown))}. "
                     f"Available: {', '.join(sorted(known))}")
        plugins = [p for p in plugins if p["name"] in args.plugins]

    if args.flatten:
        check_collisions(plugins)
    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    print(f"Destination: {dest}")
    any_installed = False
    for entry in plugins:
        plugin_dir = (REPO_ROOT / entry["source"]).resolve()
        if not plugin_dir.is_dir():
            print(f"  {entry['name']}: skipped (source not found: "
                  f"{plugin_dir} - did you run 'git submodule update --init'?)")
            continue
        for target, status in install_plugin(plugin_dir, dest, args.flatten,
                                             args.dry_run, args.force):
            print(f"  {entry['name']} -> {target}: {status}")
            any_installed |= status == "installed"

    if args.dry_run:
        print("Dry run: nothing was copied.")
    elif any_installed:
        print("Done. Restart your Codex session so it picks up new skills.")
    else:
        print("Nothing installed (everything up to date or skipped).")


if __name__ == "__main__":
    main()
