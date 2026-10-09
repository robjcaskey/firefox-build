#!/usr/bin/env python3
"""Compare compositor captures, excluding changing browser UI."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--scale',type=float,default=1.5);p.add_argument('--gpu',action='store_true');args=p.parse_args();suffix='-gpu' if args.gpu else ''
images={mode:np.array(Image.open(ROOT/'artifacts'/(f'{args.scale}-{mode}'+suffix)/'screen.png').convert('RGB')) for mode in ['gray','subpixel']}
# Locate the physical-pixel stripe run rather than assuming browser toolbar size.
image=images['gray'];runs=[]
for y,row in enumerate(image):
    equal=np.all(row[:,0:1]==row,axis=1)
    binary=equal & ((row[:,0]==0)|(row[:,0]==255))
    edges=binary[:-1]&binary[1:]&(row[:-1,0]!=row[1:,0])
    indices=np.flatnonzero(edges)
    if len(indices):
        starts=np.r_[0,np.flatnonzero(np.diff(indices)>1)+1];ends=np.r_[starts[1:],len(indices)]
        for start,end in zip(starts,ends):
            if end-start>args.scale*390:runs.append((y,int(indices[start]),int(indices[end-1]+2)))
assert runs,'No native physical-pixel stripe run: possible compositor resampling'
y,x0,x1=runs[len(runs)//2]
if image[y,x0,0]==255:x0+=1
assert x1-x0==round(400*args.scale),(x0,x1,args.scale)
for mode,im in images.items():
    assert np.array_equal(im[y,x0:x1],image[y,x0:x1]),f'{mode}: calibration changed'
# Below the calibration/control area: use the black/white text panels only.
start=max(r[0] for r in runs)+round(90*args.scale)
end=min(start+round(380*args.scale),image.shape[0])
records={}
for mode,im in images.items():
    crop=im[start:end,:round(1000*args.scale)]
    chromatic=np.max(crop,axis=2).astype(int)-np.min(crop,axis=2).astype(int)
    records[mode]={'chromatic_pixels':int(np.count_nonzero(chromatic>2)),'changed_vs_gray':int(np.count_nonzero(np.any(crop!=images['gray'][start:end,:crop.shape[1]],axis=2)))}
assert records['subpixel']['changed_vs_gray']>0,records
assert records['subpixel']['chromatic_pixels']>records['gray']['chromatic_pixels'],records
result={'scale':args.scale,'stripe_pixels':x1-x0,'sample_rows':[start,end],'modes':records}
print(json.dumps(result,indent=2));(ROOT/'artifacts'/f'comparison-{args.scale}{suffix}.json').write_text(json.dumps(result,indent=2)+'\n')
