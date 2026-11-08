"""Bold video pins (1080x1620 MP4, about 11 s) in the same style as the photo pins of 8 Nov 2026:
big photo, huge condensed headline, solid colour bands, one accent colour.

Spec (unchanged, the sites send the same JSON as before):
{
  "kicker": "small pantry fix",
  "title": "9 Small Pantry Ideas That Fit",
  "sub": "No drilling. Renter-friendly.",          # optional
  "hero": "https://.../photo.jpg",
  "slides": [{"image": "https://...", "label": "Sort food into zones"}, ...],   # 2 to 4
  "cta_kicker": "get all 9 ideas",
  "cta_title": "Small Pantry Ideas That Fit",
  "domain": "thesnugnook.com"
}

Scenes: hero (photo + white headline panel sliding in), one scene per slide (photo + numbered bottom panel),
end card (brand colour, big title, button, domain). Slow zoom on every photo, soft cross-fades.
"""
import io, json, os, re, subprocess, sys, tempfile, urllib.request
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1620, 30
T_HERO, T_SLIDE, T_END, XF = 3.0, 2.1, 2.8, 0.35

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts') + '/'

THEMES = {
    'fresh': {'primary': (47, 133, 119), 'accent': (212, 87, 47), 'ink': (31, 45, 42), 'light': (255, 255, 255),
              'panel': (255, 255, 255), 'yellow': (255, 211, 90), 'domain': 'thefreshnook.com', 'ua': 'freshnook-video/2.0'},
    'snug': {'primary': (95, 125, 76), 'accent': (194, 87, 46), 'ink': (47, 58, 44), 'light': (250, 245, 236),
             'panel': (250, 245, 236), 'yellow': (255, 211, 90), 'domain': 'thesnugnook.com', 'ua': 'snugnook-video/2.0'},
}


def ffmpeg_exe():
    import shutil
    exe = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


_fonts = {}


def font(name, size):
    key = (name, int(size))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONTS + name + '.ttf', int(size))
    return _fonts[key]


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def cover(img, w, h, zoom=1.0, fy=0.5):
    s = max(w / img.width, h / img.height) * zoom
    nw, nh = int(img.width * s) + 1, int(img.height * s) + 1
    im = img.resize((nw, nh), Image.BILINEAR)
    x = int((nw - w) / 2)
    y = int(max(0, min(nh - h, nh * fy - h / 2)))
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


def fit(d, text, name, maxw, max_lines, start, stop):
    size = start
    while size > stop:
        lines = wrap(d, text, font(name, size), maxw)
        if len(lines) <= max_lines and all(d.textlength(l, font=font(name, size)) <= maxw for l in lines):
            return size, lines
        size -= 4
    return stop, wrap(d, text, font(name, stop), maxw)[:max_lines]


def rgba(col, a):
    return tuple(col) + (int(255 * max(0.0, min(1.0, a))),)


