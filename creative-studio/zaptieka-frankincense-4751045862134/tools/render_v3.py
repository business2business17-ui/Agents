from pathlib import Path
import json, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageCms, ImageFile, ImageOps
ImageFile.LOAD_TRUNCATED_IMAGES=True
ROOT=Path(__file__).resolve().parents[3]
PROJECT=Path(__file__).resolve().parents[1]
OUT=PROJECT/'v3'
BG=OUT/'backgrounds'
GREEN='#193c2b'
ICC=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
FONTS={'serif':'georgia.ttf','italic':'georgiai.ttf','sans':'arial.ttf'}
assets=[]
def cutout():
    im=Image.open(ROOT/'images/4751045862134.png').convert('RGB')
    small=im.resize((im.width//3,im.height//3))
    ImageDraw.floodfill(small,(0,0),(255,0,255),thresh=9)
    a=np.array(small)
    mask=Image.fromarray((~((a[:,:,0]==255)&(a[:,:,1]==0)&(a[:,:,2]==255))*255).astype('uint8')).filter(ImageFilter.MedianFilter(5))
    mask=mask.resize(im.size,Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(2))
    mask=mask.point(lambda v:255 if v>200 else 0 if v<60 else int((v-60)*255/140))
    im.putalpha(mask)
    return im.crop(im.getbbox())
PACK=cutout()
BAR=Image.open(ROOT/'images/ZAptieka-amazon/20261017_100454.png').convert('RGBA')
BAR=BAR.crop(BAR.getbbox())
def product(im,x,bottom,width,unwrapped=False):
    W,H=im.size; src=BAR if unwrapped else PACK
    src=src.resize((round(width*W),round(width*W*src.height/src.width)),Image.Resampling.LANCZOS)
    px,py=round(x*W),round(bottom*H)-src.height
    assert px>=0 and py>=0 and px+src.width<=W and py+src.height<=H
    layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer)
    d.ellipse((px+src.width*.03,py+src.height-W*.008,px+src.width*1.08,py+src.height+W*.012),fill=(48,39,28,72))
    layer=layer.filter(ImageFilter.GaussianBlur(W*.006))
    out=Image.alpha_composite(im.convert('RGBA'),layer);out.alpha_composite(src,(px,py))
    return out.convert('RGB')
def text(im,t,x,y,size=.035,kind='sans',maxw=.9):
    W,H=im.size; d=ImageDraw.Draw(im); fs=round(size*W)
    f=ImageFont.truetype('C:/Windows/Fonts/'+FONTS[kind],fs)
    while d.textbbox((0,0),t,font=f)[2]>maxw*W:
        fs-=1; f=ImageFont.truetype('C:/Windows/Fonts/'+FONTS[kind],fs)
    box=d.textbbox((x*W,y*H),t,font=f,anchor='lt')
    assert box[2]<=W and box[3]<=H,(t,box)
    d.text((round(x*W),round(y*H)),t,font=f,fill=GREEN,anchor='lt')
def rule(im,x,y,width):
    W,H=im.size
    ImageDraw.Draw(im).line((x*W,y*H,(x+width)*W,y*H),fill=GREEN,width=max(2,round(W*.00065)))
def base(name,size):
    p=BG/name
    if name=='P3_Premium_Ritual.png' and p.exists():
        src=Image.open(p).convert('RGB')
        scaled=src.resize((round(src.width*size[1]/src.height),size[1]),Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',size)
        gap=size[0]-scaled.width
        if gap>0:
            wall=src.crop((int(src.width*.20),0,int(src.width*.30),src.height))
            canvas.paste(wall.resize((gap,size[1]),Image.Resampling.LANCZOS),(0,0))
            canvas.paste(scaled,(gap,0))
            ImageDraw.Draw(canvas).rectangle((0,0,round(size[0]*.60),size[1]),fill='#eee7db')
            return canvas
    return ImageOps.fit(Image.open(p).convert('RGB'),size,method=Image.Resampling.LANCZOS) if p.exists() else None
def save(im,name,copy,scene,bg=None,unwrapped=False):
    p=OUT/name
    im.save(p,'JPEG',quality=95,subsampling=0,optimize=True,icc_profile=ICC,dpi=(300,300))
    assets.append(dict(file=name,copy=copy,layout=scene,source='images/ZAptieka-amazon/20261017_100454.png' if unwrapped else 'images/4751045862134.png',background=bg,product_state='unwrapped' if unwrapped else 'packaged',dimensions=f'{im.width} x {im.height}',bytes=p.stat().st_size,placement='pdp-main' if name.startswith('01') else 'aplus-basic' if name.startswith('B') else 'aplus-premium' if name.startswith('P') else 'pdp-secondary'))
save(Image.open(PROJECT/'output/01_MAIN.jpg').convert('RGB').resize((4000,4000),Image.Resampling.LANCZOS),'01_MAIN.jpg','','Original packaged product on pure white.')
im=base('02_Hero_provider.png',(4000,4000))
if im:
    im=product(im,.085,.865,.235)
    text(im,'NATURAL SOAP BAR',.535,.10,.018,maxw=.42);rule(im,.535,.145,.09)
    text(im,'Frankincense',.535,.19,.065,'serif',.425)
    text(im,'soap for calm,',.535,.285,.047,'italic',.42);text(im,'soft skin',.535,.35,.047,'italic',.42);rule(im,.535,.435,.14)
    for i,t in enumerate(['Soothing daily cleanse.','Comfort for','sensitive-feeling skin.']):text(im,t,.535,.48+i*.043,.025,maxw=.42)
    save(im,'02_Hero.jpg','NATURAL SOAP BAR\nFrankincense\nsoap for calm,\nsoft skin\nSoothing daily cleanse.\nComfort for\nsensitive-feeling skin.','AI adult at bathroom mirror; original packaged soap on dry foreground stone.','02_Hero_provider.png')
im=base('03_Benefits.png',(4000,4000))
if im:
    im=product(im,.09,.975,.22);text(im,'Key benefits',.55,.14,.055,'serif',.40)
    blocks=[['Soothing daily','cleanse'],['Comfort for','sensitive-feeling skin'],['Leaves skin','feeling soft'],['For face & body']]
    for j,lines in enumerate(blocks):
        y=.30+j*.145;rule(im,.55,y-.025,.34)
        for k,t in enumerate(lines):text(im,t,.55,y+k*.038,.029,maxw=.40)
    save(im,'03_Benefits.jpg','Key benefits\nSoothing daily cleanse\nComfort for sensitive-feeling skin\nLeaves skin feeling soft\nFor face & body','AI adult drying face; packaged soap on dry counter.','03_Benefits.png')
im=base('04_How_to_use.png',(4000,4000))
if im:
    im=product(im,.76,.86,.18);text(im,'How to use',.07,.07,.069,'serif')
    steps=[('01','Wet hands and the soap bar'),('02','Lather and cleanse gently'),('03','Rinse well; let the bar dry between uses')]
    for i,(n,t) in enumerate(steps):
        y=.21+i*.087;text(im,n,.07,y,.033,'italic');text(im,t,.16,y,.029,maxw=.77)
    save(im,'04_How_to_use.jpg','How to use\nWet hands and the soap bar\nLather and cleanse gently\nRinse well; let the bar dry between uses','Lathered adult hands at sink; packaged product on a separate dry ledge.','04_How_to_use.png')
im=base('05_Ingredients.png',(4000,4000))
if im:
    im=product(im,.075,.86,.32,True);text(im,"What's inside",.535,.12,.058,'serif',.42)
    pairs=[('Frankincense','Boswellia Carterii Oil'),('Shea butter','Butyrospermum Parkii Butter'),('Coconut oil','Cocos Nucifera Oil')]
    for i,(a,b) in enumerate(pairs):
        y=.32+i*.17;rule(im,.535,y-.025,.36);text(im,a,.535,y,.041,'serif',.42);text(im,b,.535,y+.057,.020,maxw=.42)
    save(im,'05_Ingredients.jpg',"What's inside\nFrankincense\nBoswellia Carterii Oil\nShea butter\nButyrospermum Parkii Butter\nCoconut oil\nCocos Nucifera Oil",'Only unwrapped bar in series; original photographic texture; bathroom vanity.','05_Ingredients.png',True)
im=base('06_Size_weight.png',(4000,4000))
if im:
    im=product(im,.64,.815,.22);text(im,'Size & weight',.07,.10,.066,'serif',.60)
    text(im,'100 g',.07,.28,.10,'serif');rule(im,.07,.43,.24);text(im,'8 × 5 × 2.5 cm',.07,.48,.039,maxw=.53)
    save(im,'06_Size_weight.jpg','Size & weight\n100 g\n8 × 5 × 2.5 cm','Packaged soap on bathroom shelf; adult AI model in background; source table measurements.','06_Size_weight.png')
im=base('07_Ritual.png',(4000,4000))
if im:
    im=product(im,.65,.89,.24);text(im,'Your daily',.07,.10,.058,'serif',.51);text(im,'cleansing ritual',.07,.18,.058,'serif',.51)
    rule(im,.07,.29,.20);text(im,'Frankincense soap for',.07,.34,.035,'italic',.49);text(im,'calm, soft skin',.07,.39,.035,'italic',.49)
    save(im,'07_Ritual.jpg','Your daily cleansing ritual\nFrankincense soap for calm, soft skin','AI adult in closed robe beside shower; packaged soap outside wet zone.','07_Ritual.png')
wide_specs=[('B1_Basic_Hero',(970,600),['Frankincense'],['soap for calm,','soft skin'],['Soothing daily cleanse.','Comfort for sensitive-feeling skin.']),('B2_Basic_Ritual',(970,600),['A gentle','daily ritual'],[],['Wet. Lather. Rinse.','Let the bar dry between uses.']),('B3_Basic_Ingredients',(970,600),["What's inside"],[],['Frankincense — Boswellia Carterii Oil','Shea butter · Coconut oil','100 g']),('P1_Premium_Hero',(1464,600),['Frankincense'],['soap for calm, soft skin'],[]),('P2_Premium_Ingredients',(1464,600),['Frankincense'],['Boswellia Carterii Oil'],['Shea butter · Coconut oil']),('P3_Premium_Ritual',(1464,600),['Your daily','cleansing ritual'],[],['Wet. Lather. Rinse.','Let the bar dry between uses. · 100 g'])]
for stem,size,titles,subs,body in wide_specs:
    im=base(stem+'.png',(size[0]*2,size[1]*2))
    if im is None:continue
    basic=stem.startswith('B');im=product(im,.80 if stem.startswith(chr(80)+chr(51)) else .76,.95 if stem.startswith(chr(80)+chr(51)) else .84,.17 if basic else .12)
    text(im,'ZAptieka',.055,.07,.016,maxw=.5);y=.18
    for t in titles:
        text(im,t,.055,y,.052 if basic else .046,'serif',.56);y+=.115 if basic else .145
    y+=.025
    for t in subs:
        text(im,t,.055,y,.034 if basic else .029,'italic',.55);y+=.080 if basic else .11
    rule(im,.055,y+.025,.12);y+=.085
    for t in body:
        text(im,t,.055,y,.022 if basic else .018,maxw=.56);y+=.064 if basic else .08
    im=im.resize(size,Image.Resampling.LANCZOS)
    save(im,stem+'.jpg','\n'.join(['ZAptieka']+titles+subs+body),'Lifestyle bathroom with AI adults; original packaged product on dry foreground surface.',stem+'.png')
thumbw,thumbh=460,490
sheet=Image.new('RGB',(thumbw*min(4,len(assets)),thumbh*((len(assets)+3)//4)),'#f7f5ef');d=ImageDraw.Draw(sheet)
for i,a in enumerate(assets):
    im=Image.open(OUT/a['file']);im.thumbnail((440,445))
    x=(i%4)*thumbw+(thumbw-im.width)//2;y=(i//4)*thumbh+32
    sheet.paste(im,(x,y));d.text(((i%4)*thumbw+12,(i//4)*thumbh+9),a['file'],font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17),fill=GREEN)
sheet.save(OUT/'PREVIEW.jpg',quality=93)
(OUT/'manifest.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2),encoding='utf-8')
if len(assets)==13:
    assert sum(a['product_state']=='unwrapped' for a in assets)==1
    with zipfile.ZipFile(PROJECT/'ZAptieka_13_images_v3.zip','w',zipfile.ZIP_DEFLATED) as z:
        for a in assets:z.write(OUT/a['file'],a['file'])
print(json.dumps({'exported':len(assets),'files':[a['file'] for a in assets]},ensure_ascii=False))
