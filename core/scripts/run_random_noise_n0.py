#!/usr/bin/env python3
"""Six-case random-noise baseline matched to the inversion N=0 diagnostic."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'core/third_party/FollowYourShape/src'))


def configuration():
    return dict(protocol='random_noise_n0_v1',initialization='random_noise',inversion=False,
        control_duration=0,num_steps=15,guidance=2.0,seed=0,width=1024,height=1024,
        model_name='flux-dev',noise='CPU float32 standard normal seeded 0, cast to bfloat16; identical saved tensor reused for all six prompts',
        image_kv='none',attention_control='none',controlnet='none',mask=None,
        solver='existing flux.sampling.denoise explicit midpoint RK2',
        comparison_commit='6d3fb43775a6f888b1130ce6d4720392c0d9953b',
        interpretation='Generative composition diagnostic; random initialization does not preserve source layout or establish local editing success')


def make_noise():
    import torch
    return torch.randn((1,16,128,128),generator=torch.Generator(device='cpu').manual_seed(0),dtype=torch.float32).to(torch.bfloat16)


def sample_uncontrolled(model,inputs,timesteps,guidance):
    from flux.sampling import denoise
    trace=[]
    def observe(**kwargs):
        info=kwargs['info']
        if info['inject'] or info['inverse'] or info.get('attention_control') is not None:
            raise RuntimeError('unexpected control/inversion in random-noise baseline')
        trace.append(dict(call=len(trace),timestep=float(kwargs['timesteps'][0]),
            inject=bool(info['inject']),inverse=bool(info['inverse']),second_order=bool(info['second_order'])))
        return model(**kwargs)
    result,_=denoise(observe,**inputs,timesteps=timesteps,inverse=False,
        info={'image_kv_layers':()},inject_list=[False]*(len(timesteps)-1),guidance=guidance,
        controlnet=None,record_source_latents=False)
    if len(trace)!=2*(len(timesteps)-1):
        raise RuntimeError('wrong model call count')
    return result,trace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    cfg=configuration()
    manifest=ROOT/'core/protocols/gt_prefix_diagnostic_v1/manifest.json'
    records=json.loads(manifest.read_text())
    print(json.dumps(cfg,indent=2),flush=True)
    if not args.execute:
        print('Dry run:',[r['case_uid'] for r in records]);return 0
    import numpy as np
    import torch
    from PIL import Image,ExifTags
    from einops import rearrange
    from flux.sampling import prepare,get_schedule,unpack
    from flux.util import load_t5,load_clip,load_flow_model,load_ae,embed_watermark
    from transformers import pipeline
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise RuntimeError('require clean committed experiment checkout')
    fys_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'core/third_party/FollowYourShape',text=True).strip()
    if fys_commit!='b096e8f7736b0f44d820933d5046fe252059a5eb':raise RuntimeError('FYS revision changed')
    dest=ROOT/'core/results/random_noise_n0_v1'
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir(parents=True)
    cfg.update(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        fys_commit=fys_commit,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        torch=torch.__version__,cuda=torch.version.cuda,python=sys.version)
    (dest/'protocol.json').write_text(json.dumps(cfg,indent=2)+'\n')
    random.seed(0);np.random.seed(0);torch.manual_seed(0);torch.cuda.manual_seed_all(0)
    classifier=pipeline('image-classification',model='Falconsai/nsfw_image_detection',device='cuda')
    t5=load_t5('cuda',max_length=512);clip=load_clip('cuda')
    model=load_flow_model('flux-dev',device='cpu').eval();ae=load_ae('flux-dev',device='cpu').eval()
    noise=make_noise();torch.save(noise,dest/'initial_noise.pt')
    noise_hash=hashlib.sha256(noise.view(torch.uint8).numpy().tobytes()).hexdigest()
    with torch.inference_mode():
        for r in records:
            start=time.monotonic();print('START',r['case_uid'],r['target_prompt'],flush=True)
            folder=dest/r['case_uid']/'seed_000';folder.mkdir(parents=True)
            ae.cpu();model.cpu();torch.cuda.empty_cache()
            t5.to('cuda');clip.to('cuda')
            inputs=prepare(t5,clip,noise.clone().to('cuda'),prompt=r['target_prompt'])
            schedule=get_schedule(15,inputs['img'].shape[1],shift=True)
            t5.cpu();clip.cpu();torch.cuda.empty_cache();model.to('cuda')
            latent,trace=sample_uncontrolled(model,inputs,schedule,2.0)
            if not torch.isfinite(latent).all():raise RuntimeError('non-finite final latent')
            model.cpu();torch.cuda.empty_cache();ae.decoder.to('cuda')
            with torch.autocast(device_type='cuda',dtype=torch.bfloat16):
                decoded=ae.decode(unpack(latent.float(),1024,1024))
            decoded=embed_watermark(decoded.clamp(-1,1).float())
            image=Image.fromarray((127.5*(rearrange(decoded[0],'c h w -> h w c')+1)).cpu().byte().numpy())
            nsfw_score=next(v['score'] for v in classifier(image) if v['label']=='nsfw')
            if nsfw_score>=.85:raise RuntimeError('output withheld by existing NSFW threshold')
            exif=Image.Exif();exif[ExifTags.Base.Software]='AI generated;txt2img;flux';exif[ExifTags.Base.Make]='Black Forest Labs';exif[ExifTags.Base.Model]='flux-dev'
            image.save(folder/'img_0.jpg',exif=exif,quality=95,subsampling=0)
            record=dict(**cfg,case_uid=r['case_uid'],target_prompt=r['target_prompt'],
                initial_noise_sha256=noise_hash,timesteps=schedule,seconds=time.monotonic()-start,nsfw_score=nsfw_score)
            (folder/'run_config.json').write_text(json.dumps(record,indent=2)+'\n')
            (folder/'sampling_trace.json').write_text(json.dumps(trace,indent=2)+'\n')
            print('DONE',r['case_uid'],record['seconds'],flush=True)
            del inputs,latent,decoded
    print('COMPLETE 6/6',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
