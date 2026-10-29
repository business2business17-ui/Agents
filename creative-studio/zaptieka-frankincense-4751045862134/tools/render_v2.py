"""Photographic source compositing. Product pixels are not generated or retouched."""
from pathlib import Path
import json, math, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageCms, ImageFile, ImageOps
ImageFile.LOAD_TRUNCATED_IMAGES = True  # supplied PNGs contain a bad ancillary eXIf CRC
ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / 'v2'
OUT.mkdir(exist_ok=True)
SRC = ROOT / 'images/ZAptieka-amazon'
GREEN = '#193c2b'
FONTS = Path('C:/Windows/Fonts')
FONT = {'serif':'georgia.ttf','italic':'georgiai.ttf','sans':'arial.ttf','bold':'arialbd.ttf'}
ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
W = 4000
bg_original = Image.open(SRC/'ZAptieka_Frankincense_Hero_v2_4000x4000-1(1).jpg').convert('RGB')
# Remove the entire bottom strip containing a source service watermark by framing.
bg_original = bg_original.crop((0,0,bg_original.width,bg_original.height-180))

def backdrop(resin=False):
    if not resin:
        return bg_original.crop((0,0,650,bg_original.height)).resize((W,W),Image.Resampling.LANCZOS)
    base=bg_original.resize((W,W),Image.Resampling.LANCZOS)
    # Replace the source typography with empty photographic wall from that same photo.
    clear=bg_original.crop((0,0,1700,1450)).resize((W,2100),Image.Resampling.LANCZOS)
    layer=Image.new('RGB',(W,W)); layer.paste(clear,(0,0))
    mask=Image.new('L',(W,W)); d=ImageDraw.Draw(mask); d.rectangle((0,0,W,1950),fill=255)
    for y in range(1950,2100): d.line((0,y,W,y),fill=round(255*(2100-y)/150))
    return Image.composite(layer,base,mask)

plain=backdrop(); resin_bg=backdrop(True)

def font(kind,size): return ImageFont.truetype(str(FONTS/FONT[kind]),round(size*W))

def txt(im,text,x,y,size=.04,kind='sans',maxw=.88):
    f=font(kind,size); draw=ImageDraw.Draw(im)
    # Fit only where explicitly constrained; no raster stretching of letters.
    while draw.textbbox((0,0),text,font=f)[2]>maxw*W:
        size-=.0005; f=font(kind,size)
    draw.text((round(x*W),round(y*W)),text,font=f,fill=GREEN,anchor='lt')

def line(im,x,y,length):
    ImageDraw.Draw(im).line((int(x*W),int(y*W),int((x+length)*W),int(y*W)),fill=GREEN,width=3)

def product(im,name,x,bottom,width):
    src=Image.open(SRC/name).convert('RGBA'); src=src.crop(src.getbbox())
    src=src.resize((round(width*W),round(width*W*src.height/src.width)),Image.Resampling.LANCZOS)
    px,py=round(x*W),round(bottom*W)-src.height
    # Shadow exists on its own layer, never painted into the product.
    shadow=Image.new('RGBA',im.size,(0,0,0,0))
    contact=Image.new('RGBA',src.size,(65,48,31,0))
    contact.putalpha(src.getchannel('A').point(lambda a:round(a*.30)))
    shadow.alpha_composite(contact,(px+round(W*.003),py+round(W*.004)))
    shadow=shadow.filter(ImageFilter.GaussianBlur(max(3,W*.003)))
    canvas=Image.alpha_composite(im.convert('RGBA'),shadow)
    canvas.alpha_composite(src,(px,py))
    return canvas.convert('RGB')

assets=[]
def save(im,name,copy,layout,source,aplus=None):
    size=aplus or (4000,4000)
    if im.size!=size: im=im.resize(size,Image.Resampling.LANCZOS)
    p=OUT/name
    im.convert('RGB').save(p,'JPEG',quality=95,subsampling=0,optimize=True,icc_profile=ICC,dpi=(300,300))
    assets.append({'file':name,'copy':copy,'layout':layout,'source':source,'dimensions':f'{size[0]} x {size[1]}','bytes':p.stat().st_size,'placement':'pdp-main' if name.startswith('01') else ('pdp-secondary' if not aplus else 'aplus-basic' if name.startswith('B') else 'aplus-premium')})

