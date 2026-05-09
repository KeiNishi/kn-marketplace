# GPT Image Prompt Patterns

The planned default model for this plugin is `gpt-image-2`. The script also accepts `--model` and `PIPELINE_OPENAI_IMAGE_MODEL` for accounts that should use another GPT Image model.

## Shared Anchor Template

```text
Create production concept art for a Godot 4 3D game asset named [NAME].
Asset type: [humanoid|quadruped|prop].
Description: [DESCRIPTION]
Style anchor: stylized realistic game concept art with PBR-friendly material cues.
Keep the same design across all views. Use clean readable forms, material and color consistency, neutral studio lighting, a plain background, and no text labels, callouts, watermark, UI, or signature.
Camera requirement: [ANGLE CLAUSE].
```

## Humanoid Notes

- Ask for a neutral or T-pose when mesh generation needs clean limb separation.
- Keep hands, feet, equipment, and face silhouette visible.
- Avoid action poses, strong foreshortening, and cropped weapons.

## Quadruped Notes

- Ask for all four legs visible where possible.
- Preserve head, tail, spine, and shoulder silhouette.
- Avoid curled poses or sitting poses unless the source description requires them.

## Prop Notes

- Ask for the entire object visible in frame.
- Include material cues useful for PBR generation, such as metal, cloth, wood, leather, stone, glass, or emissive elements.
- Avoid labels, exploded diagrams, dimension markers, and UI overlays.
