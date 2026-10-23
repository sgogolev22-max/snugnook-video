"""Render every pending video from the site's public queue that is not rendered yet.

The queue holds only public information (titles and photo URLs already on thesnugnook.com).
Finished files go to ./out/video-<id>.mp4; done.json remembers what was rendered.
"""
import json, os, sys, traceback, urllib.request
from render import Video

QUEUE = os.environ.get('QUEUE_URL', 'https://thesnugnook.com/wp-json/snugnook/v1/video-queue')
done_path = 'done.json'
done = json.load(open(done_path)) if os.path.exists(done_path) else []
req = urllib.request.Request(QUEUE, headers={'User-Agent': 'snugnook-video/1.0'})
items = json.load(urllib.request.urlopen(req, timeout=60))
os.makedirs('out', exist_ok=True)
made = 0
for item in items:
    vid = int(item['id'])
    if vid in done:
        continue
    try:
        Video(item['spec']).write('out/video-%d.mp4' % vid)
        done.append(vid)
        made += 1
        print('rendered', vid)
    except Exception:
        traceback.print_exc()
json.dump(sorted(done), open(done_path, 'w'))
print('new videos:', made)
