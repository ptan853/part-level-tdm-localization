# Experiment Plan

## Goal

Evaluate whether trajectory-guided, mask-free image editing can perform part-level edits without over-editing the full object.

## Hypothesis

Because Follow-Your-Shape's TDM is computed from source-target trajectory divergence, a part-level prompt change may activate a region larger than the intended component. This can cause whole-object drift: the requested part is edited, but the object's body, color, identity, or neighboring components also change.

## Dataset

Target size: 20-40 image-edit pairs.

Case groups:

- **Accessory edits:** remove or replace a hat, glasses, backpack, strap, handle, or scarf.
- **Label/logo/text edits:** change a bottle label, can label, mug logo, package text, or sign printed on an object.
- **Small functional part edits:** change headlights, shoe laces, camera lens, buttons, chair legs, or bicycle handles.
- **Full-object sanity checks:** include a small number of ordinary object-level replacements to confirm the baseline behaves normally on the original task type.

## Prompt Format

Use the Follow-Your-Shape style: each case has a complete source prompt and complete target prompt. The two prompts should differ mainly in the part being edited, while preserving the rest of the object and background description.

### Example: Accessory Removal

Source prompt:

`A brown teddy bear sits on a wooden chair in a softly lit bedroom, wearing a small red hat. The teddy bear has round ears, brown fur, black eyes, and a stitched smile. The chair, bed, and warm background lighting remain visible.`

Target prompt:

`A brown teddy bear sits on a wooden chair in a softly lit bedroom without a hat. The teddy bear has round ears, brown fur, black eyes, and a stitched smile. The chair, bed, and warm background lighting remain visible.`

Instruction:

`Remove the red hat from the teddy bear.`

### Example: Label Replacement

Source prompt:

`A red soda can stands on a kitchen counter with a white cursive label printed on the front. The can has a cylindrical shape, metallic surface, and small water droplets. The kitchen background is softly blurred.`

Target prompt:

`A red soda can stands on a kitchen counter with a plain white rectangular label printed on the front. The can has a cylindrical shape, metallic surface, and small water droplets. The kitchen background is softly blurred.`

Instruction:

`Replace only the label on the soda can.`

## Baselines

Primary baseline:

- Follow-Your-Shape / EditAnyShape, if suitable compute is available.

Fallback baselines:

- InstructPix2Pix as a low-cost instruction-editing baseline.
- SAM + Stable Diffusion inpainting as an oracle-mask reference.
- PartEdit if its inference/demo path can be run within the available compute.

## Metrics

- **Part edit success:** whether the target part was changed as requested.
- **Whole-object preservation:** whether non-edited parts of the same object remain stable.
- **Over-editing rate:** whether changes spread outside the intended part.
- **Background preservation:** whether background and unrelated objects remain stable.
- **Failure category:** unchanged part, under-editing, whole-object drift, texture/color leakage, background damage, or semantic mismatch.

## Success Criterion

The 2-3 week project succeeds if it produces:

- A reproducible diagnostic set of 20-40 part-level editing cases.
- A small pilot evaluation on at least one runnable baseline.
- A table reporting part success, object preservation, over-editing, and background preservation.
- At least two consistent failure modes with representative success and failure examples.

The project does not require training a new model.
