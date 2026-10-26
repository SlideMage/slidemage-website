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


class FakeGitHub:
    def __init__(self):
        self.repos, self.files, self.urls = {}, {}, {}

    def release(self, repo, tag, assets, draft=False, prerelease=False):
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


@pytest.fixture
def site(tmp_path, monkeypatch):
    for name in ("REGISTRY", "PINS", "HEARTBEAT", "OUT", "MKDOCS"):
        monkeypatch.setattr(bc, name, tmp_path / getattr(bc, name).relative_to(ROOT))
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs" / "plugins").mkdir(parents=True)
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
