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

## Plugin catalogue

SlideMage reads `/plugins/index.json`; `/plugins/index-test.json` adds the hidden test plugins.

- `registry/plugins.toml`: the approved plugins. Adding an entry, by a reviewed pull request, is the approval.
- `tools/build_catalogue.py`: builds both catalogues from the plugins' GitHub releases, pins every published
  asset's SHA-256 in `catalogue/pins.json` and copies the icons. Validated against
  `schema/plugins-index.schema.json`.
- `.github/workflows/build-catalogue.yml`: runs the builder hourly (and on "Run workflow"), commits and deploys
  when something changed, opens an issue when a published asset changes, and keeps the schedule alive with a
  monthly heartbeat (`catalogue/last-run.txt`). On pull requests it runs the tests and builds against the
  proposed registry without publishing.

Run it locally with `pip install -r requirements-catalogue.txt` and `python tools/build_catalogue.py --check`;
tests with `pytest tests`.

Content is licensed under CC BY-SA 4.0 (`LICENSE`).
