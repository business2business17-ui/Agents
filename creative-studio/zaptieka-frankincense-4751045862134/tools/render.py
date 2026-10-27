"""Deterministic renderer: real packshot (cut out, never redrawn) + procedural limestone scene + exact text layers."""
import math, random, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ROOT = '/home/user/Agents'
OUT = ROOT + '/creative-studio/zaptieka-frankincense-4751045862134/output'
FD = '/tmp/claude-0/-home-user-Agents/54016bb8-3e0d-50bf-9c20-6b232339a536/scratchpad/fonts/'
GREEN = (31, 61, 43)
SERIF = FD + 'playfair-display-latin-500-normal.woff'
SERIF_I = FD + 'playfair-display-latin-500-italic.woff'
SANS = '/usr/share/fonts/opentype/inter/Inter-Regular.otf'
SANS_L = '/usr/share/fonts/opentype/inter/Inter-Light.otf'
rng = np.random.default_rng(7)

def F(p, s): return ImageFont.truetype(p, int(s))

# ---------- cutout of the real packshot ----------
def cutout(gtin):
    im = Image.open(f'{ROOT}/images/{gtin}.png').convert('RGB')
    small = im.resize((im.width // 3, im.height // 3))
    ImageDraw.floodfill(small, (0, 0), (255, 0, 255), thresh=9)
    a = np.array(small)
    soapm = ~((a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255))
    soapm = Image.fromarray((soapm * 255).astype('uint8')).filter(ImageFilter.MedianFilter(5))
    mask = soapm.resize(im.size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))
    mask = mask.point(lambda v: 255 if v > 200 else (0 if v < 60 else int((v - 60) * 255 / 140)))
    im.putalpha(mask)
    return im.crop(im.getbbox())

_cache = {}
def soap(gtin='4751045862134'):
    if gtin not in _cache: _cache[gtin] = cutout(gtin)
    return _cache[gtin]

# ---------- stone scene ----------
def noise(w, h, scale, seed):
    r = np.random.default_rng(seed)
    sw, sh = max(2, w // scale), max(2, h // scale)
    n = Image.fromarray((r.random((sh, sw)) * 255).astype('uint8')).resize((w, h), Image.BICUBIC)
    return np.array(n).astype('float32') / 255

def stone(w, h, horizon=0.36, tone=0.0, seed=1):
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    light = 1.04 - 0.10 * (x * 0.7 + y * 0.3)               # light from upper left
    wall = np.array([236, 227, 210], 'float32')
    top = np.array([248, 240, 224], 'float32')
    bot = np.array([236, 220, 190], 'float32')
    t = np.clip((y - horizon) / 0.14, 0, 1)[..., None]       # soft horizon blend
    base = top * (1 - t) + bot * t
    base = base * light[..., None] * (1 - tone)
    mott = (noise(w, h, max(8, w // 6), seed) - .5) * 14 + (noise(w, h, max(4, w // 25), seed + 1) - .5) * 9
    grain = (noise(w, h, 2, seed + 2) - .5) * 9 + (noise(w, h, 1, seed + 3) - .5) * 6
    surf = (y > horizon).astype('float32')[..., None] * 0 + np.clip((y - horizon) / 0.14, 0, 1)[..., None]
    img = base + (mott + grain)[..., None] * (0.35 + 0.65 * surf)
    img = np.clip(img, 0, 255).astype('uint8')
    pil = Image.fromarray(img)
    # blur the wall part (depth of field)
    blur = pil.filter(ImageFilter.GaussianBlur(w / 140))
    mk = Image.fromarray((np.clip(1 - (np.linspace(0, 1, h) - horizon + 0.03) / 0.10, 0, 1)[:, None] * np.ones((1, w)) * 255).astype('uint8'))
    pil = Image.composite(blur, pil, mk)
    # vignette
    vg = np.sqrt(((x - .45) ** 2 + (y - .5) ** 2)) * 0.22
    pil = Image.fromarray(np.clip(np.array(pil) * (1 - vg[..., None]), 0, 255).astype('uint8'))
    return pil.convert('RGBA')

def shadow(canvas, alpha_img, pos, dx, dy, blur, strength, color=(92, 70, 40)):
    sh = Image.new('RGBA', alpha_img.size, color + (0,))
    a = alpha_img.split()[3].point(lambda v: int(v * strength))
    sh.putalpha(a)
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    layer.paste(sh, (pos[0] + dx, pos[1] + dy), sh)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(layer)

def place_soap(canvas, gtin, cx, bottom_y, width, angle=0, flip=False):
    s = soap(gtin)
    r = width / s.width
    s = s.resize((width, int(s.height * r)), Image.LANCZOS)
    if flip: s = ImageOps_mirror(s)
    if angle: s = s.rotate(angle, expand=True, resample=Image.BICUBIC)
    x, y = int(cx - s.width / 2), int(bottom_y - s.height)
    W = canvas.width
    # long soft cast shadow (light from upper-left -> falls right/down) + tight contact shadow
    foot = s.copy()
    shadow(canvas, foot, (x, y), int(W * .035), int(W * .012), W * .018, .30)
    shadow(canvas, foot, (x, y), int(W * .006), int(W * .004), W * .004, .38, (60, 45, 25))
    canvas.alpha_composite(s, (x, y))
    return (x, y, s.width, s.height)

def ImageOps_mirror(im): return im.transpose(Image.FLIP_LEFT_RIGHT)

# ---------- frankincense resin (procedural) ----------
def resin_piece(size, seed):
    r = np.random.default_rng(seed)
    n = 16
    ang = np.sort(r.random(n) * 2 * math.pi)
    rad = size / 2 * (0.62 + 0.38 * r.random(n))
    pts = [(size + rad[i] * math.cos(ang[i]) * (1.0 + .25 * r.random()), size + rad[i] * math.sin(ang[i]) * (0.78 + .2 * r.random())) for i in range(n)]
    S = size * 2
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size * .03))
    yy, xx = np.mgrid[0:S, 0:S].astype('float32')
    d = np.sqrt(((xx - S * .42) / S) ** 2 + ((yy - S * .38) / S) ** 2)
    base = np.stack([np.interp(d, [0, .45], [245, 168]), np.interp(d, [0, .45], [196, 104]), np.interp(d, [0, .45], [108, 38])], -1)
    tex = (noise(S, S, max(3, S // 14), seed) - .5) * 46 + (noise(S, S, 2, seed + 5) - .5) * 14
    # facets: random light/dark bands
    fac = (noise(S, S, max(6, S // 5), seed + 9) - .5) * 60
    col = np.clip(base + tex[..., None] + fac[..., None], 0, 255).astype('uint8')
    img = Image.fromarray(col).convert('RGBA')
    # specular highlights
    hl = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([S * .32, S * .28, S * .48, S * .38], fill=(255, 244, 205, 200))
    hl = hl.filter(ImageFilter.GaussianBlur(size * .05))
    img.alpha_composite(hl)
    # rim darkening (inner translucency edge)
    edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(max(3, int(size * .12)) | 1)))
    edge = edge.filter(ImageFilter.GaussianBlur(size * .04))
    dark = Image.new('RGBA', (S, S), (110, 62, 20, 0)); dark.putalpha(edge.point(lambda v: int(v * .55)))
    img.alpha_composite(dark)
    img.putalpha(mask)
    return img.crop(img.getbbox())

def place_resin(canvas, items, W):
    for i, (cx, cy, sz, rot) in enumerate(items):
        p = resin_piece(int(sz), 100 + i * 13).rotate(rot, expand=True, resample=Image.BICUBIC)
        x, y = int(cx - p.width / 2), int(cy - p.height / 2)
        shadow(canvas, p, (x, y), int(W * .012), int(W * .008), W * .008, .38, (84, 52, 18))
        shadow(canvas, p, (x, y), int(W * .003), int(W * .003), W * .0025, .35, (60, 36, 12))
        canvas.alpha_composite(p, (x, y))

# ---------- typography ----------
def text(d, xy, s, font, fill=GREEN, track=0, anchor='la'):
    x, y = xy
    if not track:
        d.text((x, y), s, font=font, fill=fill, anchor=anchor); return font.getlength(s)
    tot = sum(font.getlength(c) + track for c in s) - track
    if anchor[0] == 'm': x -= tot / 2
    for c in s:
        d.text((x, y), c, font=font, fill=fill, anchor='l' + anchor[1]); x += font.getlength(c) + track
    return tot

def fit(s, path, maxw, start):
    sz = start
    while F(path, sz).getlength(s) > maxw: sz -= 2
    return sz

def rule(d, x, y, w, t, fill=GREEN):
    d.rectangle([x, y, x + w, y + max(1, int(t))], fill=fill)

def lines(d, x, y, arr, font, gap, fill=GREEN, anchor='la'):
    for s in arr:
        d.text((x, y), s, font=font, fill=fill, anchor=anchor); y += gap
    return y

# ---------- simple line icons ----------
def icon(d, kind, cx, cy, r, w):
    c = GREEN
    if kind == 'drop':
        pts = [(cx, cy - r)] + [(cx + r * .72 * math.sin(t), cy + r * .1 + r * .72 * -math.cos(t) * -1) for t in np.linspace(-2.4, 2.4, 40)]
        d.polygon([(cx, cy - r), (cx + r * .68, cy + r * .25), (cx, cy + r), (cx - r * .68, cy + r * .25)], outline=None)
        d.line([(cx, cy - r), (cx + r * .62, cy + r * .2)], fill=c, width=w, joint='curve')
        d.line([(cx, cy - r), (cx - r * .62, cy + r * .2)], fill=c, width=w, joint='curve')
        d.arc([cx - r * .66, cy - r * .3, cx + r * .66, cy + r * 1.02], 0, 180, fill=c, width=w)
    elif kind == 'wave':
        for k in (-1, 0, 1):
            pts = [(cx + t * r, cy + k * r * .6 + math.sin(t * 5) * r * .16) for t in np.linspace(-1, 1, 40)]
            d.line(pts, fill=c, width=w, joint='curve')
    elif kind == 'soft':
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
        d.arc([cx - r * .55, cy - r * .35, cx + r * .55, cy + r * .5], 20, 160, fill=c, width=w)
        d.ellipse([cx - r * .4, cy - r * .35, cx - r * .28, cy - r * .23], fill=c)
        d.ellipse([cx + r * .28, cy - r * .35, cx + r * .4, cy - r * .23], fill=c)
    elif kind == 'all':
        for k, rr in enumerate((1, .66, .33)):
            d.ellipse([cx - r * rr, cy - r * rr, cx + r * rr, cy + r * rr], outline=c, width=w)
    elif kind == 'foam':
        for ox, oy, rr in ((-.35, .15, .5), (.3, .2, .42), (0, -.3, .45), (.45, -.25, .22)):
            d.ellipse([cx + ox * r - rr * r, cy + oy * r - rr * r, cx + ox * r + rr * r, cy + oy * r + rr * r], outline=c, width=w)
    elif kind == 'rinse':
        for ox in (-.5, 0, .5):
            d.line([(cx + ox * r, cy - r * .8), (cx + ox * r - r * .12, cy + r * .1)], fill=c, width=w)
            d.arc([cx + ox * r - r * .2, cy + r * .1, cx + ox * r + r * .08, cy + r * .5], 0, 180, fill=c, width=w)
        d.arc([cx - r, cy + r * .4, cx + r, cy + r * 1.2], 0, 180, fill=c, width=w)

# ---------- text blocks reused ----------
def hero_text(canvas, x, y, W_, u):
    d = ImageDraw.Draw(canvas)
    text(d, (x, y), 'NATURAL SOAP BAR', F(SANS_L, 15 * u), track=5 * u)
    rule(d, x, y + 34 * u, 70 * u, 1.4 * u)
    fs = fit('Frankincense', SERIF, W_, 190 * u)
    d.text((x - 3 * u, y + 62 * u), 'Frankincense', font=F(SERIF, fs), fill=GREEN)
    yy = y + 62 * u + fs * 1.22
    rule(d, x, yy, W_, 1.4 * u)
    fi = fs * .5
    yy = lines(d, x, yy + 16 * u, ['soap for calm,', 'soft skin'], F(SERIF_I, fi), fi * 1.12)
    rule(d, x, yy + 14 * u, W_, 1.4 * u)
    lines(d, x, yy + 40 * u, ['Soothing daily cleanse.', 'Comfort for', 'sensitive-feeling skin.'], F(SANS, 25 * u), 34 * u)

def save(img, name, size, quality=95):
    os.makedirs(OUT, exist_ok=True)
    img = img.convert('RGB')
    if img.size != size: img = img.resize(size, Image.LANCZOS)
    p = f'{OUT}/{name}'
    img.save(p, 'JPEG', quality=quality, subsampling=0, dpi=(300, 300))
    print(name, size, os.path.getsize(p) // 1024, 'KB')

def head(d, W, y, s, u, x=None, anchor='ma'):
    fs = fit(s, SERIF, W * .86, 78 * u)
    d.text((W / 2 if x is None else x, y), s, font=F(SERIF, fs), fill=GREEN, anchor=anchor)
    return fs

# ====================================================================
def carousel():
    W = 4000; u = W / 1000
    # 1 MAIN
    c = Image.new('RGBA', (W, W), (255, 255, 255, 255))
    s = soap(); r = (W * .88) / s.width
    s = s.resize((int(s.width * r), int(s.height * r)), Image.LANCZOS)
    x, y = (W - s.width) // 2, (W - s.height) // 2 - int(W * .01)
    shadow(c, s, (x, y), 0, int(W * .012), W * .012, .22, (60, 60, 60))
    c.alpha_composite(s, (x, y)); save(c, '01_MAIN.jpg', (W, W))

    # 2 Hero
    c = stone(W, W, .36, seed=2)
    place_soap(c, '4751045862134', 1250, 3500, 1950, angle=7)
    place_resin(c, [(2750, 3250, 230, 20), (3080, 3430, 170, 70), (3400, 3200, 290, 5), (2900, 3700, 150, 110), (3680, 3520, 210, 40),
                    (3420, 3720, 140, 160), (2640, 3620, 120, 10)], W)
    hero_text(c, 2030, 300, 1750, int(u))
    # (text above is in 1000-unit design space scaled by u)
    save(c, '02_Hero.jpg', (W, W))

    # 3 Key benefits
    c = stone(W, W, .30, seed=3); d = ImageDraw.Draw(c)
    head(d, W, 230, 'Key benefits', u)
    place_soap(c, '4751045862134', 1080, 3250, 1650, angle=5)
    items = [('wave', 'Soothing daily cleanse'), ('soft', 'Comfort for sensitive-feeling skin'), ('drop', 'Soft, never tight'), ('all', 'Suits all skin types')]
    d = ImageDraw.Draw(c)
    for i, (k, t) in enumerate(items):
        cy = 1050 + i * 640
        d.ellipse([2090, cy - 150, 2390, cy + 150], outline=GREEN, width=8)
        icon(d, k, 2240, cy, 78, 9)
        f = F(SANS, 78)
        wrap = []
        words = t.split(); cur = ''
        for wd in words:
            if f.getlength((cur + ' ' + wd).strip()) > 1380: wrap.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        wrap.append(cur)
        lines(d, 2500, cy - len(wrap) * 50, wrap, f, 100)
        if i < 3: rule(d, 2090, cy + 320, 1650, 4)
    save(c, '03_Key_benefits.jpg', (W, W))

    # 4 How to use
    c = stone(W, W, .30, seed=4); d = ImageDraw.Draw(c)
    head(d, W, 230, 'How to use', u)
    steps = [('drop', 'Wet hands and the soap bar'), ('foam', 'Lather and massage gently over face or body'), ('rinse', 'Rinse well; let the bar dry between uses')]
    for i, (k, t) in enumerate(steps):
        x0 = 230 + i * 1180; y0 = 700
        card = Image.new('RGBA', (1060, 1500), (250, 246, 238, 175))
        m = Image.new('L', card.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 1059, 1499], 36, fill=255); card.putalpha(ImageChops.multiply(card.split()[3], m))
        c.alpha_composite(card, (x0, y0)); d = ImageDraw.Draw(c)
        d.text((x0 + 530, y0 + 130), str(i + 1), font=F(SERIF_I, 190), fill=GREEN, anchor='ma')
        icon(d, k, x0 + 530, y0 + 720, 190, 11)
        f = F(SANS, 66); words = t.split(); cur = ''; wrap = []
        for wd in words:
            if f.getlength((cur + ' ' + wd).strip()) > 880: wrap.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        wrap.append(cur)
        for j, ln in enumerate(wrap): d.text((x0 + 530, y0 + 1060 + j * 88), ln, font=f, fill=GREEN, anchor='ma')
    place_soap(c, '4751045862134', 3180, 3900, 1100, angle=-4)
    save(c, '04_How_to_use.jpg', (W, W))

    # 5 What's inside
    c = stone(W, W, .26, seed=5); d = ImageDraw.Draw(c)
    head(d, W, 200, "What's inside", u)
    sp = place_soap(c, '4751045862134', 2000, 2500, 1500)
    d = ImageDraw.Draw(c)
    specs = [(700, 1250, 'Frankincense (Boswellia serrata) extract', 'soothing aroma & care', 'resin'),
             (3300, 1250, 'Shea butter', 'softening', 'shea'),
             (2000, 3150, 'Coconut oil', 'mild cleansing', 'coco')]
    for cx, cy, t1, t2, kind in specs:
        R = 330
        circ = macro(kind, R * 2)
        sh = Image.new('RGBA', circ.size, (0, 0, 0, 0)); sh.putalpha(circ.split()[3]); shadow(c, circ, (cx - R, cy - R), 18, 22, 26, .25)
        c.alpha_composite(circ, (cx - R, cy - R)); d = ImageDraw.Draw(c)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=GREEN, width=6)
    # leader lines + labels
    d.line([(1030, 1500), (1450, 1900)], fill=GREEN, width=5)
    d.line([(2970, 1500), (2560, 1900)], fill=GREEN, width=5)
    d.line([(2000, 2830), (2000, 2560)], fill=GREEN, width=5)
    for cx, cy, t1, t2, kind in specs:
        yb = cy + 410
        f1 = F(SANS, 62); 
        words = t1.split(); cur = ''; wrap = []
        for wd in words:
            if f1.getlength((cur + ' ' + wd).strip()) > 900: wrap.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        wrap.append(cur)
        if kind == 'coco':
            yb = cy + 400
        for j, ln in enumerate(wrap): d.text((cx, yb + j * 76), ln, font=f1, fill=GREEN, anchor='ma')
        d.text((cx, yb + len(wrap) * 76 + 14), '- ' + t2 if False else t2, font=F(SERIF_I, 62), fill=GREEN, anchor='ma')
    save(c, '05_Whats_inside.jpg', (W, W))

    # 6 Size & volume
    c = stone(W, W, .24, seed=6); d = ImageDraw.Draw(c)
    head(d, W, 190, 'Size & volume', u)
    d.text((W / 2, 560), '8 x 5 x 2.5 cm / 100 g', font=F(SERIF_I, 110), fill=GREEN, anchor='ma')
    sp = place_soap(c, '4751045862134', 2000, 2020, 1500)
    d = ImageDraw.Draw(c)
    x0, y0, sw, sh_ = sp
    ay = y0 + sh_ + 120
    d.line([(x0, ay), (x0 + sw, ay)], fill=GREEN, width=7); 
    for xx in (x0, x0 + sw): d.line([(xx, ay - 30), (xx, ay + 30)], fill=GREEN, width=7)
    d.text((x0 + sw / 2, ay + 40), '8 cm', font=F(SANS, 70), fill=GREEN, anchor='ma')
    ax = x0 + sw + 130
    d.line([(ax, y0), (ax, y0 + sh_)], fill=GREEN, width=7)
    for yy in (y0, y0 + sh_): d.line([(ax - 30, yy), (ax + 30, yy)], fill=GREEN, width=7)
    d.text((ax + 50, y0 + sh_ / 2), '5 cm', font=F(SANS, 70), fill=GREEN, anchor='lm')
    d.text((W / 2, ay + 160), 'Size: 8 x 5 x 2.5 cm / 100 g   |   Volume: 100 g', font=F(SANS, 66), fill=GREEN, anchor='ma')
    d.text((W / 2, 2790), 'Complete your routine', font=F(SERIF_I, 96), fill=GREEN, anchor='ma')
    rule(d, 300, 2750, 3400, 4)
    names = [('4751045862141', 'Milk & Honey Soap Bar'), ('4751045862103', 'Goat Milk Soap Bar'), ('4751045863797', 'Turmeric Soap Bar')]
    for i, (g, n) in enumerate(names):
        cx = 700 + i * 1300
        place_soap(c, g, cx, 3560, 900)
        d = ImageDraw.Draw(c); d.text((cx, 3680), n, font=F(SANS, 60), fill=GREEN, anchor='ma')
    save(c, '06_Size_volume.jpg', (W, W))

    # 7 Lifestyle
    c = stone(W, W, .50, tone=.03, seed=8)
    place_soap(c, '4751045862134', 2750, 3350, 1750, angle=-6)
    d = ImageDraw.Draw(c)
    fs = fit('Frankincense soap', SERIF, 2200, 230)
    d.text((300, 330), 'Frankincense soap', font=F(SERIF, fs), fill=GREEN)
    d.text((300, 330 + fs * 1.15), 'for calm, soft skin', font=F(SERIF_I, fs), fill=GREEN)
    save(c, '07_Lifestyle.jpg', (W, W))

def macro(kind, S):
    r = np.random.default_rng(3)
    if kind == 'resin':
        base = Image.new('RGBA', (S, S), (214, 160, 78, 255))
        for i in range(10):
            p = resin_piece(int(S * (.14 + .06 * r.random())), 300 + i).rotate(float(r.random() * 360), expand=True)
            base.alpha_composite(p, (int(r.random() * S * .8), int(r.random() * S * .8)))
        img = base.filter(ImageFilter.GaussianBlur(1))
    elif kind == 'shea':
        a = 232 - noise(S, S, S // 8, 11) * 18 - noise(S, S, 3, 12) * 12
        img = Image.fromarray(np.stack([a, a - 6, a - 28], -1).astype('uint8')).convert('RGBA')
    else:
        a = 244 - noise(S, S, S // 10, 21) * 22 - noise(S, S, 2, 22) * 16
        img = Image.fromarray(np.stack([a, a - 3, a - 14], -1).astype('uint8')).convert('RGBA')
    m = Image.new('L', (S, S), 0); ImageDraw.Draw(m).ellipse([0, 0, S - 1, S - 1], fill=255)
    img.putalpha(m); return img

# ---------- A+ ----------
def aplus_basic():
    for name, (W, H) in [('A_Basic_1_header', (970, 600))]:
        k = 3; w, h = W * k, H * k; u = w / 1000
        c = stone(w, h, .42, seed=21)
        place_soap(c, '4751045862134', int(w * .80), int(h * .90), int(w * .30), angle=5)
        d = ImageDraw.Draw(c)
        d.text((w * .06, h * .20), 'Frankincense soap', font=F(SERIF, w * .062), fill=GREEN)
        d.text((w * .06, h * .20 + w * .075), 'for calm, soft skin', font=F(SERIF_I, w * .062), fill=GREEN)
        rule(d, w * .06, h * .52, w * .12, 3)
        lines(d, w * .06, h * .56, ['Soothing daily cleanse.', 'Comfort for sensitive-feeling skin.'], F(SANS, w * .022), w * .032)
        text(d, (w * .06, h * .09), 'ZAptieka', F(SANS_L, w * .020), track=6)
        save(c, f'{name}_970x600.jpg', (W, H))
    # B2
    W, H = 970, 600; k = 3; w, h = W * k, H * k
    c = stone(w, h, .30, seed=22); d = ImageDraw.Draw(c)
    d.text((w * .64, h * .12), 'Key benefits', font=F(SERIF, w * .045), fill=GREEN, anchor='ma')
    place_soap(c, '4751045862134', int(w * .20), int(h * .80), int(w * .30), angle=4)
    d = ImageDraw.Draw(c)
    cols = [('wave', 'Soothing daily cleanse'), ('soft', 'Comfort for sensitive-feeling skin'), ('drop', 'Soft, never tight')]
    for i, (kd, t) in enumerate(cols):
        cx = w * (.45 + i * .205)
        icon(d, kd, cx, h * .38, w * .028, 5)
        f = F(SANS, w * .0215); words = t.split(); cur = ''; wrap = []
        for wd in words:
            if f.getlength((cur + ' ' + wd).strip()) > w * .17: wrap.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        wrap.append(cur)
        for j, ln in enumerate(wrap): d.text((cx, h * .55 + j * w * .029), ln, font=f, fill=GREEN, anchor='ma')
        if i: d.line([(cx - w * .102, h * .30), (cx - w * .102, h * .75)], fill=GREEN, width=2)
    save(c, 'A_Basic_2_benefits_970x600.jpg', (W, H))
    # B3
    c = stone(w, h, .30, seed=23); d = ImageDraw.Draw(c)
    d.text((w * .64, h * .08), "What's inside", font=F(SERIF, w * .045), fill=GREEN, anchor='ma')
    place_soap(c, '4751045862134', int(w * .20), int(h * .80), int(w * .30), angle=4)
    d = ImageDraw.Draw(c)
    rows = [('resin', 'Frankincense (Boswellia serrata) extract', 'soothing aroma & care'), ('shea', 'Shea butter', 'softening'), ('coco', 'Coconut oil', 'mild cleansing')]
    for i, (kd, a_, b_) in enumerate(rows):
        cy = h * (.30 + i * .25); R = int(h * .095)
        m = macro(kd, R * 2); c.alpha_composite(m, (int(w * .42), int(cy - R))); d = ImageDraw.Draw(c)
        d.ellipse([w * .42, cy - R, w * .42 + 2 * R, cy + R], outline=GREEN, width=3)
        d.text((w * .42 + 2 * R + w * .03, cy - w * .018), a_, font=F(SANS, w * .0235), fill=GREEN, anchor='lm')
        d.text((w * .42 + 2 * R + w * .03, cy + w * .02), b_, font=F(SERIF_I, w * .0255), fill=GREEN, anchor='lm')
    save(c, 'A_Basic_3_ingredients_970x600.jpg', (W, H))

def aplus_premium():
    W, H = 1464, 600; k = 2.5; w, h = int(W * k), int(H * k)
    # P1
    c = stone(w, h, .46, tone=.02, seed=31)
    place_soap(c, '4751045862134', int(w * .84), int(h * .88), int(w * .21), angle=-5)
    d = ImageDraw.Draw(c)
    fs = fit('Frankincense soap', SERIF, w * .30, w * .06)
    d.text((w * .06, h * .26), 'Frankincense soap', font=F(SERIF, fs), fill=GREEN)
    d.text((w * .06, h * .26 + fs * 1.2), 'for calm, soft skin', font=F(SERIF_I, fs), fill=GREEN)
    save(c, 'A_Premium_1_hero_1464x600.jpg', (W, H))
    # P2 macro resin story
    c = stone(w, h, .40, tone=.12, seed=32)
    tint = Image.new('RGBA', (w, h), (214, 150, 60, 60)); c.alpha_composite(tint)
    items = [(w * .52, h * .30, h * .30, 20), (w * .62, h * .66, h * .22, 80), (w * .70, h * .28, h * .18, 140), (w * .46, h * .76, h * .16, 10),
             (w * .58, h * .46, h * .12, 50), (w * .67, h * .85, h * .13, 100)]
    place_resin(c, items, w)
    place_soap(c, '4751045862134', int(w * .865), int(h * .86), int(w * .20), angle=4)
    d = ImageDraw.Draw(c)
    d.text((w * .05, h * .13), 'Powered by Frankincense', font=F(SERIF, w * .030), fill=GREEN)
    d.text((w * .05, h * .13 + w * .037), '(Boswellia serrata) extract', font=F(SERIF_I, w * .030), fill=GREEN)
    rule(d, w * .05, h * .40, w * .10, 3)
    lines(d, w * .05, h * .46, ['Frankincense (Boswellia serrata) extract', '- soothing aroma & care', 'Shea butter - softening', 'Coconut oil - mild cleansing'], F(SANS, w * .0145), w * .023)
    save(c, 'A_Premium_2_ingredient_story_1464x600.jpg', (W, H))
    # P3 ritual
    c = stone(w, h, .22, seed=33); d = ImageDraw.Draw(c)
    d.text((w / 2, h * .07), 'How to use', font=F(SERIF, w * .036), fill=GREEN, anchor='ma')
    steps = [('drop', 'Wet hands and the soap bar'), ('foam', 'Lather and massage gently over face or body'), ('rinse', 'Rinse well; let the bar dry between uses'), ('soft', 'Enjoy: Comfort for sensitive-feeling skin')]
    cw = w * .21
    for i, (kd, t) in enumerate(steps):
        x0 = w * .055 + i * (cw + w * .035)
        card = Image.new('RGBA', (int(cw), int(h * .72)), (250, 246, 238, 180))
        m = Image.new('L', card.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, card.width - 1, card.height - 1], int(w * .008), fill=255)
        card.putalpha(ImageChops.multiply(card.split()[3], m)); c.alpha_composite(card, (int(x0), int(h * .22))); d = ImageDraw.Draw(c)
        cx = x0 + cw / 2
        d.text((cx, h * .25), str(i + 1), font=F(SERIF_I, w * .035), fill=GREEN, anchor='ma')
        icon(d, kd, cx, h * .53, w * .028, 5)
        f = F(SANS, w * .0145); words = t.split(); cur = ''; wrap = []
        for wd in words:
            if f.getlength((cur + ' ' + wd).strip()) > cw * .82: wrap.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        wrap.append(cur)
        for j, ln in enumerate(wrap): d.text((cx, h * .70 + j * w * .0205), ln, font=f, fill=GREEN, anchor='ma')
    save(c, 'A_Premium_3_ritual_1464x600.jpg', (W, H))

if __name__ == '__main__':
    which = sys.argv[1:] or ['c', 'b', 'p']
    if 'c' in which: carousel()
    if 'b' in which: aplus_basic()
    if 'p' in which: aplus_premium()
