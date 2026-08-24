---
name: loop-and-postprocess
description: This skill should be used when the user asks to "make it loop", "make a seamless loop", "loop the BGM", "fix the loop point", "trim the silence", "normalize the loudness", "make it louder", "hit -16 LUFS", "export ogg", "export a 16-bit wav", or "resample to 44.1k", or as the post stage of the audio asset pipeline. Covers picking the candidate to finish, trimming to the last contentful bar so a loop is bar-exact even when the model ended the song early, equal-power seam crossfading with a measured seam check, two-pass EBU R128 loudness normalization with a true-peak ceiling, and WAV/OGG export with an optional single sample-rate conversion. Also triggers on mentions of post_process.py, stages.post, loopProcessing, master.wav, LUFS, dBTP, loudnorm, crossfade, or zero crossing.
---

# Loop And Post-Processing

Turn one approved candidate into the files a game engine actually loads: trimmed,
loop-exact, loudness-normalized, and exported.

Everything here is one script, `scripts/post_process.py`. It is stdlib Python and
ffmpeg - no GPU, no generation environment, seconds per asset.

## Quick Start

Locate the installed plugin directory first; `<plugin-root>` below is that
directory. Keep the working directory in the workspace that contains
`audio-pipeline-output/`. On Windows, use `py -3` if `python3` is not available.

```bash
python3 "<plugin-root>/scripts/post_process.py" chiptune-loop
```

That is the whole happy path when `stages.generate.selected` is set or the asset
has exactly one candidate. With several candidates and no choice recorded, the
script refuses and prints them with their silence measurements:

```bash
python3 "<plugin-root>/scripts/post_process.py" chiptune-loop --candidate generate/cand-03.wav
```

Outputs land in `audio-pipeline-output/<slug>/post/` and are recorded in
`stages.post.outputs`:

| File | What it is |
| --- | --- |
| `master.wav` | 32-bit float, source sample rate, normalized. The archive copy - keep it, re-export from it. |
| `<slug>.wav` | 16-bit PCM. What a game engine loads. |
| `<slug>.ogg` | Vorbis q6 (~192 kbps). Streaming music, or when install size matters. |

## What It Does, In Order

1. **Pick the source** - `stages.generate.selected`, or the only candidate, or
   `--candidate`.
2. **Trim** - to real content, by a different rule per asset type (below).
3. **Loop seam** - equal-power crossfade over the wrap, then measure it.
4. **Normalize** - two-pass loudnorm to `requirement.targetLufs`, ceiling
   -1.0 dBTP.
5. **Export** - `requirement.formats`, plus one optional resample at the end.

Every decision is recorded in `stages.post.loopProcessing` and
`stages.post.normalize`, including the numbers it measured. Read them instead of
guessing what happened.

## Trimming

The whole file is measured first as 50 ms RMS windows, per channel, combined with
max() - the same measurement the generation workers used for
`leadingSilenceSeconds` / `trailingSilenceSeconds`, so the post stage cuts on the
boundary the manifest already reports. Per channel matters: pooling the channels
first would let content in one of them read about 3 dB quieter and move a
boundary that sits near the threshold.

| Asset | Leading | Trailing |
| --- | --- | --- |
| Loop (`requirement.loop: true`) | Cut to the first contentful window, snapped to a zero crossing. | Cut to the loop point (below). |
| One-shot | Cut only when there is **0.5 s or more** of dead air; a shorter pre-roll is often part of the attack. | Keep 0.2 s past the last contentful window, so the decay finishes inside the file. |

A one-shot's *tail* is measured against its own body - 40 dB below its loudest
window - not against the absolute -45 dBFS floor. Sound effects come out of the
model unnormalized: the measured Stable Audio 3 door creak peaks at -30 dBFS,
and an absolute cut removed 0.95 s of its audible decay. Its leading edge still
uses the absolute floor, because nothing decays *into* the first sample.

## Loops: The Bar Is Where The Music Is

For a looping asset the cut is made on a **bar boundary computed from the
audio**, not from the length that was requested.

This matters because ACE-Step's planner regularly ends the song early. The
measured chiptune case: an 18-bar request (30.857 s at 140 BPM) came back with
content stopping at 26.70 s and 4.10 s of silence after it. The last bar that is
fully contentful is bar 15, so the loop is 25.714 s.

**A 15-bar loop out of an 18-bar request is a good outcome, not a failure.** It
is bar-exact, it wraps on a downbeat, and it has no hole in it. Say that to the
user rather than apologising for the missing bars or re-rolling seeds to chase
them - the planner decided where the music ends, and no number of retries makes
it fill bars it wrote an ending before.

Bar length is derived from the take's own tempo, and only ACE-Step actually
renders to the tempo it was handed:

| Candidate backend | Bar snapping |
| --- | --- |
| `acestep` | Uses `params.bpm` and `params.beatsPerBar` from the candidate. |
| `minimax`, `sa3` | **No bar snapping.** Their BPM is an annotation - MiniMax takes tempo as caption text and is documented not to honour it, Stable Audio 3 has no tempo control at all. The cut falls back to the content boundary, snapped to a zero crossing. |

