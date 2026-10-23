"""Render one Snug Nook video pin (1080x1620 MP4, ~11 s) from a JSON spec.

Spec:
{
  "id": 123,
  "kicker": "small pantry fix",          # small script line above the headline
  "title": "9 Small Pantry Ideas That Fit",
  "sub": "No drilling. Renter-friendly.",  # optional
  "hero": "https://.../photo.jpg",
  "slides": [{"image": "https://...", "label": "Sort food into zones"}, ...],   # 2 to 4
  "cta_kicker": "get all 9 ideas",
  "cta_title": "Small Pantry Ideas That Fit",
  "domain": "thesnugnook.com"
}
Each slide label is the same headline that was approved for that photo on a still pin,
so the words always describe what the photo shows.
"""
import io, json, os, subprocess, sys, tempfile, urllib.request
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1620, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts') + '/'
PINE, CREAM, GOLD, CORAL, ARCH = (30, 58, 52), (251, 248, 242), (246, 199, 68), (228, 87, 46), (51, 82, 74)
T_HERO, T_SLIDE, T_END, XF = 2.8, 1.9, 2.6, 0.35


def font(name, size):
    return ImageFont.truetype(FONTS + name + '.ttf', size)


def big(size):
    return font('BricolageGrotesque-ExtraBold', size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'snugnook-video/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert('RGB')


def cover(img, w, h, zoom=1.0, fx=0.5, fy=0.5):
    s = max(w / img.width, h / img.height) * zoom
    nw, nh = int(img.width * s) + 1, int(img.height * s) + 1
    im = img.resize((nw, nh), Image.LANCZOS)
    x, y = int((nw - w) * fx), int((nh - h) * fy)
    return im.crop((x, y, x + w, y + h))


def wrap(d, text, f, maxw):
    lines, cur = [], ''
    for word in text.split():
        t = (cur + ' ' + word).strip()
        if cur and d.textlength(t, font=f) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, maxw, max_lines, start, stop):
    """Largest headline size at which the text fits in max_lines."""
    size = start
    while size > stop:
        lines = wrap(d, text, big(size), maxw)
        if len(lines) <= max_lines:
            return size, lines
        size -= 4
    return stop, wrap(d, text, big(stop), maxw)[:max_lines]


def mark(d, x, y, size, stroke, eye):
    k = size / 40
    w = max(2, int(3.4 * k))
    d.line([(x + 7 * k, y + 35 * k), (x + 7 * k, y + 18 * k)], fill=stroke, width=w)
    d.line([(x + 33 * k, y + 35 * k), (x + 33 * k, y + 18 * k)], fill=stroke, width=w)
    d.arc([x + 7 * k, y + 5 * k, x + 33 * k, y + 31 * k], 180, 360, fill=stroke, width=w)
    d.line([(x + 13 * k, y + 27 * k), (x + 27 * k, y + 27 * k)], fill=stroke, width=w)
    r = 2.7 * k
    d.ellipse([x + 17 * k - r, y + 21.5 * k - r, x + 17 * k + r, y + 21.5 * k + r], fill=eye)
    d.ellipse([x + 23.5 * k - r, y + 21.5 * k - r, x + 23.5 * k + r, y + 21.5 * k + r], fill=CORAL)


