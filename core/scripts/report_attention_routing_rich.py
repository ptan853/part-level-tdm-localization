#!/usr/bin/env python3
"""Export small paired research views; full recordings stay beside server runs."""

import argparse
import csv
import html
import json
from pathlib import Path

import numpy as np


def reduce_record(attention, mask):
    selected = np.asarray(mask).reshape(-1).astype(bool)
    values = attention[:, selected]
    if not selected.any() or not np.isfinite(values).all():
        raise ValueError('Invalid query region or attention')
    return dict(queries=values.mean(0), heads=values.mean(1), mean=values.mean((0, 1)),
                coordinates=np.argwhere(mask).tolist())


VIEWER = r'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Attention routing</title><style>
body{font:15px system-ui;margin:24px;color:#182026;background:#fafafa}h1{font-size:24px}
.images,.panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.images{grid-template-columns:repeat(3,minmax(0,1fr))}img{width:100%;max-height:360px;object-fit:contain}
label{display:inline-block;margin:8px 16px 12px 0}select{padding:6px}canvas{max-width:100%;height:auto;background:white}
section{min-width:0;overflow:auto}h2{font-size:18px}p{max-width:1100px;line-height:1.5}
@media(max-width:750px){.panels{grid-template-columns:1fr}.images{grid-template-columns:1fr}}
</style><h1 id="title"></h1><p id="prompt"></p>
<div class="images"><figure><img src="source_gt.jpg"><figcaption>Source + fixed GT query region</figcaption></figure>
<figure><img src="uncontrolled.jpg"><figcaption>Uncontrolled N=0</figcaption></figure>
<figure><img src="rk2_gt_n07.jpg"><figcaption>GT residual RK2 N=7</figcaption></figure></div>
<label>Evaluation <select id="phase"><option>start</option><option>midpoint</option></select></label>
<label>Step <select id="step"></select></label><label>Layer <select id="layer"></select></label>
<label>Rows <select id="view"><option value="queries">GT image positions (mean heads)</option><option value="heads">Heads (mean GT positions)</option></select></label>
<p>Joint attention, normalized over all text and image keys. Valid text columns include EOS; padding remains in the denominator. Both panels share a color scale. These are fixed source-GT coordinates, not tracked generated heads.</p>
<div class="panels"><section><h2>Uncontrolled N=0</h2><canvas id="left"></canvas></section><section><h2>GT RK2 N=7</h2><canvas id="right"></canvas></section></div>
<p id="scale"></p><p>Raw server data retain every head and every image position. This portable view contains two explicit averages, not the full head-by-position tensor. Attention and AV norms are descriptive, not causal or semantic scores.</p>
<script>const D=__DATA__;
const el=id=>document.getElementById(id);el('title').textContent=D.case;el('prompt').textContent=D.prompt;
for(let s=0;s<D.steps;s++)el('step').add(new Option(s,s));for(const l of D.layers)el('layer').add(new Option(l,l));
function paint(id,m,max){const c=el(id),ctx=c.getContext('2d'),cw=46,ch=15,left=82,top=135;
c.width=left+D.tokens.length*cw+15;c.height=top+m.length*ch+15;ctx.fillStyle='white';ctx.fillRect(0,0,c.width,c.height);ctx.font='11px system-ui';
D.tokens.forEach((t,i)=>{ctx.save();ctx.translate(left+i*cw+10,top-8);ctx.rotate(-Math.PI/3);ctx.fillStyle='#222';ctx.fillText(t,0,0);ctx.restore()});
m.forEach((row,r)=>{ctx.fillStyle='#222';const label=el('view').value==='heads'?'head '+r:D.coordinates[r].join(',');ctx.fillText(label,3,top+r*ch+11);
row.forEach((v,j)=>{const t=max?v/max:0;ctx.fillStyle=`rgb(${Math.round(245-210*t)},${Math.round(248-110*t)},${Math.round(250-80*t)})`;ctx.fillRect(left+j*cw,top+r*ch,cw-1,ch-1)})});}
function draw(){const key=[el('step').value,el('phase').value,el('layer').value].join('|'),view=el('view').value;
const a=D.runs[0][key][view],b=D.runs[1][key][view];let max=0;for(const m of [a,b])for(const r of m)for(const v of r)max=Math.max(max,v);
paint('left',a,max);paint('right',b,max);el('scale').textContent='Shared scale: 0 to '+max.toPrecision(4)+'; row labels are token-grid (row,column) or head index.';}
for(const id of ['phase','step','layer','view'])el(id).onchange=draw;draw();</script>'''


def export_case(root, case, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    conditions = ['uncontrolled', 'rk2_gt_n07']
    paths = [root / 'recording_on' / c / case / 'seed_000' for c in conditions]
    metas = [json.loads((p/'routing/metadata.json').read_text()) for p in paths]
    if metas[0]['tokens'] != metas[1]['tokens'] or metas[0]['layers'] != metas[1]['layers']:
        raise ValueError('Paired metadata mismatch')
    if not np.array_equal(*[np.load(p/'routing/initial_latent.npy') for p in paths]):
        raise ValueError('Paired initial latent mismatch')
    mask = np.load(paths[0]/'routing/observation_mask.npy').astype(bool)
    if not np.array_equal(mask, np.load(paths[1]/'routing/observation_mask.npy')):
        raise ValueError('Paired masks differ')
    tokens = metas[0]['tokens']; positions = metas[0]['valid_text_positions']
    labels = [f'{i}: {tokens["token_strings"][i]}' for i in positions]
    layers = [f'{s}_{i}' for s, ids in metas[0]['layers'].items() for i in ids]
    n = metas[0]['num_steps']; out.mkdir(parents=True, exist_ok=True)
    payload = dict(case=case, prompt=tokens['prompt'], tokens=labels, layers=layers, steps=n,
                   coordinates=np.argwhere(mask).tolist(), runs=[])
    rows = []; metric_names = ['subject', 'edit', 'part', 'outside_image', 'text_mass', 'edit_av_norm']
    cubes = np.zeros((2, 2, len(layers), n, len(metric_names)))
    for condition_index, (condition, run, meta) in enumerate(zip(conditions, paths, metas)):
        entries = {}; flat = mask.flatten()
        for record in meta['coverage']:
            with np.load(run/'routing'/record['file']) as data:
                reduced = reduce_record(data['text_attention'], mask)
                key = f"{record['step']}|{record['evaluation']}|{record['layer']}"
                entries[key] = {k: np.round(reduced[k].astype(np.float64), 7).tolist() for k in ('queries', 'heads')}
                mass = data['region_mass'][:, flat].mean((0,1))
                av = data['av_norms'][:, flat].mean((0,1))
                metrics = {g:float(reduced['mean'][[positions.index(i) for i in tokens['groups'][g]]].sum())
                           for g in ('subject','edit','part')}
                metrics.update(outside_image=float(mass[2]), text_mass=float(mass[0]),
                               edit_av_norm=float(av[meta['av_columns'].index('edit')]))
                row = dict(case=case, condition=condition, step=record['step'],
                           evaluation=record['evaluation'], layer=record['layer'], **metrics)
                rows.append(row)
                cubes[condition_index, ['start','midpoint'].index(record['evaluation']),
                      layers.index(record['layer']),record['step']] = [metrics[k] for k in metric_names]
        payload['runs'].append(entries)
        image = Image.open(run/'img_0.jpg').convert('RGB'); image.thumbnail((768,768))
        image.save(out/f'{condition}.jpg', quality=92)
    repo = Path(__file__).resolve().parents[2]
    config = json.loads((paths[0]/'run_config.json').read_text())
    source = Image.open(repo/config['source_image']).convert('RGB'); source.thumbnail((768,768))
    source.save(out/'source.jpg',quality=92)
    pixels = np.asarray(source).copy()
    region = np.asarray(Image.fromarray(mask.astype('uint8')*255).resize(source.size, Image.Resampling.NEAREST))>0
    pixels[region] = (.65*pixels[region]+.35*np.array([240,60,60])).astype('uint8')
    Image.fromarray(pixels).save(out/'source_gt.jpg',quality=92)
    # JSON is escaped for a script element; no external requests or file fetches are needed.
    encoded = json.dumps(payload,separators=(',',':')).replace('<','\\u003c')
    (out/'index.html').write_text(VIEWER.replace('__DATA__',encoded))
    with (out/'metrics.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for phase_index, phase in enumerate(('start','midpoint')):
        fig, axes=plt.subplots(6,2,figsize=(13,28),layout='constrained')
        for j,name in enumerate(metric_names):
            vmax=float(cubes[:,phase_index,:,:,j].max()) or 1
            for ci in range(2):
                ax=axes[j,ci]; im=ax.imshow(cubes[ci,phase_index,:,:,j],aspect='auto',vmin=0,vmax=vmax,cmap='viridis')
                ax.set_title(f'{conditions[ci]} | {name}'); ax.set_yticks(range(len(layers)),layers,fontsize=6)
                ax.set_xticks(range(n)); ax.set_xlabel('Denoising step'); ax.axvline(6.5,color='white',linestyle='--',linewidth=1)
            fig.colorbar(im,ax=axes[j].tolist(),shrink=.8)
        fig.suptitle(f'{case}: fixed-GT query mean across positions and heads | {phase}\nAttention uses joint keys; AV is per-head norm before output projection. Dashed line: end of N=7 control.')
        fig.savefig(out/f'layers_steps_{phase}.png',dpi=125); plt.close(fig)
    return rows


def decode_endpoints(root, cases, export):
    import sys
    import torch
    from PIL import Image
    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'core/third_party/FollowYourShape/src'))
    from flux.util import load_ae
    from flux.sampling import unpack
    ae=load_ae('flux-dev',device='cuda').eval()
    with torch.inference_mode():
        for case in cases:
            for condition in ('uncontrolled','rk2_gt_n07'):
                run=root/'recording_on'/condition/case/'seed_000'
                meta=json.loads((run/'routing/metadata.json').read_text())
                height,width=[v*16 for v in meta['image_grid_shape']]
                target=export/case/condition; target.mkdir(parents=True,exist_ok=True)
                images=[]
                for step in range(meta['num_steps']):
                    if step+1<meta['num_steps']:
                        with np.load(run/f'routing/states/step_{step+1:02d}_start.npz') as f: x=f['latent']
                    else: x=np.load(run/'routing/final_latent.npy')
                    x=unpack(torch.from_numpy(x).to('cuda'),height,width)
                    with torch.autocast('cuda',dtype=torch.bfloat16): image=ae.decode(x)
                    image=((image[0].float().clamp(-1,1)+1)*127.5).permute(1,2,0).byte().cpu().numpy()
                    image=Image.fromarray(image); image.thumbnail((384,384)); image.save(target/f'step_{step:02d}.jpg',quality=90)
                    images.append(f'<figure><img src="{condition}/step_{step:02d}.jpg"><figcaption>After step {step}</figcaption></figure>')
                (export/case/f'{condition}_steps.html').write_text('<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui}main{display:grid;grid-template-columns:repeat(5,1fr)}img{width:100%}figure{margin:8px}</style><h1>'+html.escape(case+' | '+condition)+'</h1><p>Direct endpoint latent decoding, not predicted clean x0. Early noisy states may not be recognizable. No new human scores.</p><main>'+''.join(images)+'</main>')
    del ae
    torch.cuda.empty_cache()


def report(root, cases, export, decode=False):
    export.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for case in cases:
        rows=export_case(root,case,export/case)
        for condition in ('uncontrolled','rk2_gt_n07'):
            selected=[r for r in rows if r['condition']==condition and r['evaluation']=='midpoint' and r['step']<7]
            summaries.append(dict(case=case,condition=condition,edit_attention=np.mean([r['edit'] for r in selected]),
                                  subject_attention=np.mean([r['subject'] for r in selected]),
                                  outside_image_mass=np.mean([r['outside_image'] for r in selected])))
    if decode: decode_endpoints(root,cases,export)
    with (export/'summary.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    lines=['# Rich Attention Routing Diagnostic','',
           'Exploratory five-case study. No new human scores or causal conclusions are assigned by this report.',
           '','## Design','',
           'Same source inversion latent, seed 0, 15 steps. Uncontrolled N=0 versus GT residual RK2 N=7; no KV injection. All double/single layers, start and midpoint. Raw head-by-image-by-valid-text weights stay on the server.',
           '','## Reading the Evidence','',
           '- Interactive views select every recorded step/layer/evaluation. Query rows average heads; head rows average fixed GT queries. Both conditions use a shared scale for each selection.',
           '- Static step-layer plots cover all 57 layers and all 15 steps, not a selected subset.',
           '- The fixed source GT is not a tracked generated head. Uncontrolled displacement can invalidate semantic comparisons at these coordinates.',
           '- Attention magnitude and grouped AV norms cannot establish causality. Outside-image mass also depends on the number of outside keys.',
           '- Endpoint images are direct noisy-latent decodes, not x0 predictions. They are for qualitative diagnosis, not new scores.',
           '','## Early Midpoint Summary','',
           'Means across steps 0-6, all recorded layers, heads, and fixed GT queries. Joint weights; no text-only renormalization.',
           '','|Case|Condition|Edit attention|Subject attention|Outside-image mass|','|---|---|---:|---:|---:|']
    for r in summaries:
        lines.append(f"|{r['case']}|{r['condition']}|{r['edit_attention']:.6f}|{r['subject_attention']:.6f}|{r['outside_image_mass']:.6f}|")
    lines+=['','## Cases','']
    for case in cases:
        lines += [f'### {case}',f'[Interactive attention matrices]({case}/index.html)',
                  f'![All layers and steps, midpoint]({case}/layers_steps_midpoint.png)',
                  f'[Start evaluation]({case}/layers_steps_start.png) | [Full-precision summary table]({case}/metrics.csv)']
        if decode: lines += [f'[Uncontrolled endpoint sequence]({case}/uncontrolled_steps.html) | [RK2 endpoint sequence]({case}/rk2_gt_n07_steps.html)']
    lines+=['','## Interpretation Boundary','',
            'Compare successful and failed references before attributing failure to low edit attention. An edit-weight difference is an observation, not proof that increasing it will improve semantics. If uncontrolled shows target features but RK2 does not, inspect spatial support and update diagnostics; if both fail, a separate prompt/initialization experiment is required.',
            '',f'Raw server root: `{root}`. Lightweight export contains no full attention tensors or model weights.']
    (export/'README.md').write_text('\n'.join(lines)+'\n')
    links=''.join(f'<li><a href="{c}/index.html">{c}: attention matrices</a></li>' for c in cases)
    (export/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Rich routing results</title><h1>Rich attention diagnostic</h1><p>Local portable results. Detailed report: README.md; tables: summary.csv.</p><ul>'+links+'</ul>')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path);parser.add_argument('--case',action='append',required=True)
    parser.add_argument('--export',type=Path,required=True);parser.add_argument('--decode',action='store_true')
    args=parser.parse_args();report(args.root,args.case,args.export,args.decode)
