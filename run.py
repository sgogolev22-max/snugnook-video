"""Render every pending video from each site's public queue that is not rendered yet.

The queues hold only public information (titles and photo URLs already on the sites).
Snug Nook  -> render.py,       files in ./out/video-<id>.mp4,       progress in done.json       (release "videos")
Fresh Nook -> render_fresh.py, files in ./out-fresh/video-<id>.mp4, progress in done-fresh.json (release "fresh-videos")
"""
import importlib, json, os, traceback, urllib.request

SITES = [
    {'name': 'snugnook', 'queue': os.environ.get('QUEUE_URL', 'https://thesnugnook.com/wp-json/snugnook/v1/video-queue'),
     'module': 'render', 'done': 'done.json', 'out': 'out'},
    {'name': 'freshnook', 'queue': os.environ.get('FRESH_QUEUE_URL', 'https://thefreshnook.com/wp-json/freshnook/v1/video-queue'),
     'module': 'render_fresh', 'done': 'done-fresh.json', 'out': 'out-fresh'},
]

total = 0
for site in SITES:
    done = json.load(open(site['done'])) if os.path.exists(site['done']) else []
    try:
        req = urllib.request.Request(site['queue'], headers={'User-Agent': site['name'] + '-video/1.0'})
        items = json.load(urllib.request.urlopen(req, timeout=60))
    except Exception:
        traceback.print_exc()
        continue
    Video = importlib.import_module(site['module']).Video
    os.makedirs(site['out'], exist_ok=True)
    made = 0
    for item in items:
        vid = int(item['id'])
        if vid in done:
            continue
        try:
            Video(item['spec']).write(os.path.join(site['out'], 'video-%d.mp4' % vid))
            done.append(vid)
            made += 1
            print(site['name'], 'rendered', vid)
        except Exception:
            traceback.print_exc()
    json.dump(sorted(done), open(site['done'], 'w'))
    print(site['name'], 'new videos:', made)
    total += made
print('new videos in total:', total)
