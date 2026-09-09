EXPERIMENT RECORD · 9 SEPTEMBER 2026

# Head editing: control duration and initialization

## 1. Findings

In six selected head-editing cases, increasing the number of controlled denoising steps improved source preservation: mean strict outside-mask LPIPS decreased from **0.4325 at N=0 to 0.0136 at N=13**. Code inspection, saved traces and numerical sampler tests found that N matched the number of controlled updates.

Head replacement remained unreliable in the two uncontrolled baselines. Source-inversion initialization often retained the original head or produced accessories; random-noise initialization also produced incorrect head–body relationships and whole-body hybrids. These observations indicate that the failures cannot be attributed solely to inaccurate masks or excessive preservation control. They do not establish a general inability of the model to generate these compositions.

## 2. Experiment and settings

The experiment examined whether failed local head replacement persisted when the supplied ground-truth (GT) head mask was used and preservation control was reduced. A second baseline removed source inversion to examine generation from independent noise under the same target prompts.

The six cases were selected using earlier comparison results: five previously observed failures and a bear-to-lion contrast case. No new sweep ratings were used for selection. The sweep contains repeated conditions on six cases, rather than 84 independent examples.

| Component | Setting |
| --- | --- |
| Model | FLUX.1-dev; 1024 × 1024; bf16; offloading enabled |
| Sampling | Existing explicit-midpoint RK2 implementation; 15 denoising updates |
| Guidance and seed | Target guidance 2.0; inversion guidance 1.0; seed 0 |
| Control sweep | Source-inversion initialization; N=0…13; 6 cases × 14 durations = 84 outputs |
| Random-noise baseline | N=0; 6 outputs; identical CPU-seeded Gaussian tensor reused across prompts; no source inversion or mask |
| Disabled mechanisms | Image-KV injection, attention gating, endpoint projection and ControlNet |
| Runtime | NVIDIA A800 80GB; Python 3.10.8; torch 2.1.2+cu118; CUDA 11.8 |

N specifies the first N complete denoising updates: indices 0 through N−1. Thus N=0 applies no residual control, and N=13 leaves two free updates. Each controlled update uses a controlled midpoint and endpoint. N changes duration, not a continuous control-strength parameter.

The GT mask is binarized, resized by nearest neighbour to the VAE grid and max-pooled over 2 × 2 cells to produce a 64 × 64 token mask. Inside the editable region, the method uses target-field increments; outside it, it uses increments from the cached source trajectory. After the prefix, the target trajectory evolves without this constraint. Effects accumulated during the prefix remain after release.

The two N=0 conditions share target prompts, guidance and the timestep schedule. Their initial states differ: one is the source inversion output, while the other is independent Gaussian noise. The inversion path also retains legacy diagnostic forwards that do not enter its update; the random-noise path omits them. A same-initial-state nonlinear sampler test checks update equivalence.

| Case | Frozen target prompt |
| --- | --- |
| synth_0028 | A cow with dragon head at a restaurant |
| synth_0032 | A cat with dragon head at a desert |
| synth_0033 | A dog with cat head at a restaurant |
| synth_0038 | A horse with dragon head at a zoo |
| synth_0043 | A bear with dragon head at a jungle |
| synth_0036 | A bear with lion head at a zoo |

## 3. Frozen code and experiment artifacts

| Snapshot | Commit |
| --- | --- |
| Base repository | `3f8581894eabacf7a30ee08168923bef1a89d7ba` |
| GT control-duration sweep | `6d3fb43775a6f888b1130ce6d4720392c0d9953b` |
| Random-noise N=0 baseline | `193fed11dadb88b8d9a42f408723ecf94b246918` |
| FollowYourShape submodule, both runs | `b096e8f7736b0f44d820933d5046fe252059a5eb` |

The random-noise commit adds the baseline runner, protocol and tests; it does not change the shared sampling implementation used by the sweep. Experiment settings and input hashes are recorded in `core/protocols/gt_prefix_diagnostic_v1/`. The executed sweep commit and runtime are recorded in `core/results/gt_prefix_diagnostic_v1/execution_provenance.json`; the random run records them in `core/results/random_noise_n0_v1/protocol.json`. Cached model paths and file sizes were recorded; full weight hashes were not independently recomputed.

