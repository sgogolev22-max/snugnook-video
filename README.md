# Nook video pins

Renders short video pins (1080×1620 MP4) for [thesnugnook.com](https://thesnugnook.com) and [thefreshnook.com](https://thefreshnook.com).

- Every 4 hours GitHub Actions reads each site's public queue
  (`/wp-json/snugnook/v1/video-queue`, `/wp-json/freshnook/v1/video-queue`), renders new videos
  (`render.py` for Snug Nook, `render_fresh.py` for Fresh Nook) and attaches them to the
  **videos** and **fresh-videos** releases.
- Each site then downloads its finished files into its own uploads folder.
- A second workflow checks both home pages every 30 minutes and emails the owner if one is down.
- Fonts: Bricolage Grotesque, Figtree, Caveat, Fraunces, Inter (SIL Open Font License, see `fonts/`).