class Video:
    def __init__(self, spec):
        self.s = spec
        self.hero = fetch(spec['hero'])
        self.slides = [(fetch(x['image']), x['label']) for x in spec['slides'][:4]]
        shade = Image.new('L', (1, 520))
        for y in range(520):
            shade.putpixel((0, y), int(200 * (y / 520) ** 1.6))
        self.shade = shade.resize((W, 520))
        probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        self.hero_size, self.hero_lines = fit(probe, spec['title'], W - 180, 3, 118, 76)
        self.cta_size, self.cta_lines = fit(probe, spec.get('cta_title') or spec['title'], W - 200, 3, 110, 70)

    def total(self):
        return T_HERO + T_SLIDE * len(self.slides) + T_END

    def hero_frame(self, t):
        s = self.s
        img = cover(self.hero, W, H, 1.0 + 0.08 * t / T_HERO, 0.5, 0.45)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease((t - 0.25) / 0.6)
        lh = int(self.hero_size * 0.95)
        panel = 50 + 85 + lh * len(self.hero_lines) + (100 if s.get('sub') else 40)
        top = int(H - panel * p)
        if p <= 0:
            return img
        d.rounded_rectangle([40, top, W - 40, H + 40], 46, fill=CREAM)
        d.text((90, top + 50), s.get('kicker', ''), font=font('Caveat-Bold', 66), fill=CORAL)
        y = top + 135
        for line in self.hero_lines:
            d.text((88, y), line, font=big(self.hero_size), fill=PINE)
            y += lh
        q = ease((t - 1.2) / 0.5)
        if s.get('sub') and q > 0:
            d.text((90, y + 26), s['sub'], font=font('Figtree-Bold', 40), fill=PINE + (int(255 * q),))
        return img

    def slide_frame(self, i, t):
        photo, label = self.slides[i]
        img = cover(photo, W, H, 1.12 - 0.08 * t / T_SLIDE, 0.5, 0.4 + 0.15 * t / T_SLIDE)
        img.paste(Image.new('RGB', (W, 520), PINE), (0, H - 520), self.shade)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease((t - 0.15) / 0.45)
        if p > 0:
            a = int(255 * p)
            x0 = int(70 - 90 * (1 - p))
            cy = H - 230
            d.ellipse([x0, cy - 62, x0 + 124, cy + 62], fill=GOLD + (a,))
            num = str(i + 1)
            fn = big(70)
            d.text((x0 + 62 - d.textlength(num, font=fn) / 2, cy - 44), num, font=fn, fill=PINE + (a,))
            f = big(76)
            lines = wrap(d, label, f, W - 260)[:2]
            yy = cy - 46 * len(lines)
            for ln in lines:
                d.text((x0 + 160, yy), ln, font=f, fill=CREAM + (a,))
                yy += 84
        return img

    def end_frame(self, t):
        s = self.s
        img = Image.new('RGB', (W, H), PINE)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease(t / 0.5)
        title_bottom = 730 + int(self.cta_size * 0.98) * len(self.cta_lines)
        d.ellipse([W / 2 - 360, 170, W / 2 + 360, 890], fill=ARCH)
        d.rectangle([W / 2 - 360, 530, W / 2 + 360, max(1000, title_bottom + 50)], fill=ARCH)
        mark(d, W / 2 - 110, 300 - 30 * (1 - p), 220, GOLD, CREAM)
        y = 620
        fk = font('Caveat-Bold', 76)
        k = s.get('cta_kicker', 'read more')
        d.text((W / 2 - d.textlength(k, font=fk) / 2, y), k, font=fk, fill=GOLD)
        y += 110
        f = big(self.cta_size)
        for line in self.cta_lines:
            d.text((W / 2 - d.textlength(line, font=f) / 2, y), line, font=f, fill=CREAM)
            y += int(self.cta_size * 0.98)
        q = ease((t - 0.6) / 0.5)
        bw, bh = 640, 120
        bx, by = W / 2 - bw / 2, y + 80 + 30 * (1 - q)
        col = PINE + (int(255 * q),)
        d.rounded_rectangle([bx, by, bx + bw, by + bh], 60, fill=GOLD + (int(255 * q),))
        ft = font('Figtree-Bold', 46)
        txt = 'Read the guide'
        tw = d.textlength(txt, font=ft)
        tx = W / 2 - (tw + 60) / 2
        d.text((tx, by + 32), txt, font=ft, fill=col)
        ax, ay = tx + tw + 22, by + bh / 2 + 2
        d.line([(ax, ay), (ax + 36, ay)], fill=col, width=6)
        d.line([(ax + 22, ay - 14), (ax + 37, ay), (ax + 22, ay + 14)], fill=col, width=6, joint='curve')
        fs = font('Figtree-Bold', 40)
        dom = s.get('domain', 'thesnugnook.com')
        d.text((W / 2 - d.textlength(dom, font=fs) / 2, H - 150), dom, font=fs, fill=CREAM)
        return img

    def segments(self):
        segs = [('hero', 0, 0.0, T_HERO)]
        t = T_HERO
        for i in range(len(self.slides)):
            segs.append(('slide', i, t, t + T_SLIDE))
            t += T_SLIDE
        segs.append(('end', 0, t, t + T_END))
        return segs

    def render_seg(self, seg, lt):
        kind, i = seg[0], seg[1]
        if kind == 'hero':
            return self.hero_frame(lt)
        if kind == 'slide':
            return self.slide_frame(i, lt)
        return self.end_frame(lt)

    def frame(self, t):
        segs = self.segments()
        for k, seg in enumerate(segs):
            a, b = seg[2], seg[3]
            if a <= t < b:
                cur = self.render_seg(seg, t - a)
                if k + 1 < len(segs) and t > b - XF:
                    nxt = self.render_seg(segs[k + 1], 0)
                    return Image.blend(cur, nxt, ease((t - (b - XF)) / XF))
                return cur
        return self.render_seg(segs[-1], T_END - 0.01)

    def write(self, out_path):
        with tempfile.TemporaryDirectory() as tmp:
            n = int(self.total() * FPS)
            for i in range(n):
                self.frame(i / FPS).save(os.path.join(tmp, 'f%04d.jpg' % i), quality=92)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.jpg'),
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'slow', '-movflags', '+faststart', out_path], check=True)


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    Video(spec).write(sys.argv[2])
    print('wrote', sys.argv[2])
