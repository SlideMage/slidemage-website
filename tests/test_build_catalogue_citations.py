"""Citation formats in the catalogue builder: listing, pinning, the checks on a .smcite, previews, and no trace
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
CITATION = '[[citation]]\nid = "ieee"\nrepository = "o/ieee"\nmaintainer = "M"\nreleases = "all"\nyanked = []\n'
BASE_FILES = {
    "SlideMage_citation_ieee.tex": "\\ProvidesFile{x}\n",
    "LICENSE": "MIT", "README.md": "# T\n", "CHANGELOG.md": "# C\n",
}


def smcite(cid="ieee", version="1.0.0", files=None, drop=(), manifest_drop=(), **changes):
    """A .smcite; files adds (or with None removes) members, names are stored exactly as given."""
    manifest = {"id": cid, "name": "IEEE", "version": version, "requires_slidemage": ">=0.13.0",
                "summary": "A test citation format.", "author": "Someone",
                "homepage": "https://github.com/someone/c", "license": "LPPL-1.3c-or-later"}
    manifest.update(changes)
    members = {"citation.toml": "".join(f"{key} = {json.dumps(value)}\n" for key, value in manifest.items()
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
    for name in ("REGISTRY", "PINS", "CITATION_PINS", "HEARTBEAT", "OUT", "CITATION_OUT", "MKDOCS"):
        monkeypatch.setattr(bc, name, tmp_path / getattr(bc, name).relative_to(ROOT))
    (tmp_path / "registry").mkdir()
    (tmp_path / "docs" / "plugins").mkdir(parents=True)
    shutil.copy(ROOT / "docs" / "plugins" / "index.md", tmp_path / "docs" / "plugins" / "index.md")
    (tmp_path / "mkdocs.yml").write_text(f"site_name: x\nsite_url: {SITE}\n")
    return tmp_path


def release(gh, data, version="1.0.0", tag=None, name=None, **kwargs):
    gh.release("o/ieee", tag or f"v{version}", {name or f"ieee-{version}.smcite": data}, **kwargs)


def citations(site, name="index-test.json"):
    return catalogue(site, name).get("citations", [])


def test_a_valid_citation_is_listed_and_pinned_apart_from_plugins(site):
    gh = FakeGitHub()
    data = smcite(files={"preview.png": PNG})
    digest = hashlib.sha256(data).hexdigest()
    gh.release("o/ieee", "v1.0.0", {"ieee-1.0.0.smcite": data,
                                    "ieee-1.0.0.smcite.sha256": f"{digest}  x\n".encode()})
    registry(site, HELLO + CITATION)
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    assert bc.main([], gh) == 0
    citation = citations(site, "index.json")[0]
    assert citation["homepage"] == SITE + "citations/ieee/"
    assert citation["preview"] == SITE + "citations/ieee/preview.png"
    assert citation["releases"][0]["sha256"] == digest and "api_version" not in citation["releases"][0]
    assert citation["releases"][0]["requires_slidemage"] == ">=0.13.0"
    pins = json.loads((site / "catalogue" / "citation-pins.json").read_text())
    assert pins["ieee"]["1.0.0"]["sha256"] == digest
    assert "ieee" not in json.loads((site / "catalogue" / "pins.json").read_text())
    assert (site / "docs" / "citations" / "ieee" / "preview.png").read_bytes() == PNG
    assert not (site / "docs" / "citations" / "ieee" / "index.md").exists()
    assert bc.validate(catalogue(site)) == []


def test_without_a_citation_nothing_about_citations_appears(site):
    gh = FakeGitHub()
    gh.release("o/hello", "v0.1.0", {"hello-0.1.0.smplugin": smplugin()})
    registry(site, HELLO)
    assert bc.main([], gh) == 0
    assert "citations" not in catalogue(site) and "citations" not in catalogue(site, "index.json")
    assert not (site / "catalogue" / "citation-pins.json").exists()
    assert not (site / "docs" / "citations").exists()


def test_a_hidden_citation_is_only_in_the_test_catalogue(site):
    gh = FakeGitHub()
    release(gh, smcite())
    registry(site, CITATION + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert "citations" not in catalogue(site, "index.json")
    assert [c["id"] for c in citations(site)] == ["ieee"]
    assert bc.validate(catalogue(site)) == []


def test_a_previous_entry_is_kept_when_github_cannot_be_read(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert bc.main([], FakeGitHub()) == 0
    assert citations(site)[0]["preview"].endswith("preview.png")
    assert (site / "docs" / "citations" / "ieee" / "preview.png").exists()


def test_check_mode_fails_for_a_citation_without_a_listable_release(site):
    gh = FakeGitHub()
    release(gh, smcite(), name="ieee-1.0.0.zip")
    registry(site, CITATION)
    assert bc.main(["--check"], gh) == 1
    release(gh, smcite(version="1.1.0"), version="1.1.0")
    assert bc.main(["--check"], gh) == 0
    assert not (site / "catalogue").exists()


def test_extra_bibliography_files_are_allowed(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"SlideMage_citation_ieee_shared.bbx": "x", "SlideMage_citation_ieee.cbx": "x"}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert [c["id"] for c in citations(site)] == ["ieee"]


@pytest.mark.parametrize("package", [
    smcite(api_version=1),                                              # plugin/theme keys are refused
    smcite(needs=[]),
    smcite(network=[]),
    smcite(layout="fira"),
    smcite(version="1.0.1"),                                            # differs from the tag v1.0.0
    smcite(id="other"),
    smcite(homepage="ftp://x"),
    smcite(files={"x.sty": "x"}),                                       # TeX code besides format/extra files
    smcite(files={"x.bst": "x"}),
    smcite(files={"fast.pyd": b"\0"}),                                  # compiled
    smcite(files={"../evil.txt": "x"}),                                 # path outside the package
    smcite(files={"a/../evil.txt": "x"}),
    smcite(files={"/abs.txt": "x"}),
    smcite(files={"C:/abs.txt": "x"}),
    smcite(files={"a\\b.txt": "x"}),                                    # backslash
    smcite(files={"notes.txt": "x"}),                                   # nothing else
    smcite(files={"SlideMage_base.tex": "x"}),                          # named like a framework file
    smcite(files={"SlideMage_citation_default.tex": "x"}),
    smcite(drop=("SlideMage_citation_ieee.tex",)),                      # format file missing
    smcite(drop=("LICENSE",)),
    b"not a zip",
    smcite(drop=("citation.toml",)),
])
def test_packages_that_break_a_rule_are_refused(site, package):
    gh = FakeGitHub()
    release(gh, package)
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert citations(site) == []
    assert bc.main(["--check"], gh) == 1


def test_a_framework_named_file_is_refused_with_a_clear_reason():
    _, problems = bc.inspect_citation(smcite(files={"SlideMage_base.tex": "x"}), "ieee", "1.0.0")
    assert any("framework files" in problem for problem in problems)


def test_a_symbolic_link_is_refused():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("citation.toml", zipfile.ZipFile(io.BytesIO(smcite())).read("citation.toml"))
        info = zipfile.ZipInfo("link.txt")
        info.external_attr = (0o120777 << 16)
        archive.writestr(info, "LICENSE")
    _, problems = bc.inspect_citation(buffer.getvalue(), "ieee", "1.0.0")
    assert any("outside the package" in problem for problem in problems)


def test_a_wrong_asset_name_or_a_reserved_id_is_refused(site):
    gh = FakeGitHub()
    release(gh, smcite(), name="ieee-1.0.0.smplugin")
    registry(site, CITATION)
    assert bc.main(["--check"], gh) == 1
    for reserved in ("default", "submit"):
        registry(site, CITATION.replace("ieee", reserved))
        assert bc.main([], gh) == 1


@pytest.mark.parametrize("picture", [b"GIF89a", PNG + b"\0" * 1_000_000], ids=["not-png", "too-big"])
def test_an_unusable_preview_leaves_the_citation_listed_without_it(site, picture):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": picture}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    assert "preview" not in citations(site)[0]
    assert not (site / "docs" / "citations" / "ieee" / "preview.png").exists()


def test_a_citation_leaving_the_catalogue_loses_its_preview(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    registry(site, CITATION.replace("yanked = []", 'yanked = ["1.0.0"]'))
    assert bc.main([], gh) == 0
    assert not (site / "docs" / "citations" / "ieee" / "preview.png").exists()
    assert "citations" not in catalogue(site)


def test_a_run_without_news_changes_no_file(site):
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    before = {path: path.read_bytes() for path in site.rglob("*") if path.is_file()}
    assert bc.main([], gh) == 0
    assert {path: path.read_bytes() for path in site.rglob("*") if path.is_file()} == before


def test_a_replaced_citation_asset_is_dropped_and_reported(site, tmp_path):
    gh = FakeGitHub()
    release(gh, smcite())
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    url = gh.repos["o/ieee"][0]["assets"][0]["browser_download_url"]
    gh.urls[url] = b"x" * len(gh.urls[url])
    report = tmp_path / "report.json"
    assert bc.main(["--full-check", "--report", str(report)], gh) == 0
    assert citations(site) == []
    problems = json.loads(report.read_text())["problems"]
    assert problems[0]["kind"] == "changed" and problems[0]["plugin"] == "citation ieee"


@pytest.mark.parametrize("text", [
    CITATION + CITATION,                                        # listed twice
    CITATION.replace('"ieee"', '"IEEE"'),                       # invalid id
    CITATION + "colour = 1\n",                                  # unknown key
    CITATION.replace('releases = "all"', 'releases = "some"'),
])
def test_an_invalid_citation_registry_fails_the_whole_run(site, text):
    registry(site, text)
    assert bc.main([], FakeGitHub()) == 1


# --- per-format pages and cards -------------------------------------------------------------------------------------


def _site_with_cards(site):
    index = site / "docs" / "citations"
    index.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "docs" / "citations" / "index.md", index / "index.md")
    return index


def test_a_listed_format_gets_a_page_and_a_card_and_loses_both_when_it_goes(site):
    folder = _site_with_cards(site)
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    gh.files[("o/ieee", "v1.0.0", "README.md")] = b"# A\n\nAPA <script>x</script> [l](javascript:x)\n\n## Development\n\nn\n"
    registry(site, CITATION)
    assert bc.main([], gh) == 0
    page = (folder / "ieee" / "index.md").read_text()
    assert "# IEEE" in page and "![The reference list of IEEE on a slide](preview.png)" in page
    assert "SMCitationFormat}{ieee}" in page and "ieee-1.0.0.smcite" in page
    assert "<script>" not in page and "javascript:" not in page and "Development" not in page
    cards = (folder / "index.md").read_text()
    assert "(ieee/index.md)" in cards and "ieee/preview.png" in cards
    registry(site, "")
    assert bc.main([], gh) == 0
    assert not (folder / "ieee" / "index.md").exists() and "(ieee/index.md)" not in (folder / "index.md").read_text()


def test_a_hidden_format_has_no_page_or_card(site):
    folder = _site_with_cards(site)
    gh = FakeGitHub()
    release(gh, smcite())
    registry(site, CITATION + "hidden = true\n")
    assert bc.main([], gh) == 0
    assert not (folder / "ieee" / "index.md").exists() and "(ieee/index.md)" not in (folder / "index.md").read_text()


def test_the_built_in_house_format_has_a_card_and_keeps_its_hand_written_page(site):
    folder = _site_with_cards(site)
    (folder / "default").mkdir()
    (folder / "default" / "index.md").write_text("# House\n")
    (folder / "default" / "preview.png").write_bytes(PNG)
    gh = FakeGitHub()
    release(gh, smcite(files={"preview.png": PNG}))
    registry(site, CITATION)
    for _ in range(2):          # a second run changes nothing
        assert bc.main([], gh) == 0
    cards = (folder / "index.md").read_text()
    assert cards.index("(default/index.md)") < cards.index("(ieee/index.md)")
    assert "Built in: comes with SlideMage, nothing to install" in cards
    assert (folder / "default" / "index.md").read_text() == "# House\n"
    assert (folder / "default" / "preview.png").read_bytes() == PNG
    for name in ("index.json", "index-test.json"):      # never a catalogue entry
        assert [c["id"] for c in catalogue(site, name).get("citations", [])] == ["ieee"]
    registry(site, "")
    assert bc.main([], gh) == 0
    assert (folder / "default" / "index.md").exists() and "(default/index.md)" in (folder / "index.md").read_text()
    assert "(ieee/index.md)" not in (folder / "index.md").read_text()
