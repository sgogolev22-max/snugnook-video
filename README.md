# Snug Nook video pins

Renders short video pins (1080×1620 MP4) for [thesnugnook.com](https://thesnugnook.com).

- Every 4 hours GitHub Actions reads the site's public queue (`/wp-json/snugnook/v1/video-queue`),
  renders new videos with `render.py` and attaches them to the **videos** release.
- The site then downloads each finished file into its own uploads folder.
- Fonts: Bricolage Grotesque, Figtree, Caveat (SIL Open Font License, see `fonts/`).
