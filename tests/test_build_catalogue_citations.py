"""Citation formats in the catalogue builder: listing, pinning, the checks on a .smcite, previews, pages, and no trace
without one."""
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
CITATION = '[[citation]]\nid = "apa"\nrepository = "o/apa"\nmaintainer = "M"\nreleases = "all"\nyanked = []\n'
BASE_FILES = {
    "SlideMage_citation_apa.tex": "\\renewcommand{\\SMBiblatexOptions}{style=apa}\n",
    "LICENSE": "LPPL", "README.md": "# A\n\nAPA 7.\n", "CHANGELOG.md": "# C\n\n## v1.0.0 (2026-11-06)\n\nFirst.\n",
}


def smcite(cid="apa", version="1.0.0", files=None, drop=(), manifest_drop=(), **changes):
    """A .smcite; files adds (or with None removes) members, names are stored exactly as given."""
    manifest = {"id": cid, "name": "APA 7", "version": version, "requires_slidemage": ">=0.13.0",
                "summary": "A test format.", "author": "Someone", "homepage": "https://github.com/someone/c",
                "license": "LPPL-1.3c-or-later"}
    manifest.update(changes)
    members = {"citation.toml": "".join(f"{key} = {json.dumps(value)}\n" for key, value in manifest.items()
                                        if key not in manifest_drop),
               **{name.replace("apa", cid): text for name, text in BASE_FILES.items()}, **(files or {})}
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
    for name in ("REGISTRY", "PINS", "THEME_PINS", "CITATION_PINS", "HEARTBEAT", "OUT", "THEME_OUT", "CITATION_OUT",
                 "MKDOCS"):
        monkeypatch.setattr(bc, name, tmp_path / getattr(bc, name).relative_to(ROOT))
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs" / "plugins").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "plugins" / "index.md", tmp_path / "docs" / "plugins" / "index.md")
    (tmp_path / "docs" / "citations").mkdir()
    shutil.copy(ROOT / "docs" / "citations" / "index.md", tmp_path / "docs" / "citations" / "index.md")
    (tmp_path / "mkdocs.yml").write_text(f"site_name: x\nsite_url: {SITE}\n")
    return tmp_path


def release(gh, data, version="1.0.0", tag=None, name=None, **kwargs):
    gh.release("o/apa", tag or f"v{version}", {name or f"apa-{version}.smcite": data}, **kwargs)


def formats(site, name="index-test.json"):
    return catalogue(site, name).get("citations", [])


def test_a_valid_format_is_listed_pinned_and_gets_a_page(site):
    gh = FakeGitHub()
    data = smcite(files={"preview.png": PNG, "SlideMage_citation_apa_extra.bbx": "x", "LICENSES/LPPL.txt": "x"})
    digest = hashlib.sha256(data).hexdigest()
    release(gh, data)
    gh.release("o/apa", "v1.0.1", {"apa-1.0.1.smcite": smcite(version="1.0.1"),
                                   "apa-1.0.1.smcite.sha256": b"0" * 64 + b"  x\n"})   # wrong hash: refused
    registry(site, HELLO + CITATION)
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    assert bc.main([], gh) == 0
    entry = formats(site, "index.json")[0]
    assert entry["homepage"] == SITE + "citations/apa/" and "layout" not in entry
    assert entry["preview"] == SITE + "citations/apa/preview.png"
    assert [r["version"] for r in entry["releases"]] == ["1.0.0"]
    assert entry["releases"][0]["sha256"] == digest and "api_version" not in entry["releases"][0]
    pins = json.loads((site / "catalogue" / "citation-pins.json").read_text())
    assert pins["apa"]["1.0.0"]["sha256"] == digest
    assert "apa" not in json.loads((site / "catalogue" / "pins.json").read_text())
    assert (site / "docs" / "citations" / "apa" / "preview.png").read_bytes() == PNG
    page = (site / "docs" / "citations" / "apa" / "index.md").read_text()
    assert "# APA 7" in page and "SMCitationFormat}{apa}" in page and "apa-1.0.0.smcite" in page
    assert "citations/apa" not in page and "(apa/index.md)" in (site / "docs" / "citations" / "index.md").read_text()
    assert bc.validate(catalogue(site)) == []