# Preserve the existing MAIN product photography rather than regenerate its label.
main=Image.open(PROJECT/'output/01_MAIN.jpg').convert('RGB')
save(main,'01_MAIN.jpg','', 'One packaged product on white; existing photographic composite retained.','images/4751045862134.png')

im=resin_bg.copy(); im=product(im,'20261017_100454.png',.018,.96,.60)
txt(im,'NATURAL SOAP BAR',.525,.05,.019,maxw=.43)
line(im,.525,.098,.08)
txt(im,'Frankincense',.47,.142,.073,'serif',.49)
txt(im,'soap for calm,',.525,.227,.057,'italic',.43)
txt(im,'soft skin',.525,.300,.057,'italic',.43)
line(im,.525,.385,.13)
for i,t in enumerate(['Soothing daily cleanse.','Comfort for','sensitive-feeling skin.']): txt(im,t,.525,.42+i*.036,.025,maxw=.44)
hero='NATURAL SOAP BAR\nFrankincense\nsoap for calm,\nsoft skin\nSoothing daily cleanse.\nComfort for\nsensitive-feeling skin.'
save(im,'02_Hero.jpg',hero,'Reference composition: typography upper right; real unwrapped bar lower left; photographic resin lower right.','20261017_100454.png')

im=plain.copy(); txt(im,'Key benefits',.07,.075,.078,'serif')
im=product(im,'20261017_100405.png',.035,.91,.48)
benefits=['Soothing daily cleanse','Comfort for','sensitive-feeling skin','Leaves skin feeling soft','For face & body']
for y,lines in [(.34,benefits[:1]),(.46,benefits[1:3]),(.63,benefits[3:4]),(.76,benefits[4:])]:
    line(im,.55,y-.025,.35)
    for i,t in enumerate(lines): txt(im,t,.55,y+i*.043,.032,maxw=.40)
save(im,'03_Benefits.jpg','Key benefits\n'+'\n'.join(benefits),'Title top left; source product lower left; four benefit blocks right.','20261017_100405.png')

im=plain.copy(); txt(im,'How to use',.07,.075,.08,'serif')
steps=[('01','Wet hands and','the soap bar'),('02','Lather and','cleanse gently'),('03','Rinse well; let the bar','dry between uses')]
for i,(n,a,b) in enumerate(steps):
    y=.28+i*.19; txt(im,n,.075,y,.047,'italic'); line(im,.20,y-.015,.69)
    txt(im,a,.22,y,.04,maxw=.69); txt(im,b,.22,y+.054,.04,maxw=.69)
im=product(im,'20261017_100454.png',.68,.955,.25)
save(im,'04_How_to_use.jpg','How to use\n1. Wet hands and the soap bar\n2. Lather and cleanse gently\n3. Rinse well; let the bar dry between uses','Three numbered typographic steps; small real bar bottom right.','20261017_100454.png')

im=plain.copy(); txt(im,"What's inside",.07,.075,.078,'serif')
im=product(im,'20261017_100402.png',.035,.93,.47)
ingredients=[('Frankincense','Boswellia Carterii Oil'),('Shea butter','Butyrospermum Parkii Butter'),('Coconut oil','Cocos Nucifera Oil')]
for i,(a,b) in enumerate(ingredients):
    y=.35+i*.17; line(im,.54,y-.03,.37)
    txt(im,a,.54,y,.044,'serif',.40); txt(im,b,.54,y+.062,.019,maxw=.40)
save(im,'05_Ingredients.jpg',"What's inside\n"+'\n'.join(a+'\n'+b for a,b in ingredients),'Unwrapped soap left; three ingredient name pairs right; composition per user table.','20261017_100402.png')

im=plain.copy(); txt(im,'Size & weight',.07,.075,.078,'serif')
txt(im,'100 g',.07,.25,.11,'serif'); line(im,.07,.40,.31)
txt(im,'8 × 5 × 2.5 cm',.07,.445,.048,maxw=.74)
im=product(im,'20261017_100454.png',.27,.94,.65)
save(im,'06_Size_weight.jpg','Size & weight\n100 g\n8 × 5 × 2.5 cm','Large weight upper left; dimensions below; real bar bottom right, no inferred measurement arrows.','20261017_100454.png')

