"""Render one Fresh Nook video pin (1080x1620 MP4, about 11 s) from a JSON spec.

Same spec as render.py (Snug Nook), drawn in the Fresh Nook style:
calm warm white, sage green, Fraunces headlines, the brand arch.

Spec:
{
  "id": 123,
  "kicker": "tuesday bathroom day",
  "title": "Clean the Bathroom in 20 Minutes",
  "sub": "Gentle on finishes.",             # optional
  "hero": "https://.../photo.jpg",
  "slides": [{"image": "https://...", "label": "Spray, wait, then wipe"}, ...],   # 2 to 4
  "cta_kicker": "the full routine",
  "cta_title": "A 20-Minute Bathroom Reset",
  "domain": "thefreshnook.com"
}
"""
import io, json, os, subprocess, sys, tempfile, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1620, 30

INK = (36, 51, 44)
CREAM = (250, 248, 244)
SAGE = (126, 156, 136)
DEEP = (79, 110, 90)
SOFT = (230, 237, 230)
MIST = (201, 216, 204)
MUTED = (95, 107, 100)
LINE = (227, 224, 216)
T_HERO, T_SLIDE, T_END, XF = 3.0, 2.0, 2.8, 0.4

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts') + '/'


def ffmpeg_exe():
    import shutil
    exe = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def font(name, size):
    return ImageFont.truetype(FONTS + name + '.ttf', int(size))


def serif(size):
    return font('Fraunces-SemiBold', size)


def italic(size):
    return font('Fraunces-MediumItalic', size)


def sans(size):
    return font('Inter-SemiBold', size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'freshnook-video/1.0'})
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
        lines = wrap(d, text, serif(size), maxw)
        if len(lines) <= max_lines:
            return size, lines
        size -= 4
    return stop, wrap(d, text, serif(stop), maxw)[:max_lines]


def arch_mask(w, h, r_bottom=28):
    """Arch: half-circle top, straight sides, softly rounded bottom corners (drawn 2x for smooth edges)."""
    m = Image.new('L', (w * 2, h * 2), 0)
    d = ImageDraw.Draw(m)
    r = w
    d.ellipse([0, 0, w * 2 - 1, w * 2 - 1], fill=255)
    d.rounded_rectangle([0, r, w * 2 - 1, h * 2 - 1], r_bottom * 2, fill=255)
    d.rectangle([0, r, w * 2 - 1, h * 2 - 1 - r_bottom * 2], fill=255)
    return m.resize((w, h), Image.LANCZOS)


def sparkle(d, cx, cy, r, fill):
    q = r * 0.22
    d.polygon([(cx, cy - r), (cx + q, cy - q), (cx + r, cy), (cx + q, cy + q),
               (cx, cy + r), (cx - q, cy + q), (cx - r, cy), (cx - q, cy - q)], fill=fill)


def mark(d, x, y, size, stroke, star):
    """The Fresh Nook mark: a thin arch on a base line with a sparkle inside."""
    k = size / 40
    w = max(2, int(2.6 * k))
    d.line([(x + 8 * k, y + 36 * k), (x + 8 * k, y + 18 * k)], fill=stroke, width=w)
    d.line([(x + 32 * k, y + 36 * k), (x + 32 * k, y + 18 * k)], fill=stroke, width=w)
    d.arc([x + 8 * k, y + 6 * k, x + 32 * k, y + 30 * k], 180, 360, fill=stroke, width=w)
    d.line([(x + 5 * k, y + 36 * k), (x + 35 * k, y + 36 * k)], fill=stroke, width=w)
    sparkle(d, x + 20 * k, y + 24 * k, 7.5 * k, star)