If the tempo of such a take has been *measured* (by ear against a metronome, or
in a DAW), pass it: `--bpm 92`. That is the only way `requirement.bpm` becomes
trustworthy for those backends.

## The Seam

The last 30 ms of the loop are equal-power crossfaded into its head, with the
fade-out material taken from the audio that *follows* the loop point - the
natural continuation of the last sample. Two consequences worth knowing:

- The loop stays exactly its computed length, so a bar-snapped loop stays on
  the grid.
- The wrap is continuous by construction: the first sample after the seam is the
  sample that used to follow it.

`--crossfade-ms N` tunes it between 10 and 80. Longer smooths a rougher edit and
blurs more of the downbeat; shorter is tighter and less forgiving.

A take whose content runs all the way to the last sample has nothing to fade
from. When that happens the loop **gives a whole bar back** so the overhang
exists - the grid survives, one bar of music is spent. If even that is
impossible (a single bar of content ending at the file's end), the stage fails
with a `user_error` rather than shipping a loop whose wrap is a bare cut.
Anything from 10 ms up is accepted and recorded as `crossfadeShortfall`; 10 ms
is the floor because it is the low end of the flag's own documented range.

Afterwards the script renders what the engine will hear - the last 100 ms
followed immediately by the first 100 ms - and compares the one sample step that
spans the join against the largest step inside either half. The ratio goes into
`loopProcessing.seamRatio`:

- **Under 1.0**: the join is no rougher than the music around it. On the
  measured chiptune loop it is **0.013**; the same cut without the crossfade
  would have been **0.138**, a 52x bigger step.
- **Over 1.0**: printed as `CHECK BY EAR`. Sometimes legitimate (a loop that
  wraps onto a percussion hit), sometimes a bad loop point. Listen before
  accepting it.

The metric is a smoke alarm, not an ear. It cannot hear a bar of music arriving
half a beat late. Always do the listening check in the verification checklist.

## Loudness

Two passes: ffmpeg's `loudnorm` measures, then a single static gain moves the
level. Nothing is compressed - `loopProcessing` and `normalize` record the gain
that was applied, and the result is measured *again* afterwards rather than
trusted.

The correction is computed rather than handed back to `loudnorm`'s own apply
pass, because `linear=true` there is a request, not a guarantee: when the gain
it needs would breach the true-peak target it silently switches to **dynamic**
normalization, which compresses the track and says so only in a log line. Here
the gain is capped at the ceiling instead, and whatever loudness is left on the
table is recorded as `normalize.targetShortfallDb` and printed. If a track comes
back short of its target, that number is why - the fix is a quieter mix or a
lower target, not more gain.

When R128's gating finds no programme at all (a very short or very quiet
one-shot), there is no integrated figure to correct toward; the peak becomes the
reference instead, recorded as `normalizationType: "peak-only"`.

| Asset | `requirement.targetLufs` | Why |
| --- | --- | --- |
| BGM | **-16 LUFS** | Music sits under the mix. -16 is the usual integrated target for game music and leaves room for effects and dialogue on top. |
| SE | **-12 LUFS** | Effects have to cut through that music at the same fader position, which is about 4 LU above it. |

True-peak ceiling is **-1.0 dBTP** for everything. The extra dB below full scale
is headroom for the intersample peaks a lossy decoder or a resampler
reconstructs. It is enforced even with `--skip-normalize`, because a master
sitting at 0 dBTP clips when it is turned into 16-bit or Vorbis - MiniMax
candidates arrive at **+0.11 dBTP** and are exactly that case.

A lossy encoder reconstructs its own waveform, so an export made from a master
sitting exactly on the ceiling decodes above it - measured at **+0.25 dB** on a
limited sound effect, which is enough to fail the review stage. How much a given
file overshoots is only knowable after the encode, so the post stage measures
each export and re-encodes it once from the master attenuated by exactly that
much, recording the correction as `encoderTrimDb` in `normalize.exports`. A
trimmed export therefore reads slightly quieter than its WAV sibling; that
difference is the ceiling being honoured, not a normalization error. A reading
at or above 0 dBTP is still a hard failure.

Integrated loudness gates in 400 ms blocks, so under about 3 s of programme the
figure is indicative rather than exact. Short one-shots get
`normalize.shortProgramme: true` - judge those by ear against their neighbours.

## Formats And Sample Rate

`requirement.formats` drives the exports; `wav` and `ogg` are supported.

- **wav** is 16-bit PCM with triangular dither. Every engine loads it, it decodes
  for free, and it is the right choice for anything triggered often.
- **ogg** is Vorbis quality 6, about 192 kbps - the point where it stops being
  distinguishable from the source on game material. Use it for long music beds
  where install size matters.

The float `master.wav` always stays at the source rate. Three rates are in play
across the backends - **ACE-Step 48 kHz, Stable Audio 3 and MiniMax 44.1 kHz** -
so a project that wants one rate everywhere passes `--target-rate 44100` or
`--target-rate 48000`. That conversion happens once, at the very end, with
`soxr` at precision 28: 44.1 <-> 48 kHz is not an integer ratio, and it is where
a cheap resampler leaves audible aliasing.