class BoldVideo:
    site = 'fresh'

    def __init__(self, spec):
        self.s = spec
        self.c = THEMES[self.site]
        self.hero = self.fetch(spec['hero'])
        self.slides = [(self.fetch(x['image']), x['label']) for x in spec['slides'][:4]]
        probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        title = spec['title'].upper()
        m = re.match(r'^(\d{1,3})\s+(.*)$', title)
        self.num = m.group(1) if m else ''
        self.title_rest = m.group(2) if m else title
        self.t_size, self.t_lines = fit(probe, self.title_rest, 'Anton-Regular', W - 120, 3, 170, 84)
        self.k_size, self.k_lines = fit(probe, spec.get('kicker') or '', 'Caveat-Bold', W - 160, 1, 92, 56)
        cta = (spec.get('cta_title') or spec['title']).upper()
        self.c_size, self.c_lines = fit(probe, cta, 'Anton-Regular', W - 160, 4, 150, 80)
        self.labels = [fit(probe, lab.upper(), 'ArchivoBlack-Regular', W - 140, 3, 92, 60) for _, lab in self.slides]

    def fetch(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': THEMES[self.site]['ua']})
        with urllib.request.urlopen(req, timeout=60) as r:
            return Image.open(io.BytesIO(r.read())).convert('RGB')

    def total(self):
        return T_HERO + T_SLIDE * len(self.slides) + T_END

    def centered(self, d, y, text, f, fill):
        d.text((W / 2 - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)

    def pill(self, d, text, f, bg, fg, cy, pad=46):
        tw = d.textlength(text, font=f)
        h = int(f.size * 1.9)
        x1 = W / 2 - tw / 2 - pad
        d.rounded_rectangle([x1, cy - h / 2, W / 2 + tw / 2 + pad, cy + h / 2], h / 2, fill=bg)
        d.text((W / 2 - tw / 2, cy - f.size * 0.62), text, font=f, fill=fg)

    # ---- scenes -------------------------------------------------------
    def hero_frame(self, t):
        c = self.c
        img = cover(self.hero, W, H, 1.0 + 0.08 * t / T_HERO, 0.72)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease(t / 0.55)
        f = font('Anton-Regular', self.t_size)
        lh = int(self.t_size * 1.0)
        num_h = int(self.t_size * 1.25) if self.num else 0
        k_h = int(self.k_size * 1.15) if self.k_lines else 0
        panel_h = 56 + num_h + lh * len(self.t_lines) + (16 + k_h if k_h else 0) + 50
        top = int(-panel_h * (1 - p))
        d.rectangle([0, top, W, top + panel_h], fill=c['panel'])
        d.rectangle([0, top + panel_h, W, top + panel_h + 12], fill=c['primary'])
        y = top + 50
        if self.num:
            fn = font('Anton-Regular', int(self.t_size * 1.25))
            self.centered(d, y - int(self.t_size * 0.12), self.num, fn, c['accent'])
            y += num_h
        for i, line in enumerate(self.t_lines):
            self.centered(d, y - int(self.t_size * 0.12), line, f, c['ink'] if (self.num or i) else c['accent'])
            y += lh
        if self.k_lines:
            q = ease((t - 0.5) / 0.5)
            self.centered(d, y + 10, self.k_lines[0], font('Caveat-Bold', self.k_size), rgba(c['primary'], q))
        q2 = ease((t - 0.9) / 0.5)
        if q2 > 0:
            self.pill(d, c['domain'], font('Poppins-ExtraBold', 42), rgba(c['primary'], q2), rgba((255, 255, 255), q2), H - 110)
        return img

    def slide_frame(self, i, t):
        c = self.c
        photo, _ = self.slides[i]
        size, lines = self.labels[i]
        img = cover(photo, W, H, 1.1 - 0.08 * t / T_SLIDE, 0.25 + 0.1 * t / T_SLIDE)
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease((t - 0.1) / 0.45)
        lh = int(size * 1.08)
        panel_h = 60 + lh * len(lines) + 56
        top = int(H - panel_h + (panel_h + 20) * (1 - p))
        if top - 12 >= H:
            return img
        top = min(top, H - 1)
        d.rectangle([0, top - 12, W, top], fill=c['primary'])
        d.rectangle([0, top, W, H], fill=c['light'])
        y = top + 50
        f = font('ArchivoBlack-Regular', size)
        for k, line in enumerate(lines):
            col = c['primary'] if k == len(lines) - 1 and len(lines) > 1 else c['ink']
            self.centered(d, y - int(size * 0.08), line, f, col)
            y += lh
        q = ease((t - 0.25) / 0.4)
        if q > 0:
            fb = font('Poppins-ExtraBold', 44)
            badge = 'IDEA #%d' % (i + 1)
            self.pill(d, badge, fb, rgba(c['accent'], q), rgba((255, 255, 255), q), 120)
        return img

    def end_frame(self, t):
        c = self.c
        img = Image.new('RGB', (W, H), c['primary'])
        d = ImageDraw.Draw(img, 'RGBA')
        p = ease(t / 0.5)
        lh = int(self.c_size * 1.0)
        kick = self.s.get('cta_kicker') or 'read the guide'
        fk = font('Caveat-Bold', 96)
        block = 120 + lh * len(self.c_lines) + 80 + 130
        y = int((H - block) / 2 - 60 + 30 * (1 - p))
        self.centered(d, y, kick, fk, rgba(c['yellow'], p))
        y += 130
        f = font('Anton-Regular', self.c_size)
        for line in self.c_lines:
            self.centered(d, y - int(self.c_size * 0.12), line, f, rgba((255, 255, 255), p))
            y += lh
        q = ease((t - 0.45) / 0.45)
        fb = font('Poppins-ExtraBold', 50)
        self.pill(d, 'READ THE FULL GUIDE', fb, rgba(c['accent'], q), rgba((255, 255, 255), q), y + 110 + int(20 * (1 - q)), pad=60)
        self.centered(d, H - 150, c['domain'].upper(), font('Poppins-ExtraBold', 44), rgba(c['light'], q))
        return img

    # ---- timeline -----------------------------------------------------
    def segments(self):
        segs = [('hero', 0, 0.0, T_HERO)]
        t = T_HERO
        for i in range(len(self.slides)):
            segs.append(('slide', i, t, t + T_SLIDE))
            t += T_SLIDE
        segs.append(('end', 0, t, t + T_END))
        return segs

    def render_seg(self, seg, lt):
        if seg[0] == 'hero':
            return self.hero_frame(lt)
        if seg[0] == 'slide':
            return self.slide_frame(seg[1], lt)
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
            # H.264 Main + a silent AAC track: the most widely accepted MP4 for Pinterest uploads.
            subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.jpg'),
                            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                            '-shortest', '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0', '-pix_fmt', 'yuv420p',
                            '-crf', '21', '-preset', 'slow', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', out_path], check=True)


def make(site):
    return type('Video', (BoldVideo,), {'site': site})


if __name__ == '__main__':
    site = sys.argv[3] if len(sys.argv) > 3 else 'fresh'
    make(site)(json.load(open(sys.argv[1]))).write(sys.argv[2])
    print('wrote', sys.argv[2])
