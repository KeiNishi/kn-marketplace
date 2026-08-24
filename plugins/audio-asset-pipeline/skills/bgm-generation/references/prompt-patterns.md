# Prompt Patterns For ACE-Step Game Music

Contents:

- [The shape of a good music prompt](#the-shape-of-a-good-music-prompt)
- [Worked prompts by cue type](#worked-prompts-by-cue-type)
- [Structure tags](#structure-tags)
- [Loop hygiene](#loop-hygiene)
- [Lyrics format](#lyrics-format)
- [What the prompt does not control](#what-the-prompt-does-not-control)

## The shape of a good music prompt

Four slots, comma separated:

`<mood and function>, <genre>, <instrumentation>, <key>`

`tense stealth loop, dark synthwave, arpeggiated bass and muted kick, F minor`

Tempo and time signature do NOT belong here. They are structured fields
(`requirement.bpm`, `requirement.timeSignature`), and the loop bar snapping
reads them from the manifest, not from the text.

The key does belong here: the manifest has no key field, and ACE-Step reads the
key out of the caption.

Keep it to roughly one line. The caption limit is 512 characters, but past a
dozen or so descriptors the conditioning smears rather than sharpens.

## Worked prompts by cue type

| Cue | Prompt | BPM |
| --- | --- | --- |
| Boss battle | `driving orchestral boss battle theme, taiko drums, brass ostinato, choir stabs, D minor` | 150 |
| Regular battle | `fast energetic battle theme, rock orchestra, electric guitar and strings, E minor` | 160 |
| Town | `calm medieval town theme, lute, recorder, hand percussion, F major` | 100 |
| Overworld | `adventurous overworld theme, sweeping orchestral strings and horns, C major` | 120 |
| Dungeon | `oppressive dungeon theme, low drones, sparse metallic percussion, atonal` | 70 |
| Stealth | `tense stealth loop, dark synthwave, arpeggiated bass, muted kick, F minor` | 110 |
| Shop / menu | `light cosy shop theme, jazzy piano trio, brushed drums, G major` | 95 |
| Victory sting | `triumphant short victory fanfare, brass and timpani, C major` | 130 |
| Game over | `melancholy game over theme, solo piano, sparse, A minor` | 60 |
| Retro action | `upbeat chiptune battle theme, 8-bit square lead, driving bass, energetic` | 140 |
| Credits song | `wistful indie folk ending theme, acoustic guitar, female vocal, warm` | 85 |

Pattern worth copying: the cue's **function** ("boss battle theme", "shop
theme") is doing as much work as the genre. It is vocabulary the model saw
attached to music that behaves the way game music behaves.

## Structure tags

Adding an arrangement sketch to the caption shapes how the duration is filled:

- `intro, main loop, build, no outro`
- `A section, B section, return to A`
- `sparse first half, full arrangement second half`

Useful for anything over about 60 seconds, where the model otherwise decides
its own arc. For a short loop, leave the structure out and let the whole
duration be the loop.

## Loop hygiene

The backend appends `seamless loop, no intro, no outro` for looping assets. On
top of that:

- Ask for a steady arrangement: `consistent arrangement throughout` fights the
  model's habit of building toward a climax it cannot resolve inside a loop.
- Avoid `fade out`, `ending`, `finale`, `outro` - the model obliges, and a fade
  is unrecoverable at the loop seam.
- Avoid one-shot openers: `cymbal swell`, `riser`, `orchestral hit intro`.
- Shorter loops (16-32 bars) come back tighter than long ones. Two 30 s loops
  that alternate beat one 4 minute track for in-game use.

## Lyrics format

`requirement.lyrics` accepts plain text with section markers on their own lines:

```
[verse]
line one
line two

[chorus]
line one
line two
```

- Section markers the model recognises: `[verse]`, `[chorus]`, `[bridge]`,
  `[intro]`, `[outro]`.
- The vocal language is detected from the lyrics; no field to set.
- `[Instrumental]` as the entire lyrics is what the backend sends when
  `requirement.vocals` is false. Do not write it by hand - set the flag.
- Lyrics cap at 4096 characters. Long lyrics against a short duration get
  crammed or dropped; roughly match the word count to the length.

## What the prompt does not control

Be straight with the user about these instead of promising a re-prompt will fix
them:

- **Exact melodies.** There is no way to specify a motif. Reference audio
  borrows character, not tunes.
- **Stem separation.** One stereo mixdown comes back, not layered stems.
- **Precise instrument counts.** "Three violins" reads as "strings".
- **Loudness.** Loudness is a post-stage concern (`requirement.targetLufs`),
  not a prompt word.
- **Bar-exact section boundaries.** The requested length is honoured closely and
  the bar count is snapped, but where the B section starts is the model's call.
