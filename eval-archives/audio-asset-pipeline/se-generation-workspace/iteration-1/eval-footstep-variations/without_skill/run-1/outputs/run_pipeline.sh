#!/usr/bin/env bash
set -uo pipefail

SCRIPTS="D:/Projects/kn-marketplace/plugins/audio-asset-pipeline/scripts"
WS="C:/Users/24kei/AppData/Local/Temp/claude/D--Projects-kn-marketplace/fc3ae81e-a691-43c6-b6b5-aa366e827bfe/scratchpad/chunk7/bench/se-generation/eval-footstep-variations/without_skill/workspace"
export AUDIO_PIPELINE_DRY_RUN=1

cd "$SCRIPTS" || exit 1

slugs=(footstep-gravel-01 footstep-gravel-02 footstep-gravel-03 footstep-gravel-04 footstep-gravel-05)
prompts=(
  "single footstep on dry gravel, boot heel then toe, close-mic foley, crunchy pebbles shifting underfoot, no reverb, no music, video game sound effect one-shot"
  "single footstep on loose gravel, sneaker sole, lighter contact, small stones scattering, close-mic foley, no reverb, no music, video game sound effect one-shot"
  "single heavy footstep on coarse gravel, deep crunch, boot digging into stones, close-mic foley, no reverb, no music, video game sound effect one-shot"
  "single footstep on damp gravel, muted crunch with a faint squelch, close-mic foley, no reverb, no music, video game sound effect one-shot"
  "single footstep on fine gravel, quick scuff, small pebbles sliding, close-mic foley, no reverb, no music, video game sound effect one-shot"
)
seeds=(4001 4002 4003 4004 4005)

for i in "${!slugs[@]}"; do
  slug="${slugs[$i]}"
  prompt="${prompts[$i]}"
  seed="${seeds[$i]}"

  echo "### STEP: init_asset.py $slug"
  python init_asset.py "$slug" --type se --mode auto --prompt "$prompt" --duration 1.0 --base "$WS"
  echo "EXIT=$?"
  echo ""

  echo "### STEP: generate_sa3.py $slug --seed $seed"
  python backends/generate_sa3.py "$slug" --seed "$seed" --base "$WS"
  echo "EXIT=$?"
  echo ""

  echo "### STEP: post_process.py $slug"
  python post_process.py "$slug" --base "$WS"
  echo "EXIT=$?"
  echo ""

  echo "### STEP: review_asset.py $slug"
  python review_asset.py "$slug" --base "$WS"
  echo "EXIT=$?"
  echo ""
done