def test_without_a_format_nothing_about_citations_appears(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    before = (site / "docs" / "citations" / "index.md").read_text()
    assert bc.main([], gh) == 0
    assert "citations" not in catalogue(site) and "citations" not in catalogue(site, "index.json")
    assert not (site / "catalogue" / "citation-pins.json").exists()
    assert (site / "docs" / "citations" / "index.md").read_text() == before


def test_a_hidden_format_is_only_in_the_test_catalogue_and_has_no_page(site):
    gh = FakeGitHub()
    release(gh, smcite())
    registry(site, CITATION + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert "citations" not in catalogue(site, "index.json")
    assert [c["id"] for c in formats(site)] == ["apa"]
    assert not (site / "docs" / "citations" / "apa" / "index.md").exists()
    assert bc.validate(catalogue(site)) == []


def test_check_mode_fails_for_a_format_without_a_listable_release(site):
    gh = FakeGitHub()
    release(gh, smcite(), name="apa-1.0.0.zip")
    registry(site, CITATION)
    assert bc.main(["--check"], gh) == 1
    release(gh, smcite(version="1.1.0"), version="1.1.0")
    assert bc.main(["--check"], gh) == 0
    assert not (site / "catalogue").exists()


@pytest.mark.parametrize("package", [
    smcite(api_version=1),                                               # plugin keys are refused
    smcite(needs=[]),
    smcite(network=[]),
    smcite(layout="fira"),                                               # a format has no layout profile
    smcite(version="1.0.1"),                                             # differs from the tag v1.0.0
    smcite(id="other"),
    smcite(manifest_drop=("homepage",)),
    smcite(homepage="ftp://x"),
    smcite(files={"SlideMage_citation_default.tex": "x"}),               # named like the framework's own file
    smcite(files={"SlideMage_base.tex": "x"}),
    smcite(files={"SlideMage_citation_other.tex": "x"}),                 # another format's file
    smcite(files={"biblatex.cfg": "x"}, ),                               # TeX code that is not the format's
    smcite(files={"apa.bbx": "x"}),                                      # a stock style's name
    smcite(files={"x.sty": "x"}),
    smcite(files={"fast.pyd": b"\0"}),                                   # compiled
    smcite(files={"../evil.txt": "x"}),                                  # path outside the package
    smcite(files={"a/../evil.txt": "x"}),
    smcite(files={"/abs.txt": "x"}),
    smcite(files={"C:/abs.txt": "x"}),
    smcite(files={"sub\\a.txt": "x"}),                                   # backslash
    smcite(files={"notes.txt": "x"}),                                    # nothing else
    smcite(files={"sub/SlideMage_citation_apa_x.tex": "x"}),             # extra files sit at the top
    smcite(drop=("SlideMage_citation_apa.tex",)),                        # the format missing
    smcite(drop=("LICENSE",)),
    smcite(drop=("CHANGELOG.md",)),
    b"not a zip",
    smcite(drop=("citation.toml",)),
])
def test_packages_that_break_a_rule_are_refused(site, package):
    gh = FakeGitHub()
    release(gh, package)
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert formats(site) == []
    assert not (site / "docs" / "citations" / "apa").exists()


def test_extra_files_of_the_format_are_accepted():
    data = smcite(files={"SlideMage_citation_apa_x.tex": "x", "SlideMage_citation_apa_x.bbx": "x",
                         "SlideMage_citation_apa_x.cbx": "x", "SlideMage_citation_apa_x.dbx": "x",
                         "SlideMage_citation_apa_x.lbx": "x", "preview.png": PNG})
    manifest, problems = bc.inspect_citation(data, "apa", "1.0.0")
    assert problems == [] and manifest["name"] == "APA 7"


def test_the_reserved_id_default_cannot_be_listed(site):
    gh = FakeGitHub()
    gh.release("o/apa", "v1.0.0", {"default-1.0.0.smcite": smcite(cid="default")})
    registry(site, CITATION.replace('"apa"', '"default"', 1))
    assert bc.main([], gh) == 1


@pytest.mark.parametrize("text", [
    CITATION.replace('"apa"', '"default"', 1),
    CITATION.replace('"apa"', '"submit"', 1),
    CITATION + CITATION,
    CITATION.replace("o/apa", "not a repo"),
    CITATION + 'extra = 1\n',
])
def test_an_invalid_citation_registry_fails_the_whole_run(site, text):
    registry(site, HELLO + text)
    assert bc.main([], FakeGitHub()) == 1


def test_a_run_without_news_changes_no_file(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    before = {p: p.read_bytes() for p in site.rglob("*") if p.is_file() and p.name != "last-run.txt"}
    assert bc.main([], gh) == 0
    after = {p: p.read_bytes() for p in site.rglob("*") if p.is_file() and p.name != "last-run.txt"}
    assert {p: v for p, v in before.items() if p.name != "index.json" and p.name != "index-test.json"} == \
           {p: v for p, v in after.items() if p.name != "index.json" and p.name != "index-test.json"}


def test_a_format_leaving_the_registry_loses_its_page_and_preview(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert (site / "docs" / "citations" / "apa" / "index.md").exists()
    registry(site, HELLO)
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    assert bc.main([], gh) == 0
    assert not (site / "docs" / "citations" / "apa" / "index.md").exists()
    assert not (site / "docs" / "citations" / "apa" / "preview.png").exists()
    assert "(apa/index.md)" not in (site / "docs" / "citations" / "index.md").read_text()
