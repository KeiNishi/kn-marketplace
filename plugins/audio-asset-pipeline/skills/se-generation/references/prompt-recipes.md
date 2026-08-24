# Prompt Recipes For Stable Audio 3 Sound Effects

Contents:

- [The shape of a good SFX prompt](#the-shape-of-a-good-sfx-prompt)
- [Realistic foley](#realistic-foley)
- [Ambience](#ambience)
- [Impacts and weapons](#impacts-and-weapons)
- [Stylized and anime SFX](#stylized-and-anime-sfx)
- [Negative prompts](#negative-prompts)
- [Structured tags](#structured-tags)

## The shape of a good SFX prompt

Four slots, in this order, comma separated:

`<sound source and action>, <material>, <space>, <mic distance and treatment>`

The model is trained on descriptions of recordings, so it responds to the
vocabulary a sound librarian would use, not to narrative framing. Write
"metal latch clicking shut, close mic, dry", not "the hero locks the door
behind him".

Keep prompts short. Two to twelve words beats a sentence. Every extra clause
competes for the same conditioning budget and blurs the result.

## Realistic foley

| Sound | Prompt |
| --- | --- |
| Door | `wooden door creaking open, interior, close mic` |
| Latch | `metal latch clicking shut, close mic, dry` |
| Footstep | `single footstep on wet gravel, close mic, dry` |
| Cloth | `cloth rustle, jacket sleeve movement, close mic` |
| Paper | `paper page turning, close mic, quiet room` |
| Liquid | `water pouring into a glass, close mic` |
| Fire | `small campfire crackling, close mic` |

Rules that matter:

- Say **single** or **one** when a one-shot is wanted. Without it the model
  happily produces a sequence of footsteps.
- Say **dry** or **no reverb** unless the space is part of the sound. Game
  audio usually applies reverb in the engine.
- Name the material explicitly. "footstep" alone averages every surface in the
  training set into mush; "on wet gravel" does not.

## Ambience

Ambience is where the model is strongest, because it is closest to what it was
trained on.

- `forest ambience at dawn, distant birdsong, light wind in leaves`
- `busy market street, indistinct crowd murmur, distant traffic`
- `cave interior, dripping water, low rumble, wide stereo`
- `spaceship engine room hum, steady low drone`

For a looping bed, generate 20-30 s and let the post stage find loop points.
Do not ask the prompt for a loop; the model has no concept of one.

## Impacts and weapons

- `heavy metal impact on concrete, short decay, no reverb tail`
- `wooden crate smashing, splintering debris, close mic`
- `sword unsheathing, metal ring, close mic`
- `bow string release and arrow whoosh, close mic`
- `deep explosion, low end thump, short tail`

Impacts need decay control. `short decay`, `no tail`, and `tight` all shorten
the result; `long reverb tail` lengthens it. If the transient is buried, add
`sharp attack`.

## Stylized and anime SFX

Prompt-only styling has a real ceiling. Stable Audio 3 was trained mostly on
recorded audio, so it reaches stylized game and anime SFX by analogy rather
than by having heard many of them. Expect to iterate, and expect some sets
(a consistent family of magic sounds sharing a timbre) to stay out of reach.

What does work:

| Target | Prompt |
| --- | --- |
| Whoosh | `fast air whoosh, swishing past microphone, short` |
| Magic chime | `bright bell chime, shimmering sparkle tail, magical` |
| UI blip | `short UI click, digital blip, dry, no tail` |
| Confirm | `soft positive interface chime, two tones rising` |
| Error | `low buzz error tone, short, dry` |
| Power up | `rising synth sweep, energetic, short` |
| Retro | `8-bit chiptune jump sound, square wave` |

Techniques:

- Reach for synthesis words rather than object words: `synth sweep`,
  `square wave`, `shimmering`, `resonant`, `filtered`. The model knows these.
- Anchor on a physical analogue and then bend it: a magic ice spell is
  `glass shattering, crystalline, reversed shimmer` more reliably than it is
  `ice magic spell`.
- Say `short` and `dry` for anything that plays on a button press.

Measured limits of prompt-only styling (`small-sfx`, 4 seeds, two wordings of
the same request): style words carry far less than the physical description does.
`bright magical sparkle chime, anime style, ascending, cute` and
`glockenspiel and bell tree glissando, single ascending run, bright shimmering
tail, clean studio recording` produced the same kind of output as each other -
which is to say the instrument names did the work and `anime style` and `cute`
did none of it. What did change the result was the duration: at a 6 s window the
ascending shimmer and the decay both appeared, at 2.5 s neither did. Tune the
window and the physical description first; treat genre and mood adjectives as
free but weak.

When a whole stylized set has to share a timbre, prompting is the wrong tool.
The forward path is a LoRA fine-tuned on the target library; Stable Audio 3
supports loading LoRA weights, and the pipeline does not wire that up yet. In
the meantime, generate one good exemplar and use it as `referenceAudio` for the
rest of the set with a high `referenceStrength` (0.7-0.9), which is the closest
prompt-level approximation of a consistent family.

## Negative prompts

Pass with `--negative-prompt`. Only add terms that actually leaked in; a long
negative prompt fights the positive one.

- Unwanted music bed: `music, melody, rhythm`
- Unwanted voices: `speech, singing, voice`
- Too much room: `reverb, echo, distant, room tone`
- Hiss and rumble: `noise, hiss, hum, distortion`

## Structured tags

For musical or ambient material the model also responds to structured tags,
one per line or comma separated:

```
TrackType: Ambient
Instruments: pad, low strings
Mood: tense, sparse
BPM: 70
```

For one-shot SFX this adds nothing. Use plain descriptive prompts there and
keep structured tags for BGM-shaped requests.