im=plain.copy(); txt(im,'Your daily',.07,.085,.082,'serif'); txt(im,'cleansing ritual',.07,.185,.082,'serif')
line(im,.07,.315,.25); txt(im,'Frankincense soap for',.07,.36,.044,'italic'); txt(im,'calm, soft skin',.07,.42,.044,'italic')
im=product(im,'20261017_100454.png',.30,.96,.65)
save(im,'07_Ritual.jpg','Your daily cleansing ritual\nFrankincense soap for calm, soft skin','Typographic reassurance upper left; real soap lower right on photographic stone.','20261017_100454.png')

# Wide artworks are composed at 2x their final dimensions with normal product proportions.
def widebase(size): return ImageOps.fit(plain,size,method=Image.Resampling.LANCZOS).convert('RGB')
def wide(name,size,title,subtitle,body,source='20261017_100454.png',ingredient=False):
    global W
    old=W; W=size[0]*2
    H=size[1]*2; im=widebase((W,H))
    # Text coordinates below are normalised by canvas width; y values stay width based.
    txt(im,'ZAptieka',.06,.045,.018,'sans',.55)
    ypos=.11
    for t in title.split('\n'):
        txt(im,t,.06,ypos,.047,'serif',.57); ypos+=.061
    if subtitle:
        for t in subtitle.split('\n'):
            txt(im,t,.06,ypos+.01,.035,'italic',.56); ypos+=.046
    line(im,.06,ypos+.032,.15)
    for i,t in enumerate(body.split('\n') if body else []): txt(im,t,.06,ypos+.062+i*.035,.020,maxw=.55)
    # source product is placed in its true source aspect ratio, without a new generated view
    im=product(im,source,.66,H/W-.035,.29)
    copy='\n'.join(t for t in ['ZAptieka',title,subtitle,body] if t)
    save(im,name,copy,'Wide composition: left 56% text, right 29% immutable real product, photographic ivory stone background.',source,size)
    W=old

wide('B1_Basic_Hero.jpg',(970,600),'Frankincense','soap for calm,\nsoft skin','Soothing daily cleanse.\nComfort for sensitive-feeling skin.')
wide('B2_Basic_Ritual.jpg',(970,600),'A gentle\ndaily ritual','','Wet. Lather. Rinse.\nLet the bar dry between uses.','20261017_100405.png')
wide('B3_Basic_Ingredients.jpg',(970,600),"What's inside",'','Frankincense — Boswellia Carterii Oil\nShea butter\nCoconut oil\n100 g')
wide('P1_Premium_Hero.jpg',(1464,600),'Frankincense','soap for calm, soft skin','')
wide('P2_Premium_Ingredients.jpg',(1464,600),'Frankincense','Boswellia Carterii Oil','Shea butter · Coconut oil')
wide('P3_Premium_Ritual.jpg',(1464,600),'Your daily cleansing ritual','','Wet. Lather. Rinse.\nLet the bar dry between uses. · 100 g')

# Contact sheet of all 13 deliverables, labelled outside each artwork.
thumbw=420; thumbh=465
sheet=Image.new('RGB',(thumbw*4,thumbh*4),'#f7f5ef'); d=ImageDraw.Draw(sheet)
for i,a in enumerate(assets):
    im=Image.open(OUT/a['file']); im.thumbnail((400,420))
    x=(i%4)*thumbw+(thumbw-im.width)//2; y=(i//4)*thumbh+30
    sheet.paste(im,(x,y)); d.text(((i%4)*thumbw+12,(i//4)*thumbh+8),a['file'],font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16),fill=GREEN)
sheet.save(OUT/'PREVIEW.jpg',quality=92)
(OUT/'manifest.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(PROJECT/'ZAptieka_13_images_v2.zip','w',zipfile.ZIP_DEFLATED) as z:
    for a in assets: z.write(OUT/a['file'],a['file'])
print(json.dumps({'output':str(OUT),'count':len(assets),'max_bytes':max(a['bytes'] for a in assets)},ensure_ascii=False))
