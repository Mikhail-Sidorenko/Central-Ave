import numpy as np
from PIL import Image
AX=[0,4130,7100,13900]; AY=[0,3850,10150,14130,16130]
CFG={'f1':('/home/claude/pg/f1.png',[663,993,1232,1774],[339,677,1209,1539,1702]),
     'f2':('/home/claude/pg/f2.png',[585,912,1158,1729],[333,666,1204,1537,1702]),
     'f3':('/home/claude/pg/f3.png',[630,963,1208,1757],[339,673,1203,1531,1693])}
def mp(m,mm,px):
    m=np.asarray(m,float); out=np.interp(m,mm,px)
    lo=m<mm[0]; hi=m>mm[-1]
    out[lo]=px[0]+(m[lo]-mm[0])*(px[1]-px[0])/(mm[1]-mm[0])
    out[hi]=px[-1]+(m[hi]-mm[-1])*(px[-1]-px[-2])/(mm[-1]-mm[-2])
    return out
S=0.06; X0,X1,Y0,Y1=-2500,16500,-2500,18500
for k,(p,cx,cy) in CFG.items():
    src=np.array(Image.open(p).convert('L'))
    xs=np.arange(X0,X1,1/S); ys=np.arange(Y0,Y1,1/S)
    sx=np.clip(mp(xs,AX,cx).round().astype(int),0,src.shape[1]-1)
    sy=np.clip(mp(ys,AY,cy).round().astype(int),0,src.shape[0]-1)
    out=src[sy][:,sx]
    # whiten paper
    out=np.clip((out.astype(float)-60)*255/(215-60),0,255).astype(np.uint8)
    Image.fromarray(out).save(f'/home/claude/work/{k}_rect.jpg',quality=55)
    print(k,out.shape)
