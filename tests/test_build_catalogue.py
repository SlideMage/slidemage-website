"""The catalogue builder against a fake GitHub: conventions, pinning, hidden plugins, quiet runs."""
import hashlib
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_catalogue as bc  # noqa: E402

SITE = "https://example.org/site/"
ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>'


def smplugin(pid="hello", version="0.1.0", **changes):
    manifest = {"id": pid, "name": pid.title(), "version": version, "api_version": 1,
                "requires_slidemage": ">=9.0", "summary": "A test plugin.", "author": "Someone",
                "homepage": "https://github.com/someone/p", "license": "GPL-3.0-or-later", "needs": [],
                "network": []}
    manifest.update(changes)
    lines = []
    for key, value in manifest.items():
        lines.append(f"{key} = {json.dumps(value)}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("plugin.toml", "\n".join(lines) + "\n")
        archive.writestr(f"{pid}/__init__.py", "def activate(host):\n    pass\n")
    return buffer.getvalue()


README = "# Hello\n\nSays hello.\n\n## Development\n\nBuild notes.\n"
CHANGELOG = "# History\n\nv0.1.0 (2026-10-26, first release): The first one.\n"


class FakeGitHub:
    def __init__(self):
        self.repos, self.files, self.urls = {}, {}, {}

    def release(self, repo, tag, assets, draft=False, prerelease=False, material=True):
        if material:
            self.files[(repo, tag, "README.md")] = README.encode()
            self.files[(repo, tag, "CHANGELOG.md")] = CHANGELOG.encode()
        entries = []
        for name, data in assets.items():
            url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
            self.urls[url] = data
            entries.append({"name": name, "size": len(data), "browser_download_url": url})
        self.repos.setdefault(repo, []).append({
            "tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": entries,
            "published_at": "2026-10-26T10:00:00Z", "html_url": f"https://github.com/{repo}/releases/tag/{tag}"})

    def releases(self, repo):
        if repo not in self.repos:
            raise bc.urllib.error.URLError("not found")
        return self.repos[repo]

    def download(self, url):
        return self.urls[url]

    def file_at(self, repo, tag, path):
        return self.files.get((repo, tag, path))

    def list_dir(self, repo, tag, path):
        prefix = f"{path}/"
        return [{"name": p[len(prefix):], "size": len(data)} for (r, t, p), data in self.files.items()
                if r == repo and t == tag and p.startswith(prefix) and "/" not in p[len(prefix):]]


@pytest.fixture
def site(tmp_path, monkeypatch):
    for name in ("REGISTRY", "PINS", "HEARTBEAT", "OUT", "MKDOCS"):
        monkeypatch.setattr(bc, name, tmp_path / getattr(bc, name).relative_to(ROOT))
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs" / "plugins").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "plugins" / "index.md", tmp_path / "docs" / "plugins" / "index.md")
    (tmp_path / "mkdocs.yml").write_text(f"site_name: x\nsite_url: {SITE}\n")
    return tmp_path


def registry(site, text):
    (site / "registry" / "plugins.toml").write_text(text)


HELLO = '[[plugin]]\nid = "hello"\nrepository = "o/hello"\nmaintainer = "M"\nreleases = "all"\nyanked = []\n'


def catalogue(site, name="index-test.json"):
    return json.loads((site / "docs" / "plugins" / name).read_text())


def test_a_release_that_follows_the_conventions_is_listed_and_pinned(site):
    gh = FakeGitHub()
    data = smplugin()
    digest = hashlib.sha256(data).hexdigest()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": data,
                                     "hello-0.1.0.smplugin.sha256": f"{digest}  hello-0.1.0.smplugin\n".encode()})
    gh.files[("o/hello", "v0.1.0", "website/icon.svg")] = ICON
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    plugin = catalogue(site, "index.json")["plugins"][0]
    assert plugin["homepage"] == SITE + "plugins/hello/"
    assert plugin["icon"] == SITE + "plugins/hello/icon.svg"
    assert plugin["releases"][0]["sha256"] == digest
    assert (site / "docs" / "plugins" / "hello" / "icon.svg").read_bytes() == ICON
    assert json.loads((site / "catalogue" / "pins.json").read_text())["hello"]["0.1.0"]["sha256"] == digest