def centered(d, y, text, f, fill):
    d.text((W / 2 - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def with_alpha(col, a):
    return col + (int(255 * max(0.0, min(1.0, a))),)


class Video:
    def __init__(self, spec):
        self.s = spec
        self.hero = fetch(spec['hero'])
        self.slides = [(fetch(x['image']), x['label']) for x in spec['slides'][:4]]
        probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        self.hero_size, self.hero_lines = fit(probe, spec['title'], W - 170, 3, 104, 66)
        self.cta_size, self.cta_lines = fit(probe, spec.get('cta_title') or spec['title'], W - 300, 3, 92, 60)
        self.aw, self.ah = 800, 850
        self.amask = arch_mask(self.aw, self.ah)
        # soft shadow under the hero arch
        sh = Image.new('L', (self.aw + 120, self.ah + 120), 0)
        sh.paste(self.amask, (60, 70))
        self.ashadow = sh.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.22))

    def total(self):
        return T_HERO + T_SLIDE * len(self.slides) + T_END

    def hero_frame(self, t):
        s = self.s
        img = Image.new('RGB', (W, H), CREAM)
        d = ImageDraw.Draw(img, 'RGBA')
        d.rectangle([28, 28, W - 29, H - 29], outline=LINE, width=2)
        ax, ay = (W - self.aw) // 2, 90
        img.paste(Image.new('RGB', self.ashadow.size, INK), (ax - 60, ay - 60), self.ashadow)
        photo = cover(self.hero, self.aw, self.ah, 1.0 + 0.07 * t / T_HERO, 0.5, 0.45)
        img.paste(photo, (ax, ay), self.amask)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease((t - 0.3) / 0.7)
        rise = int(26 * (1 - p))
        y = ay + self.ah + 46 + rise
        if s.get('kicker'):
            centered(d, y, s['kicker'], italic(54), with_alpha(DEEP, p))
            y += 84
        lh = int(self.hero_size * 1.02)
        for line in self.hero_lines:
            centered(d, y, line, serif(self.hero_size), with_alpha(INK, p))
            y += lh
        q = ease((t - 1.1) / 0.6)
        if s.get('sub') and q > 0 and y + 60 < H - 60:
            centered(d, y + 18, s['sub'], sans(36), with_alpha(MUTED, q))
        return img

    def slide_frame(self, i, t):
        photo, label = self.slides[i]
        img = cover(photo, W, H, 1.1 - 0.07 * t / T_SLIDE, 0.5, 0.42 + 0.12 * t / T_SLIDE)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease((t - 0.15) / 0.5)
        if p <= 0:
            return img
        f = serif(66)
        lines = wrap(d, label, f, W - 360)[:2]
        ch = 120 + 76 * len(lines)
        top = int(H - 70 - ch + 60 * (1 - p))
        d.rounded_rectangle([56, top, W - 56, top + ch], 44, fill=with_alpha(CREAM, 0.96 * p))
        cx, cy = 160, top + ch / 2
        d.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=with_alpha(DEEP, p))
        num = '%02d' % (i + 1)
        fn = italic(54)
        d.text((cx - d.textlength(num, font=fn) / 2, cy - 36), num, font=fn, fill=with_alpha(CREAM, p))
        yy = cy - 38 * len(lines) - 4
        for ln in lines:
            d.text((250, yy), ln, font=f, fill=with_alpha(INK, p))
            yy += 76
        return img

    def end_frame(self, t):
        s = self.s
        img = Image.new('RGB', (W, H), CREAM)
        d = ImageDraw.Draw(img, 'RGBA')
        d.rectangle([28, 28, W - 29, H - 29], outline=LINE, width=2)
        p = ease(t / 0.6)
        lh = int(self.cta_size * 1.02)
        body = 240 + 100 + lh * len(self.cta_lines) + 230
        aw = 900
        ah = max(1300, body + 300)
        ax, ay = (W - aw) // 2, 120
        img.paste(Image.new('RGB', (aw, ah), DEEP), (ax, ay), arch_mask(aw, ah, 40))
        d = ImageDraw.Draw(img, 'RGBA')
        y0 = ay + 150 + max(0, (ah - 150 - body) // 2 - 60)
        mark(d, W / 2 - 80, y0 - 24 * (1 - p), 160, CREAM, MIST)
        y = y0 + 220
        centered(d, y, s.get('cta_kicker') or 'read the guide', italic(62), MIST)
        y += 104
        for line in self.cta_lines:
            centered(d, y, line, serif(self.cta_size), CREAM)
            y += lh
        q = ease((t - 0.6) / 0.5)
        bw, bh = 560, 112
        bx, by = W / 2 - bw / 2, y + 70 + 26 * (1 - q)
        d.rounded_rectangle([bx, by, bx + bw, by + bh], 56, fill=with_alpha(CREAM, q))
        ft = sans(42)
        txt = 'Read the guide'
        tw = d.textlength(txt, font=ft)
        tx = W / 2 - (tw + 58) / 2
        col = with_alpha(INK, q)
        d.text((tx, by + 30), txt, font=ft, fill=col)
        axx, ayy = tx + tw + 22, by + bh / 2 + 2
        d.line([(axx, ayy), (axx + 34, ayy)], fill=col, width=5)
        d.line([(axx + 21, ayy - 13), (axx + 35, ayy), (axx + 21, ayy + 13)], fill=col, width=5, joint='curve')
        dom = s.get('domain', 'thefreshnook.com')
        fs = sans(38)
        yd = H - 130
        tw2 = d.textlength(dom, font=fs)
        sparkle(d, W / 2 - tw2 / 2 - 34, yd + 22, 14, SAGE)
        d.text((W / 2 - tw2 / 2, yd), dom, font=fs, fill=INK)
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
            subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.jpg'),
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'slow', '-movflags', '+faststart', out_path], check=True)


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    Video(spec).write(sys.argv[2])
    print('wrote', sys.argv[2])
