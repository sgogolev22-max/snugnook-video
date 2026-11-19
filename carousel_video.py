"""Carousel video pins (1080x1620 MP4): a row of finished slides, each a full 2:3 picture
(cover, one slide per tip, end slide), shown one after another with a slow zoom and a soft cross-fade.
The slides are drawn by the sites' infographic robot in the same style as the infographic pins.

Spec:
{
  "frames": ["https://.../slide-1.jpg", "https://.../slide-2.jpg", ...],   # 3 to 12, cover first, end slide last
  "seconds": 3.0          # optional, time per slide (2.0 to 5.0)
}
"""
import io, os, subprocess, tempfile, urllib.request
from PIL import Image

W, H, FPS = 1080, 1620, 30
XF = 0.4


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class CarouselVideo:
    ua = 'nook-video/3.0'

    def __init__(self, spec):
        urls = [u for u in (spec.get('frames') or []) if u][:12]
        if len(urls) < 2:
            raise ValueError('a carousel needs at least 2 frames')
        self.sec = max(2.0, min(5.0, float(spec.get('seconds') or 3.0)))
        self.frames = [self.fit(self.fetch(u)) for u in urls]

    def fetch(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': self.ua})
        with urllib.request.urlopen(req, timeout=60) as r:
            return Image.open(io.BytesIO(r.read())).convert('RGB')

    @staticmethod
    def fit(img):
        # Cover 1080x1620 with a 6% margin so the slow zoom never shows an edge.
        s = max(W / img.width, H / img.height) * 1.06
        return img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)

    def shot(self, i, t):
        # Slow zoom from 100% to 106% of the slide, centred: the visible window shrinks from the full
        # 1080x1620 cover area (img / 1.06) to img / 1.06 / 1.06.
        img = self.frames[i]
        z = 1.0 + 0.06 * ease(t / self.sec)
        cw, ch = img.width / 1.06 / z * 1.0, img.height / 1.06 / z
        x, y = (img.width - cw) / 2, (img.height - ch) / 2
        return img.crop((int(x), int(y), int(x + cw), int(y + ch))).resize((W, H), Image.BILINEAR)

    def total(self):
        return self.sec * len(self.frames)

    def frame(self, t):
        i = min(int(t // self.sec), len(self.frames) - 1)
        lt = t - i * self.sec
        cur = self.shot(i, lt)
        if i + 1 < len(self.frames) and lt > self.sec - XF:
            return Image.blend(cur, self.shot(i + 1, 0), ease((lt - (self.sec - XF)) / XF))
        return cur

    def write(self, out_path):
        from bold_video import ffmpeg_exe
        with tempfile.TemporaryDirectory() as tmp:
            n = int(self.total() * FPS)
            for k in range(n):
                self.frame(k / FPS).save(os.path.join(tmp, 'f%04d.jpg' % k), quality=92)
            subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.jpg'),
                            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                            '-shortest', '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0', '-pix_fmt', 'yuv420p',
                            '-crf', '21', '-preset', 'slow', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', out_path], check=True)