## 4. Evidence

### 4.1 Control execution

All 84 saved traces contain 15 denoising updates and exactly N residual-controlled updates at the expected indices. Recorded source references use indices i/i/i+1, control times descend, and residual diagnostics are finite. No additional KV, attention or projection control appears in the traces. The maximum recorded outside residual after controlled midpoint and endpoint updates is zero.

Numerical tests exercised the actual torch sampler with a nonlinear test field at every N=0…13. The midpoint and endpoint updates, release positions and absence of KV/attention injection passed for all 14 durations. The two existing prefix integration tests also passed. These tests support the inspected implementation properties; they are not additional image-generation runs or a proof that the full system is error-free.

### 4.2 Source preservation

The following values are arithmetic means over the same six cases. Lower LPIPS indicates greater source preservation. Evaluation uses the frozen 512 × 512 contract and AlexNet LPIPS. The buffered mask excludes an additional two-token-radius region (16 pixels at evaluation resolution).

| N | Strict outside LPIPS ↓ | Buffered outside LPIPS ↓ |
| --- | --- | --- |
| 0 | 0.4325 | 0.4000 |
| 1 | 0.3561 | 0.3266 |
| 2 | 0.1979 | 0.1831 |
| 3 | 0.1730 | 0.1594 |
| 4 | 0.1509 | 0.1374 |
| 5 | 0.1326 | 0.1204 |
| 6 | 0.1138 | 0.1026 |
| 7 | 0.0959 | 0.0872 |
| 8 | 0.0780 | 0.0708 |
| 9 | 0.0604 | 0.0544 |
| 10 | 0.0426 | 0.0378 |
| 11 | 0.0293 | 0.0258 |
| 12 | 0.0197 | 0.0169 |
| 13 | 0.0136 | 0.0113 |

The means decrease monotonically across this sweep. These metrics measure preservation, not target-head identity or successful local replacement. They therefore do not identify an optimal N. All 84 strict and buffered values are available in `core/results/gt_prefix_diagnostic_v1/evaluation/image_metrics.csv`.

### 4.3 Uncontrolled generation

Each row shows the source, inversion-initialized N=0 output and random-noise N=0 output. Descriptions are qualitative image observations, not blinded reviewer scores. All six cases are included.

### Cow → dragon head synth_0028

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/f03ad80412830e796b16.png) | ![Inversion N=0](assets/dbb38fe4f28b8ad65d51.jpg) | ![Random noise N=0](assets/0d4420c83ddfbec79a02.jpg) |

**Inversion:** Head remains recognizably bovine. **Random noise:** Scales and sharp teeth appear, but scales also cover the body.

### Cat → dragon head synth_0032

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/5e879b4944443b6f90e2.png) | ![Inversion N=0](assets/5a5dda2f79924ff9bf0d.jpg) | ![Random noise N=0](assets/2518bd013a9aa205f221.jpg) |

**Inversion:** A dragon head appears, with substantial dragon-like changes to the body. **Random noise:** A whole-body cat–dragon hybrid; the transformation is not confined to the head.

### Dog → cat head synth_0033

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/8bdc74a36ac254d6ecfe.png) | ![Inversion N=0](assets/8d6f8625049ed18b484a.jpg) | ![Random noise N=0](assets/f098d5661da26e2fcfd3.jpg) |

**Inversion:** Head remains recognizably canine. **Random noise:** A separate kitten sits on the dog’s head: object placement instead of head replacement.

### Horse → dragon head synth_0038

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/e419c6b72ce0606df766.png) | ![Inversion N=0](assets/97643e019a443edcfd66.jpg) | ![Random noise N=0](assets/daf75d813f31f82daf08.jpg) |

**Inversion:** Horse anatomy remains, with a horned face covering. **Random noise:** A horse wearing metal-like face armour, rather than a biological dragon head.

### Bear → dragon head synth_0043

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/8d5c80c059b7d1323f90.png) | ![Inversion N=0](assets/5096b0aa5e08c7452693.jpg) | ![Random noise N=0](assets/f47cd0bb20c733f1bf8b.jpg) |

**Inversion:** Bear anatomy remains, with a dragon-like muzzle covering and decorations. **Random noise:** Pronounced reptilian face, horns and teeth on a furry body; a more plausible but still hybrid composition.