def test_hidden_plugins_are_only_in_the_test_catalogue(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert catalogue(site, "index.json")["plugins"] == []
    assert [p["id"] for p in catalogue(site)["plugins"]] == ["hello"]


@pytest.mark.parametrize("assets, prerelease", [
    ({"hello-0.2.0.smplugin": smplugin(version="0.2.0")}, True),          # pre-release: ignored
    ({"hello-0.2.0.zip": smplugin(version="0.2.0")}, False),              # wrong asset name: refused
    ({"hello-0.2.0.smplugin": smplugin(version="0.3.0")}, False),         # version differs from the tag
    ({"hello-0.2.0.smplugin": smplugin(version="0.2.0"),
      "hello-0.2.0.smplugin.sha256": b"0" * 64}, False),                  # .sha256 does not match
    ({"hello-0.2.0.smplugin": smplugin(version="0.2.0"), "notes.txt": b"x"}, False),   # extra asset
])
def test_releases_that_break_a_convention_are_left_out(site, assets, prerelease):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    gh.release("o/hello", "v0.2.0", assets, prerelease=prerelease)
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert [r["version"] for r in catalogue(site)["plugins"][0]["releases"]] == ["0.1.0"]


def test_compiled_files_are_refused(site):
    gh = FakeGitHub()
    buffer = io.BytesIO(smplugin())
    with zipfile.ZipFile(buffer, "a") as archive:
        archive.writestr("hello/fast.pyd", b"\0")
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": buffer.getvalue()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert catalogue(site)["plugins"] == []


def test_yanked_and_unapproved_versions_are_left_out_newest_first(site):
    gh = FakeGitHub()
    for version in ("1.0.0", "1.1.0", "1.2.0", "1.10.0"):
        gh.release("o/hello", f"v{version}", {f"hello-{version}.smplugin": smplugin(version=version)})
    registry(site, HELLO.replace('releases = "all"', 'releases = ["1.0.0", "1.1.0", "1.10.0"]')
             .replace("yanked = []", 'yanked = ["1.1.0"]'))
    assert bc.main([], gh) == 0
    assert [r["version"] for r in catalogue(site)["plugins"][0]["releases"]] == ["1.10.0", "1.0.0"]


def test_a_replaced_asset_is_dropped_and_reported(site, tmp_path):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    url = gh.repos["o/hello"][0]["assets"][0]["browser_download_url"]
    gh.urls[url] = smplugin(summary="Same size, other bytes.")[:len(gh.urls[url])].ljust(len(gh.urls[url]), b"x")
    report = tmp_path / "report.json"
    assert bc.main(["--report", str(report)], gh) == 0                  # hourly run: size unchanged, still listed
    assert catalogue(site)["plugins"]
    assert bc.main(["--full-check", "--report", str(report)], gh) == 0  # daily run: hash differs, dropped
    assert catalogue(site)["plugins"] == []
    assert [p["kind"] for p in json.loads(report.read_text())["problems"]] == ["changed", "error"]


def test_a_run_without_news_changes_no_file(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    before = {path: path.read_bytes() for path in site.rglob("*") if path.is_file()}
    assert bc.main([], gh) == 0
    assert {path: path.read_bytes() for path in site.rglob("*") if path.is_file()} == before


def test_when_github_cannot_be_read_the_previous_entry_is_kept(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert bc.main([], FakeGitHub()) == 0
    assert [p["id"] for p in catalogue(site)["plugins"]] == ["hello"]


def test_check_mode_writes_nothing_and_fails_for_a_broken_new_entry(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.zip": smplugin()})
    registry(site, HELLO)
    assert bc.main(["--check"], gh) == 1
    assert not (site / "docs" / "plugins" / "index.json").exists()
    assert not (site / "catalogue").exists()


@pytest.mark.parametrize("text", [
    HELLO + HELLO,                                              # listed twice
    HELLO.replace('"hello"', '"Hello"'),                        # invalid id
    HELLO.replace('releases = "all"', 'releases = "some"'),
    HELLO + "colour = 1\n",                                     # unknown key
])
def test_an_invalid_registry_fails_the_whole_run(site, text):
    registry(site, text)
    assert bc.main([], FakeGitHub()) == 1


def test_unsafe_or_small_icons_are_refused():
    assert bc.check_icon("website/icon.svg", b'<svg onload="x()"/>')
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + (64).to_bytes(4, "big") * 2
    assert "128" in bc.check_icon("website/icon.png", png)
    assert bc.check_icon("website/icon.svg", ICON) is None


def page_of(site, pid="hello"):
    return (site / "docs" / "plugins" / pid / "index.md").read_text(encoding="utf-8")


def test_a_listed_plugin_gets_a_page_and_a_card(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin(network=["Example server"])})
    gh.files[("o/hello", "v0.1.0", "website/icon.svg")] = ICON
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    page = page_of(site)
    assert page.startswith("# Hello\n")
    assert "Says hello." in page and "Build notes" not in page          # README cut at ## Development
    assert "- Example server" in page and "What leaves your computer" in page
    assert "### v0.1.0" in page and "The first one." in page
    assert "| 0.1.0 | &gt;=9.0 | 2026-10-26 |" in page
    index = (site / "docs" / "plugins" / "index.md").read_text(encoding="utf-8")
    assert "[Hello](hello/index.md)" in index and "No plugins listed yet" not in index
    assert "hello/icon.svg" in index


def test_hidden_plugins_get_no_page_or_card(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert not (site / "docs" / "plugins" / "hello" / "index.md").exists()
    assert "No plugins listed yet" in (site / "docs" / "plugins" / "index.md").read_text(encoding="utf-8")


def test_a_release_without_readme_or_changelog_is_refused(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()}, material=False)
    gh.files[("o/hello", "v0.1.0", "README.md")] = README.encode()
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert catalogue(site)["plugins"] == []


def test_screenshots_are_copied_in_name_order_at_most_six_and_small(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 100
    for name in ("b.png", "a.png", "c.png", "d.png", "e.png", "f.png", "g.png"):
        gh.files[("o/hello", "v0.1.0", f"website/screenshots/{name}")] = png
    gh.files[("o/hello", "v0.1.0", "website/screenshots/big.png")] = png + b"\0" * 1_000_000
    gh.files[("o/hello", "v0.1.0", "website/screenshots/fake.png")] = b"GIF89a"
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    shots = sorted(p.name for p in (site / "docs" / "plugins" / "hello" / "screenshots").iterdir())
    assert shots == ["a.png", "b.png", "c.png", "d.png", "e.png", "f.png"]
    assert page_of(site).index("screenshots/a.png") < page_of(site).index("screenshots/b.png")


def test_a_plugin_no_longer_listed_loses_its_page(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    registry(site, HELLO.replace('yanked = []', 'yanked = ["0.1.0"]'))
    assert bc.main([], gh) == 0
    assert not (site / "docs" / "plugins" / "hello" / "index.md").exists()


def test_third_party_markdown_is_defused():
    text = bc.pages.defuse(
        "# Title\n<script>alert(1)</script>\nA [bad](javascript:alert(1)) and [doc](docs/x.md) and "
        "[ok](https://a.org)\n![shot](img.png)\nText{: onclick=\"x\" }\n`<kept>` code\n"
        "```python {onclick=x}\n<b>in code</b>\n```\n[ref]: javascript:evil\n", "o/p", "v1.0.0")
    assert "<script" not in text and "&lt;script&gt;" in text
    assert "javascript:" not in text
    assert "(https://github.com/o/p/blob/v1.0.0/docs/x.md)" in text and "(https://a.org)" in text
    assert "*shot*" in text and "img.png" not in text
    assert "{:" not in text and "&#123;: onclick" in text
    assert "`<kept>`" in text and "<b>in code</b>" in text
    assert "```python\n" in text and "## Title" in text


def test_plugin_fields_cannot_inject_markup():
    assert bc.pages.inline("<img src=x> [a](b) {: x}") == r"&lt;img src=x&gt; \[a\](b) &#123;: x&#125;"
