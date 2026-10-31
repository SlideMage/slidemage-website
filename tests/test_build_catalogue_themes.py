"""Themes in the catalogue builder: listing, pinning, the checks on a .smtheme, previews, and no trace without one."""
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
from test_build_catalogue import HELLO, SITE, FakeGitHub, catalogue, registry, smplugin  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 100
THEME = '[[theme]]\nid = "uni-graz"\nrepository = "o/uni-graz"\nmaintainer = "M"\nreleases = "all"\nyanked = []\n'
BASE_FILES = {
    "SlideMage_template_uni-graz.tex": "\\ProvidesFile{x}\n",
    "schemes/scheme_uni_graz/logo.pdf": "pdf",
    "LICENSE": "MIT", "README.md": "# T\n", "CHANGELOG.md": "# C\n",
}


def smtheme(tid="uni-graz", version="1.0.0", files=None, drop=(), manifest_drop=(), **changes):
    """A .smtheme; files adds (or with None removes) members, names are stored exactly as given."""
    manifest = {"id": tid, "name": "Uni Graz", "version": version, "requires_slidemage": ">=10.16",
                "summary": "A test theme.", "author": "Someone", "homepage": "https://github.com/someone/t",
                "license": "LPPL-1.3c-or-later", "layout": "fira"}
    manifest.update(changes)
    members = {"theme.toml": "".join(f"{key} = {json.dumps(value)}\n" for key, value in manifest.items()
                                     if key not in manifest_drop),
               **BASE_FILES, **(files or {})}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            if content is None or name in drop:
                continue
            info = zipfile.ZipInfo("x")
            info.filename = name        # as given: ZipInfo("..") would turn a Windows backslash into a slash
            archive.writestr(info, content)
    return buffer.getvalue()


@pytest.fixture
def site(tmp_path, monkeypatch):
    for name in ("REGISTRY", "PINS", "THEME_PINS", "HEARTBEAT", "OUT", "THEME_OUT", "MKDOCS"):
        monkeypatch.setattr(bc, name, tmp_path / getattr(bc, name).relative_to(ROOT))
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs" / "plugins").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "plugins" / "index.md", tmp_path / "docs" / "plugins" / "index.md")
    (tmp_path / "mkdocs.yml").write_text(f"site_name: x\nsite_url: {SITE}\n")
    return tmp_path


def release(gh, data, version="1.0.0", tag=None, name=None, **kwargs):
    gh.release("o/uni-graz", tag or f"v{version}", {name or f"uni-graz-{version}.smtheme": data}, **kwargs)


def themes(site, name="index-test.json"):
    return catalogue(site, name).get("themes", [])


def test_a_valid_theme_is_listed_and_pinned_apart_from_plugins(site):
    gh = FakeGitHub()
    data = smtheme(files={"preview.png": PNG, "SlideMage_layout_uni.tex": "x"}, layout="uni")
    digest = hashlib.sha256(data).hexdigest()
    gh.release("o/uni-graz", "v1.0.0", {"uni-graz-1.0.0.smtheme": data,
                                        "uni-graz-1.0.0.smtheme.sha256": f"{digest}  x\n".encode()})
    registry(site, HELLO + THEME)
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    assert bc.main([], gh) == 0
    theme = themes(site, "index.json")[0]
    assert theme["homepage"] == SITE + "themes/uni-graz/"
    assert theme["layout"] == "uni" and theme["preview"] == SITE + "themes/uni-graz/preview.png"
    assert theme["releases"][0]["sha256"] == digest and "api_version" not in theme["releases"][0]
    assert theme["releases"][0]["requires_slidemage"] == ">=10.16"
    pins = json.loads((site / "catalogue" / "theme-pins.json").read_text())
    assert pins["uni-graz"]["1.0.0"]["sha256"] == digest
    assert "uni-graz" not in json.loads((site / "catalogue" / "pins.json").read_text())
    assert (site / "docs" / "themes" / "uni-graz" / "preview.png").read_bytes() == PNG
    assert not (site / "docs" / "themes" / "uni-graz" / "index.md").exists()
    assert bc.validate(catalogue(site)) == []