### Bear → lion head synth_0036

| Source | Inversion N=0 | Random noise N=0 |
| --- | --- | --- |
| ![Source](assets/84cfd41d06ab1f79d1f7.png) | ![Inversion N=0](assets/1178ab0a5a81b98e63ec.jpg) | ![Random noise N=0](assets/22b5891def15dbfaac87.jpg) |

**Inversion:** A lion-like face and mane appear on a bear-like body. **Random noise:** A lion-like face and mane appear; the body’s species identity is less unambiguous.

### 4.4 Complete control-duration results

All six cases, GT masks and N=0…13 outputs are shown below. Expand each case to inspect the sequence.

<details>
<summary>Cow → dragon head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/2063d5b0bb2400ed19bf.png) | ![N=0](assets/dbb38fe4f28b8ad65d51.jpg) | ![N=1](assets/28032e1635b34bc29173.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/041c40d7159e249daebe.jpg) | ![N=3](assets/674d1d21c80d610dbdbd.jpg) | ![N=4](assets/77d4b1cf6bc6b89291f3.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/98176d7bcff59f585006.jpg) | ![N=6](assets/7b7b8b8ddaf8152fcf61.jpg) | ![N=7](assets/b8c95e82052fc3e9d35c.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/afc16a9ba8aa3b98f938.jpg) | ![N=9](assets/0cf5aa121f95c06afaa1.jpg) | ![N=10](assets/bcb8edae1d92a87af17b.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/027f34037b1e7a71d19a.jpg) | ![N=12](assets/2b6f4a4694f972bda504.jpg) | ![N=13](assets/0d94109af8f038079b0c.jpg) |

</details>

<details>
<summary>Cat → dragon head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/501e5d2fc5f0017ffed7.png) | ![N=0](assets/5a5dda2f79924ff9bf0d.jpg) | ![N=1](assets/0b540597f742ff33df9e.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/e5ac060729cdf144628f.jpg) | ![N=3](assets/b5a0e4657d8443bbe788.jpg) | ![N=4](assets/a0cf7364a27f0e94abae.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/e3ecb24e4f920474e647.jpg) | ![N=6](assets/98b667560a8e69a542b9.jpg) | ![N=7](assets/11e9fb0017f20c673c31.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/7cd825be9e919b3673e9.jpg) | ![N=9](assets/425caf5572c182ab3f7f.jpg) | ![N=10](assets/fcfd2dcd6ae135d7cb59.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/dd4a7aa40eb759f3389b.jpg) | ![N=12](assets/6162e570706682bda938.jpg) | ![N=13](assets/116299b665fbb0e980c3.jpg) |

</details>

<details>
<summary>Dog → cat head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/c9d1c93997a528726017.png) | ![N=0](assets/8d6f8625049ed18b484a.jpg) | ![N=1](assets/81ee27736bf2d5ea9260.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/94f29d7b11cb29eccbb1.jpg) | ![N=3](assets/dbb30a5beee2a309bdff.jpg) | ![N=4](assets/1307a22a67b00e68a004.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/0666cb71e4c4f6fe777a.jpg) | ![N=6](assets/c9d70fe9f17d3151b676.jpg) | ![N=7](assets/3a11580756824cb15fbb.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/fbd5fee6576baea49ecc.jpg) | ![N=9](assets/bf83c482acc79e505c44.jpg) | ![N=10](assets/2192cdeb76abdd88495e.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/7af65b46fbeee2550779.jpg) | ![N=12](assets/e9e9010b8dcb3512e993.jpg) | ![N=13](assets/80326886bcfc15f48531.jpg) |

</details>

<details>
<summary>Horse → dragon head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/902432704b62d6dc13e4.png) | ![N=0](assets/97643e019a443edcfd66.jpg) | ![N=1](assets/29596fcddd9585b9164e.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/9b97129c31ec5dd5d046.jpg) | ![N=3](assets/2cd587deff6f95f64ea6.jpg) | ![N=4](assets/4737882f55ac0365898d.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/b39c16c84a1f0dfc66dd.jpg) | ![N=6](assets/b883b5a41fbcb3da08fc.jpg) | ![N=7](assets/b6c5ef78731f2899191d.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/3d58c37b981015e001f6.jpg) | ![N=9](assets/af961dd763db4bdf71ec.jpg) | ![N=10](assets/11e7f543f409232d5211.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/bc2a4d438e9c58c9e332.jpg) | ![N=12](assets/83213a79378fc86a4129.jpg) | ![N=13](assets/e792b926e8e1ac575f3e.jpg) |