Resampling does not damage a bar-exact loop. The measured 16-bar chiptune loop
is 1316571 samples at 48 kHz and 1209600 at 44.1 kHz - both exactly 27.428571 s.

## Flags

| Flag | Effect |
| --- | --- |
| `--candidate generate/cand-NN.wav` | Which take to finish. Required when there are several and none is selected. |
| `--base <workspace>` | Workspace holding `audio-pipeline-output/`. |
| `--skip-loop` | Treat a looping asset as a one-shot: no bar cut, no crossfade. For a track that turned out to want an intro and an ending. |
| `--skip-normalize` | Leave the loudness alone. The true-peak ceiling still applies. |
| `--crossfade-ms N` | Seam crossfade, 10-80 (default 30). |
| `--bpm N` | Tempo to snap bars to, for a MiniMax or Stable Audio 3 take. |
| `--target-rate 44100\|48000` | Resample the exports once, at the end. |
| `--selftest` | Run the built-in assertions for the bar, zero-crossing, crossfade and seam maths. |

Re-running overwrites `post/`; it always starts again from the chosen candidate,
never from the previous output, so nothing accumulates two crossfades or two
rounds of gain.

## Dry Run

`AUDIO_PIPELINE_DRY_RUN=1` prints the plan - content bounds, mode, bar count,
sample-exact cut, crossfade, loudness target, exports - and writes nothing. The
manifest is not touched either. Use it to confirm the bar count before spending
the (short) processing time, and to show the user what is about to happen.

The generate stage treats the same flag differently: it writes placeholder audio
and fills in the manifest, so a dry run stops dead here and `review_asset.py`
then refuses for want of outputs. That is not a wiring fault. This stage needs no
model and no GPU, so to finish a rehearsal just run it **without** the flag - it
processes placeholder candidates exactly as it does real ones.

## When It Fails

The stage records `stages.post.failureKind` and prints an actionable message.

| failureKind | What to do |
| --- | --- |
| `user_error` | No candidate chosen among several, a `--candidate` that is not in the manifest or resolves outside the asset directory, a file that is not on disk or not decodable, an unsupported entry in `requirement.formats`, a `targetLufs` that is not a number, a take whose content is shorter than one bar at the given BPM, a loop with under 10 ms of audio after its loop point, a take that is silent throughout, or ffmpeg/ffprobe missing from PATH. The message names which. |
| `backend_error` | ffmpeg failed, the cut came back a different length than it was asked for, a finished export measured at or above 0 dBTP, or a file could not be moved into place (locked, read-only, out of space). The message carries the cause; check the ffmpeg version first. |
| `timeout` | Only from a stalled sample read. The whole stage is normally seconds, even on a 75 s track, so this means something is wrong with the file or the disk. |

A run clears `outputs`, `loopProcessing` and `normalize` the moment it starts, so
a failed stage never leaves the previous run's bar count and loudness figures
behind. Files are written to a staging name and moved into place only after they
verify, so a failure also leaves the last good exports untouched - the manifest
says `failed`, and what is on disk is still the previous take.

## Verification Checklist

Before declaring the post stage done, confirm all of the following:

- `stages.post.status` is `done` and `failureKind` is `null`.
- Every path in `stages.post.outputs` exists on disk and is non-empty.
- `ffprobe` shows the exports at the expected duration, sample rate and channel
  count. For a bar-snapped loop the duration should equal
  `loopProcessing.bars * loopProcessing.barSeconds`.
- `normalize.measuredOutput.integratedLufs` is within 1 LU of
  `requirement.targetLufs`, or `normalize.targetShortfallDb` explains the
  difference and the user has been told.
- `normalize.measuredOutput.truePeakDbtp` is at or under -1.0 dBTP, and every
  entry in `normalize.exports` is at or under it too (an `encoderTrimDb` on an
  entry is how it got there).
- The 16-bit export does not clip: `ffmpeg -i <file> -af astats -f null -` shows
  a peak level below 0 dB.
- The `.ogg` decodes (the same `ffprobe`/`astats` run proves it).
- **For a loop, listen to the wrap.** Either play the file twice in a row, or
  load it into the engine with looping on and let it go round at least three
  times. `seamRatio` being green is not the same as the loop sounding right - a
  bar arriving late is inaudible to the metric and obvious to a person.
- For a one-shot, the decay is intact and there is no click at either end.
- The user has been told the real length when it differs from the request (for
  example "15 bars of the 18 you asked for - that is where the music ends").

A quick way to hear the wrap without an engine:

```bash
ffmpeg -stream_loop 2 -i audio-pipeline-output/<slug>/post/master.wav -c copy tripled.wav
ffmpeg -i tripled.wav -af silencedetect=n=-45dB:d=0.02 -f null -
```

Play `tripled.wav`, and read the `silencedetect` lines as a cheap check that no
gap opened at the join: on the measured chiptune loop every silence it finds is
one of the track's own musical rests, repeating exactly one loop length
(25.714286 s) apart, and none of them lands on a join. Delete `tripled.wav`
afterwards - it is scratch, not an asset.

If any item fails, fix it and re-verify before moving to the review stage.
