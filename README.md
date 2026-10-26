# slidemage-website

The SlideMage website, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and
served by GitHub Pages. Every push to `main` deploys it (`.github/workflows/deploy.yml`).

Preview locally:

```bash
pip install -r requirements.txt
mkdocs serve
```

Content is in `docs/`. The paths `/plugins/` and `/plugins/<id>/` are opened by the SlideMage app; keep them
stable.

Content is licensed under CC BY-SA 4.0 (`LICENSE`).