</details>

<details>
<summary>Bear → dragon head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/3b0267afa9eefeae45f4.png) | ![N=0](assets/5096b0aa5e08c7452693.jpg) | ![N=1](assets/eb365aaf19bd4539a29b.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/5322eeb57c36f9b666e6.jpg) | ![N=3](assets/690bb0d23da0e015a08e.jpg) | ![N=4](assets/a66e077e624d5b459717.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/d6dbee54e5db2f09dbcf.jpg) | ![N=6](assets/2fd8934b4069b95161a3.jpg) | ![N=7](assets/03b01a7b5c24681bee3c.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/0261dd16cbf25bb84c18.jpg) | ![N=9](assets/38af71f88e47e18c9988.jpg) | ![N=10](assets/ff87a281d859fb91553f.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/04a337b7692b3dd4813d.jpg) | ![N=12](assets/c3359e10d352abf30928.jpg) | ![N=13](assets/da27930858bbf7db3a85.jpg) |

</details>

<details>
<summary>Bear → lion head — N=0…13</summary>

| GT head mask | N=0 | N=1 |
| --- | --- | --- |
| ![GT head mask](assets/307ab702431565b58ab4.png) | ![N=0](assets/1178ab0a5a81b98e63ec.jpg) | ![N=1](assets/2d113e30466cccf0c791.jpg) |

| N=2 | N=3 | N=4 |
| --- | --- | --- |
| ![N=2](assets/06dec3a4944309f034df.jpg) | ![N=3](assets/05dcf73ad88b54063e1e.jpg) | ![N=4](assets/40f92ea6e66a69c78a63.jpg) |

| N=5 | N=6 | N=7 |
| --- | --- | --- |
| ![N=5](assets/bf19f967af9909fadc58.jpg) | ![N=6](assets/d907169f9e14b603a4eb.jpg) | ![N=7](assets/7369ca3b2c5dde87a1c4.jpg) |

| N=8 | N=9 | N=10 |
| --- | --- | --- |
| ![N=8](assets/edd76b411430d540f37d.jpg) | ![N=9](assets/6f77c2a8530a65330e4d.jpg) | ![N=10](assets/981f615cbf53e67b9fee.jpg) |

| N=11 | N=12 | N=13 |
| --- | --- | --- |
| ![N=11](assets/857e54d8e7a800ec5661.jpg) | ![N=12](assets/a325c53007210ed0ea13.jpg) | ![N=13](assets/9dc6c365ef3417e2ac7d.jpg) |

</details>

## 5. Discussion

Both inversion-based and random-noise N=0 generation produced incorrect head–body combinations in these cases. Some outputs retained the original head, added a separate animal or accessory, or extended the target features across the body. This raises the possibility that the current FLUX setup has difficulty generating unusual cross-species compositions, beyond the effect of the added preservation control.

FLUX’s joint attention allows information exchange within and between text and image tokens, as shown in the [official implementation](https://github.com/black-forest-labs/flux/blob/main/src/flux/modules/layers.py). This raises a question about how the model represents a requested local species identity alongside the identity of the whole animal, and whether their interaction contributes to these outcomes. The current experiment does not examine those internal representations or establish attention as the cause of the failures.

Increasing N improves source preservation, but preservation alone does not establish successful head replacement. With only six selected cases, one seed and one sampling configuration, the results leave open whether the observed composition difficulties persist more broadly. They do not establish that FLUX is generally unable to generate such images.

Images are embedded from original output files without retouching. Qualitative descriptions were prepared with AI assistance and are not independent blinded ratings.

## Supporting files

- [Per-case preservation metrics](image_metrics.csv)
- [Frozen sweep protocol](../../protocols/gt_prefix_diagnostic_v1/protocol.json)
- [Implementation audit](../../protocols/gt_prefix_diagnostic_v1/audit.md)
- [Random-noise protocol](../../protocols/random_noise_n0_v1.json)
