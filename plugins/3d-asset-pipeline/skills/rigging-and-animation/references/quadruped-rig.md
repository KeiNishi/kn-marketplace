# Quadruped Rig Reference

Use the `quadruped` template for four-legged creatures and animals that need locomotion clips.

## Template

- Template name: `quadruped`
- Expected source: Stage 2 GLB from `stages.mesh.files.glb`
- Expected output: Stage 3 FBX at `rigged/<slug>.fbx`
- Vendor: Meshy v5
- Stage field: `stages.rig.template`

## Suitable Assets

- Wolves, dogs, cats, horses, deer, boars, and similar animals
- Four-legged fantasy creatures
- Low, wide monsters with four primary legs
- Creature assets that need walk or gallop animation

Avoid this template for props, bipeds, vehicles, insects with many legs, serpentine creatures, and creatures whose front limbs are wings rather than legs.

## Common Quadruped Issues

- Digitigrade legs can be interpreted as plantigrade legs.
- Plantigrade creatures can receive awkward hock placement.
- Hooves and paws may need different foot contact assumptions.
- Long tails can be treated as decoration instead of a controllable chain.
- Wings, horns, saddles, or armor can confuse body-part detection.
- Low-poly meshes may produce unstable skin weights around shoulders and hips.
- Very stylized proportions can cause limb swapping or twisted joints.

Review quadruped output before animation when the asset has unusual anatomy.

## Mesh Preparation Notes

- Keep all four legs visible in the source mesh.
- Prefer a neutral standing pose over a crouched action pose.
- Avoid crossed legs, tucked feet, and hidden paws.
- Keep the belly, chest, shoulders, and hips readable from the side.
- Keep tails separated from the hind legs when possible.
- Avoid saddle straps, armor plates, or fur clumps that merge into joints.
- Use a clean silhouette for hooves, paws, claws, and ankles.
- Regenerate the mesh before rigging if the leg count or limb separation is unclear.

## Digitigrade vs Plantigrade

Digitigrade creatures stand on toes, such as dogs and cats. Plantigrade creatures place more of the foot on the ground, such as bears. The Meshy template choice is still `quadruped`; the distinction should be handled by prompt quality, mesh shape, and manual review after rigging.

If the first rig produces poor foot contact, regenerate the mesh with clearer side-view anatomy before rerunning rigging.

## Biped Fallback

Some fantasy creatures are ambiguous. If a creature stands upright most of the time and uses forelimbs as arms, use `humanoid` instead of `quadruped`.

Examples:

- Werewolf standing upright: `humanoid`
- Wolf running on four legs: `quadruped`
- Dragon with wings and four legs: `quadruped`, then review carefully
- Small imp with two legs and arms: `humanoid`

## Validation

- Confirm `assetType` is `quadruped` or `--template quadruped` was explicitly passed.
- Confirm `stages.mesh.files.glb` exists.
- Confirm rig output lands in `rigged/<slug>.fbx`.
- Confirm animation defaults use `idle`, `walk`, and `gallop`.
- Confirm props remain skipped and do not enter this template.