def test_without_a_theme_nothing_about_themes_appears(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert "themes" not in catalogue(site) and "themes" not in catalogue(site, "index.json")
    assert not (site / "catalogue" / "theme-pins.json").exists()
    assert not (site / "docs" / "themes").exists()


def test_a_hidden_theme_is_only_in_the_test_catalogue(site):
    gh = FakeGitHub()
    release(gh, smtheme())
    registry(site, THEME + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert "themes" not in catalogue(site, "index.json")
    assert [t["id"] for t in themes(site)] == ["uni-graz"]
    assert bc.validate(catalogue(site)) == []


def test_a_previous_entry_is_kept_when_github_cannot_be_read(site):
    gh = FakeGitHub()
    release(gh, smtheme(files={"preview.png": PNG}))
    registry(site, THEME)
    assert bc.main([], gh) == 0
    assert bc.main([], FakeGitHub()) == 0
    assert themes(site)[0]["preview"].endswith("preview.png")
    assert (site / "docs" / "themes" / "uni-graz" / "preview.png").exists()


def test_check_mode_fails_for_a_theme_without_a_listable_release(site):
    gh = FakeGitHub()
    release(gh, smtheme(), name="uni-graz-1.0.0.zip")
    registry(site, THEME)
    assert bc.main(["--check"], gh) == 1
    release(gh, smtheme(version="1.1.0"), version="1.1.0")
    assert bc.main(["--check"], gh) == 0
    assert not (site / "catalogue").exists()


@pytest.mark.parametrize("package", [
    smtheme(api_version=1),                                              # plugin keys are refused
    smtheme(needs=[]),
    smtheme(network=[]),
    smtheme(version="1.0.1"),                                            # differs from the tag v1.0.0
    smtheme(id="other"),
    smtheme(manifest_drop=("layout",)),
    smtheme(homepage="ftp://x"),
    smtheme(files={"schemes/scheme_uni_graz/x.sty": "x"}),               # TeX code besides the template
    smtheme(files={"SlideMage_layout_fira.tex": "x"}),                   # a standard layout is not shipped
    smtheme(files={"fast.pyd": b"\0"}),                                  # compiled
    smtheme(files={"../evil.txt": "x"}),                                 # path outside the package
    smtheme(files={"a/../evil.txt": "x"}),
    smtheme(files={"/abs.txt": "x"}),
    smtheme(files={"C:/abs.txt": "x"}),
    smtheme(files={"schemes\\scheme_uni_graz\\a.pdf": "x"}),             # backslash
    smtheme(files={"schemes/scheme_other/logo.pdf": "x"}),               # wrong scheme folder
    smtheme(files={"notes.txt": "x"}),                                   # nothing else
    smtheme(drop=("SlideMage_template_uni-graz.tex",)),                  # template missing
    smtheme(drop=("LICENSE",)),
    smtheme(layout="uni"),                                               # own layout without its file
    b"not a zip",
    smtheme(drop=("theme.toml",)),
])
def test_packages_that_break_a_rule_are_refused(site, package):
    gh = FakeGitHub()
    release(gh, package)
    registry(site, THEME)
    assert bc.main([], gh) == 0
    assert themes(site) == []
    assert bc.main(["--check"], gh) == 1


def test_a_symbolic_link_is_refused():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.toml", zipfile.ZipFile(io.BytesIO(smtheme())).read("theme.toml"))
        info = zipfile.ZipInfo("link.txt")
        info.external_attr = (0o120777 << 16)
        archive.writestr(info, "LICENSE")
    _, problems = bc.inspect_theme(buffer.getvalue(), "uni-graz", "1.0.0")
    assert any("outside the package" in problem for problem in problems)


def test_a_wrong_asset_name_or_a_reserved_id_is_refused(site):
    gh = FakeGitHub()
    release(gh, smtheme(), name="uni-graz-1.0.0.smplugin")
    registry(site, THEME)
    assert bc.main(["--check"], gh) == 1
    for reserved in ("slidemage", "greyscale", "submit"):
        registry(site, THEME.replace("uni-graz", reserved))
        assert bc.main([], gh) == 1


@pytest.mark.parametrize("picture", [b"GIF89a", PNG + b"\0" * 1_000_000], ids=["not-png", "too-big"])
def test_an_unusable_preview_leaves_the_theme_listed_without_it(site, picture):
    gh = FakeGitHub()
    release(gh, smtheme(files={"preview.png": picture}))
    registry(site, THEME)
    assert bc.main([], gh) == 0
    assert "preview" not in themes(site)[0]
    assert not (site / "docs" / "themes" / "uni-graz" / "preview.png").exists()


def test_a_theme_leaving_the_catalogue_loses_its_preview(site):
    gh = FakeGitHub()
    release(gh, smtheme(files={"preview.png": PNG}))
    registry(site, THEME)
    assert bc.main([], gh) == 0
    registry(site, THEME.replace("yanked = []", 'yanked = ["1.0.0"]'))
    assert bc.main([], gh) == 0
    assert not (site / "docs" / "themes" / "uni-graz" / "preview.png").exists()
    assert "themes" not in catalogue(site)


def test_a_run_without_news_changes_no_file(site):
    gh = FakeGitHub()
    release(gh, smtheme(files={"preview.png": PNG}))
    registry(site, THEME)
    assert bc.main([], gh) == 0
    before = {path: path.read_bytes() for path in site.rglob("*") if path.is_file()}
    assert bc.main([], gh) == 0
    assert {path: path.read_bytes() for path in site.rglob("*") if path.is_file()} == before


def test_a_replaced_theme_asset_is_dropped_and_reported(site, tmp_path):
    gh = FakeGitHub()
    release(gh, smtheme())
    registry(site, THEME)
    assert bc.main([], gh) == 0
    url = gh.repos["o/uni-graz"][0]["assets"][0]["browser_download_url"]
    gh.urls[url] = b"x" * len(gh.urls[url])
    report = tmp_path / "report.json"
    assert bc.main(["--full-check", "--report", str(report)], gh) == 0
    assert themes(site) == []
    problems = json.loads(report.read_text())["problems"]
    assert problems[0]["kind"] == "changed" and problems[0]["plugin"] == "theme uni-graz"


@pytest.mark.parametrize("text", [
    THEME + THEME,                                              # listed twice
    THEME.replace('"uni-graz"', '"Uni"'),                       # invalid id
    THEME + "colour = 1\n",                                     # unknown key
    THEME.replace('releases = "all"', 'releases = "some"'),
])
def test_an_invalid_theme_registry_fails_the_whole_run(site, text):
    registry(site, text)
    assert bc.main([], FakeGitHub()) == 1
