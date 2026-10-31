"""Build the plugin catalogue from registry/plugins.toml.

Writes docs/plugins/index.json (listed plugins) and docs/plugins/index-test.json (listed and hidden ones),
pins every published asset's SHA-256 in catalogue/pins.json, copies plugin icons to docs/plugins/<id>/,
generates the listed plugins' pages (docs/plugins/<id>/index.md, with screenshots) and the cards on
docs/plugins/index.md, and keeps catalogue/last-run.txt as a monthly heartbeat. One plugin's problems never
block the others.

Themes (SlideMage slide templates, [[theme]] in the registry, packed as .smtheme) are listed the same way under
"themes" in both catalogues, but only when there is one: nothing is written for a registry without themes. Their
pins go to catalogue/theme-pins.json, the preview.png inside a package to docs/themes/<id>/preview.png; there are
no theme pages or cards.

    python tools/build_catalogue.py                 build and write
    python tools/build_catalogue.py --full-check    also re-hash every pinned asset (once a day)
    python tools/build_catalogue.py --check         build and validate, write nothing (pull requests)
    --report FILE                                   the problems found, as JSON

Exit status 1 when the registry or the catalogue as a whole is invalid; with --check also when a registry
plugin has no release that can be listed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import struct
import sys
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import NamedTuple

import plugin_pages as pages

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "plugins.toml"
SCHEMA = ROOT / "schema" / "plugins-index.schema.json"
PINS = ROOT / "catalogue" / "pins.json"
THEME_PINS = ROOT / "catalogue" / "theme-pins.json"
HEARTBEAT = ROOT / "catalogue" / "last-run.txt"
OUT = ROOT / "docs" / "plugins"
THEME_OUT = ROOT / "docs" / "themes"
MKDOCS = ROOT / "mkdocs.yml"

ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
# Ids no plugin may have, and why. "submit": docs/plugins/submit.md is /plugins/submit/, where that plugin's page
# would go. The others are folders and files SlideMage keeps next to installed plugins (RESERVED_IDS in
# SlideMage's src/slidemage/plugins/manifest.py, the ones a valid id can spell); the app refuses them.
RESERVED_IDS = {
    "submit": "a page of the website",
    **dict.fromkeys(("settings", "secrets", "pending", "staging", "old", "state", "catalogue",
                     "last-update-check", "offer-seen", "migrations-seen"), "SlideMage's own storage"),
}
# Ids no theme may have: the templates SlideMage ships (a theme cannot replace one) and "submit", where a theme's
# page would go (/themes/submit/).
RESERVED_THEME_IDS = {
    "submit": "a page of the website",
    **dict.fromkeys(("slidemage", "greyscale"), "a template SlideMage ships"),
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
RANGE_RE = re.compile(r"^(>=|<=|==|<|>)\s*\d+(\.\d+){0,2}(\s*,\s*(>=|<=|==|<|>)\s*\d+(\.\d+){0,2})*$")
REPO_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
COMPILED = (".pyc", ".pyo", ".so", ".pyd", ".dll", ".dylib", ".exe")
ICONS = ("website/icon.svg", "website/icon.png")
PNG = b"\x89PNG\r\n\x1a\n"
SCREENSHOTS, SCREENSHOT_BYTES = 6, 1_000_000
SVG_ACTIVE = re.compile(r"<script|\bon[a-z]+\s*=|javascript:|<foreignObject", re.IGNORECASE)
REGISTRY_KEYS = {"id", "repository", "maintainer", "recommended", "releases", "yanked", "hidden"}
MANIFEST_KEYS = ("name", "summary", "license", "needs", "network", "api_version", "requires_slidemage")
THEME_MANIFEST_KEYS = ("name", "summary", "license", "requires_slidemage", "layout")
# Only a theme's template and its own layout profile may be TeX code: an installed theme sits on TeX's search path
# ahead of the TeX distribution, so a .sty in it would replace a package of the same name for every deck.
TEX_CODE = (".tex", ".sty", ".cls", ".lua", ".def", ".cfg", ".fd", ".clo", ".ltx", ".dtx", ".ins")
THEME_REFUSED_KEYS = ("api_version", "needs", "network")
THEME_FILES = {"theme.toml", "LICENSE", "README.md", "CHANGELOG.md", "preview.png"}
STANDARD_LAYOUTS = ("fira", "lmsans", "lmroman")
LAYOUT_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")   # as the app's themes.LAYOUT_RE
PREVIEW_BYTES = 1_000_000
NETWORK_ERRORS = (urllib.error.URLError, OSError, ValueError)


class RegistryError(Exception):
    pass


class GitHub:
    """The few GitHub reads the builder needs. Tests replace it."""

    def __init__(self, token: str | None = None):
        self.token = token

    def _get(self, url: str, accept: str | None = None, auth: bool = False) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "slidemage-catalogue"})
        if accept:
            request.add_header("Accept", accept)
        if auth and self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()

    def releases(self, repo: str) -> list[dict]:
        found, page = [], 1
        while True:
            batch = json.loads(self._get(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}",
                                         "application/vnd.github+json", auth=True))
            found += batch
            if len(batch) < 100:
                return found
            page += 1

    def download(self, url: str) -> bytes:
        return self._get(url)   # public asset; the token must not follow the redirect to the CDN

    def list_dir(self, repo: str, tag: str, path: str) -> list[dict]:
        """The files in a folder at the tag ({name, size}); empty when the folder does not exist."""
        try:
            data = self._get(f"https://api.github.com/repos/{repo}/contents/{path}?ref={tag}",
                             "application/vnd.github+json", auth=True)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return []
            raise
        items = json.loads(data)
        return [{"name": item["name"], "size": item["size"]}
                for item in (items if isinstance(items, list) else []) if item["type"] == "file"]

    def file_at(self, repo: str, tag: str, path: str) -> bytes | None:
        try:
            return self._get(f"https://raw.githubusercontent.com/{repo}/{tag}/{path}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise


class Report:
    """Problems found, per plugin and version. kind: refused (a release breaks a convention), changed (a
    published asset changed), error (GitHub could not be read)."""

    def __init__(self):
        self.problems: list[dict] = []

    def add(self, kind: str, plugin: str, version: str | None, message: str) -> None:
        self.problems.append({"kind": kind, "plugin": plugin, "version": version, "message": message})
        where = f"{plugin} {version}" if version else plugin
        print(f"{kind}: {where}: {message}", file=sys.stderr)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def load_registry(text: str, table: str = "plugin") -> list[dict]:
    """The [[plugin]] entries of the registry, or with table="theme" its [[theme]] entries (same keys)."""
    reserved = RESERVED_IDS if table == "plugin" else RESERVED_THEME_IDS
    try:
        entries = tomllib.loads(text).get(table, [])
    except tomllib.TOMLDecodeError as exc:
        raise RegistryError(f"registry does not parse: {exc}") from exc
    seen = set()
    for entry in entries:
        pid = entry.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            raise RegistryError(f"invalid id {pid!r}")
        if pid in reserved:
            raise RegistryError(f"{pid}: the id is reserved for {reserved[pid]}")
        if pid in seen:
            raise RegistryError(f"{pid}: listed twice")
        seen.add(pid)
        unknown = set(entry) - REGISTRY_KEYS
        if unknown:
            raise RegistryError(f"{pid}: unknown keys {sorted(unknown)}")
        if not isinstance(entry.get("repository"), str) or not REPO_RE.match(entry["repository"]):
            raise RegistryError(f"{pid}: repository must be owner/name")
        if not isinstance(entry.get("maintainer"), str) or not entry["maintainer"].strip():
            raise RegistryError(f"{pid}: maintainer missing")
        for key in ("recommended", "hidden"):
            if not isinstance(entry.get(key, False), bool):
                raise RegistryError(f"{pid}: {key} must be true or false")
        releases = entry.get("releases", "all")
        if releases != "all" and not (isinstance(releases, list)
                                      and all(isinstance(v, str) and VERSION_RE.match(v) for v in releases)):
            raise RegistryError(f'{pid}: releases must be "all" or a list of versions')
        yanked = entry.get("yanked", [])
        if not (isinstance(yanked, list) and all(isinstance(v, str) and VERSION_RE.match(v) for v in yanked)):
            raise RegistryError(f"{pid}: yanked must be a list of versions")
    return entries


def check_text(manifest: dict, key: str, longest: int, problems: list[str]) -> None:
    value = manifest.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= longest:
        problems.append(f"{key} must be text of 1 to {longest} characters")


def check_manifest(manifest: dict, pid: str, version: str) -> list[str]:
    """What is wrong with a plugin.toml; empty when nothing is."""
    problems = []

    def text(key, longest):
        check_text(manifest, key, longest, problems)

    if manifest.get("id") != pid:
        problems.append(f"id is {manifest.get('id')!r}, the registry has {pid!r}")
    if manifest.get("version") != version:
        problems.append(f"version is {manifest.get('version')!r}, the tag has {version!r}")
    text("name", 40)
    text("summary", 120)
    text("author", 200)
    text("license", 200)
    api = manifest.get("api_version")
    if not isinstance(api, int) or isinstance(api, bool) or api < 1:
        problems.append("api_version must be an integer of at least 1")
    span = manifest.get("requires_slidemage")
    if not isinstance(span, str) or not RANGE_RE.match(span):
        problems.append("requires_slidemage is not a version range")
    homepage = manifest.get("homepage")
    if not isinstance(homepage, str) or not homepage.startswith("https://"):
        problems.append("homepage must be an https URL")
    for key in ("needs", "network"):
        lines = manifest.get(key)
        if not isinstance(lines, list) or not all(isinstance(s, str) and 1 <= len(s) <= 120 for s in lines):
            problems.append(f"{key} must be a list of lines of 1 to 120 characters")
    return problems


def inspect_asset(data: bytes, pid: str, version: str) -> tuple[dict | None, list[str]]:
    """The plugin.toml of a downloaded .smplugin, or the problems that refuse it."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None, ["the asset is not a zip file"]
    names = archive.namelist()
    compiled = [name for name in names if name.lower().endswith(COMPILED)]
    if compiled:
        return None, [f"compiled files in the asset: {', '.join(compiled[:3])}"]
    if "plugin.toml" not in names:
        return None, ["no plugin.toml at the root of the asset"]
    try:
        manifest = tomllib.loads(archive.read("plugin.toml").decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, [f"plugin.toml does not parse: {exc}"]
    problems = check_manifest(manifest, pid, version)
    return (None if problems else manifest), problems


def check_theme_manifest(manifest: dict, tid: str, version: str) -> list[str]:
    """What is wrong with a theme.toml; empty when nothing is."""
    problems = []
    refused = [key for key in THEME_REFUSED_KEYS if key in manifest]
    if refused:
        problems.append(f"theme.toml has {', '.join(refused)}: those belong to plugin.toml, a theme runs no Python")
    if manifest.get("id") != tid:
        problems.append(f"id is {manifest.get('id')!r}, the registry has {tid!r}")
    if manifest.get("version") != version:
        problems.append(f"version is {manifest.get('version')!r}, the tag has {version!r}")
    for key, longest in (("name", 40), ("summary", 120), ("author", 200), ("license", 200)):
        check_text(manifest, key, longest, problems)
    span = manifest.get("requires_slidemage")
    if not isinstance(span, str) or not RANGE_RE.match(span):
        problems.append("requires_slidemage is not a version range")
    homepage = manifest.get("homepage")
    if not isinstance(homepage, str) or not homepage.startswith(("https://", "http://")):
        problems.append("homepage must be an http or https URL")
    layout = manifest.get("layout")
    if not isinstance(layout, str) or not LAYOUT_RE.match(layout):
        problems.append("layout must be fira, lmsans, lmroman or the name of the package's own layout profile")
    return problems


def check_theme_members(archive: zipfile.ZipFile, tid: str, layout: str | None) -> list[str]:
    """What is wrong with the files of a .smtheme: paths, links, code, compiled files, what must be there."""
    template = f"SlideMage_template_{tid}.tex"
    own_layout = f"SlideMage_layout_{layout}.tex" if layout and layout not in STANDARD_LAYOUTS else None
    scheme = f"schemes/scheme_{tid.replace('-', '_')}/"
    unsafe, compiled, code, strays, wrong_scheme = [], [], [], [], []
    for info in archive.infolist():
        name = info.filename
        # orig_filename: on Windows zipfile turns a backslash in filename into a slash
        if (name.startswith("/") or re.match(r"^[A-Za-z]:", name) or "\\" in info.orig_filename
                or ".." in name.split("/") or (info.external_attr >> 16) & 0o170000 == 0o120000):
            unsafe.append(name)
        elif name.endswith("/"):
            continue
        elif name.lower().endswith(COMPILED):
            compiled.append(name)
        elif name.lower().endswith(TEX_CODE) and name not in (template, own_layout):
            code.append(name)
        elif name in THEME_FILES or name in (template, own_layout) or name.startswith(("LICENSES/", scheme)):
            continue
        elif name.startswith("schemes/"):
            wrong_scheme.append(name)
        else:
            strays.append(name)
    names = set(archive.namelist())
    problems = []
    for found, what in ((unsafe, "paths or links outside the package"), (compiled, "compiled files"),
                        (code, "TeX code besides the template and its own layout profile"),
                        (wrong_scheme, f"files in a scheme folder other than {scheme}"),
                        (strays, "files a theme package does not have")):
        if found:
            problems.append(f"{what}: {', '.join(found[:3])}")
    for required in (template, "LICENSE", "README.md", "CHANGELOG.md") + ((own_layout,) if own_layout else ()):
        if required not in names:
            problems.append(f"no {required} in the asset")
    return problems


def inspect_theme(data: bytes, tid: str, version: str) -> tuple[dict | None, list[str]]:
    """The theme.toml of a downloaded .smtheme, or the problems that refuse it."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None, ["the asset is not a zip file"]
    if "theme.toml" not in archive.namelist():
        return None, ["no theme.toml at the root of the asset"]
    try:
        manifest = tomllib.loads(archive.read("theme.toml").decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, [f"theme.toml does not parse: {exc}"]
    layout = manifest.get("layout")
    problems = (check_theme_manifest(manifest, tid, version)
                + check_theme_members(archive, tid, layout if isinstance(layout, str) else None))
    return (None if problems else manifest), problems


def theme_preview(data: bytes, tid: str, version: str, report: Report) -> bytes | None:
    """preview.png from inside a .smtheme; None when there is none or it cannot be used."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if "preview.png" not in archive.namelist():
            return None
        info = archive.getinfo("preview.png")
        picture = archive.read(info) if info.file_size <= PREVIEW_BYTES else b""
    if picture[:8] != PNG:
        report.add("refused", f"theme {tid}", version, "preview.png is not a PNG of at most 1 MB; no preview")
        return None
    return picture


class Kind(NamedTuple):
    """What differs between listing a plugin and a theme."""
    prefix: str         # in front of the id where problems are reported
    suffix: str         # of the release asset
    inspect: object     # (data, id, version) -> (manifest | None, problems)
    keys: tuple         # the manifest fields a pin keeps


PLUGIN = Kind("", ".smplugin", inspect_asset, MANIFEST_KEYS)
THEME = Kind("theme ", ".smtheme", inspect_theme, THEME_MANIFEST_KEYS)


def check_icon(path: str, data: bytes) -> str | None:
    """Why an icon cannot be used; None when it can."""
    if path.endswith(".svg"):
        text = data.decode("utf-8", "replace")
        if "<svg" not in text:
            return "icon.svg is not an SVG"
        if SVG_ACTIVE.search(text):
            return "icon.svg contains scripts or event handlers"
        return None
    if data[:8] != PNG or len(data) < 24:
        return "icon.png is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    if width != height or width < 128:
        return f"icon.png must be square and at least 128 px, it is {width}x{height}"
    return None


def list_releases(entry: dict, releases: list[dict], gh: GitHub, pins: dict, today: str, full_check: bool,
                  report: Report, kind: Kind = PLUGIN, previews: dict | None = None) -> list[tuple[dict, dict]]:
    """(catalogue release, GitHub release) for every release of one plugin (or theme) that can be listed, newest
    first. Pins new versions into pins[id]; for a theme previews[version] gets the preview.png of each new one."""
    pid, who = entry["id"], f"{kind.prefix}{entry['id']}"
    plugin_pins = pins.setdefault(pid, {})
    approved = entry.get("releases", "all")
    listed = []
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name", "")
        match = TAG_RE.match(tag)
        if not match:
            report.add("refused", who, tag, "the tag is not v<MAJOR.MINOR.PATCH>")
            continue
        version = match.group(1)
        if (approved != "all" and version not in approved) or version in entry.get("yanked", []):
            continue
        name = f"{pid}-{version}{kind.suffix}"
        assets = {asset["name"]: asset for asset in release.get("assets", [])}
        if name not in assets:
            report.add("refused", who, version, f"no asset named {name}")
            continue
        extra = sorted(set(assets) - {name, f"{name}.sha256"})
        if extra:
            report.add("refused", who, version, f"assets besides {name} and its .sha256: {', '.join(extra)}")
            continue
        asset, pin = assets[name], plugin_pins.get(version)
        if pin is None:
            pin = pin_new(entry, version, release, assets, gh, today, report, kind, previews)
            if pin is None:
                continue
            plugin_pins[version] = pin
        else:
            if asset.get("size") != pin["size"]:
                report.add("changed", who, version,
                           f"the asset's size changed from {pin['size']} to {asset.get('size')} bytes")
                continue
            if full_check:
                try:
                    digest = hashlib.sha256(gh.download(asset["browser_download_url"])).hexdigest()
                except NETWORK_ERRORS as exc:
                    report.add("error", who, version, f"could not re-check the asset: {exc}")
                else:
                    if digest != pin["sha256"]:
                        report.add("changed", who, version, f"the asset's SHA-256 changed from {pin['sha256']} "
                                                            f"to {digest}")
                        continue
        manifest = pin["manifest"]
        listed.append(({
            "version": version,
            **({"api_version": manifest["api_version"]} if "api_version" in manifest else {}),
            "requires_slidemage": manifest["requires_slidemage"],
            "url": asset["browser_download_url"],
            "sha256": pin["sha256"],
            "size": pin["size"],
            "published": pin["published"],
            "notes_url": release["html_url"],
        }, release))
    listed.sort(key=lambda pair: version_key(pair[0]["version"]), reverse=True)
    return listed


def pin_new(entry: dict, version: str, release: dict, assets: dict, gh: GitHub, today: str,
            report: Report, kind: Kind = PLUGIN, previews: dict | None = None) -> dict | None:
    """Download, check and pin a version seen for the first time; None when it is refused."""
    pid, who = entry["id"], f"{kind.prefix}{entry['id']}"
    name = f"{pid}-{version}{kind.suffix}"
    for required in ("README.md", "CHANGELOG.md"):
        try:
            present = gh.file_at(entry["repository"], release["tag_name"], required) is not None
        except NETWORK_ERRORS as exc:
            report.add("error", who, version, f"could not read {required}: {exc}")
            return None
        if not present:
            report.add("refused", who, version, f"no {required} at the tag")
            return None
    try:
        data = gh.download(assets[name]["browser_download_url"])
    except NETWORK_ERRORS as exc:
        report.add("error", who, version, f"could not download the asset: {exc}")
        return None
    digest = hashlib.sha256(data).hexdigest()
    if f"{name}.sha256" in assets:
        try:
            expected = gh.download(assets[f"{name}.sha256"]["browser_download_url"]).decode("ascii").split()[0]
        except NETWORK_ERRORS as exc:
            report.add("error", who, version, f"could not download the .sha256 asset: {exc}")
            return None
        except (UnicodeDecodeError, IndexError):
            report.add("refused", who, version, "the .sha256 asset is not a hash")
            return None
        if expected.lower() != digest:
            report.add("refused", who, version, f"the .sha256 asset says {expected}, the asset hashes to {digest}")
            return None
    manifest, problems = kind.inspect(data, pid, version)
    if problems:
        report.add("refused", who, version, "; ".join(problems))
        return None
    if previews is not None:
        previews[version] = theme_preview(data, pid, version, report)
    return {"sha256": digest, "size": len(data), "published": release["published_at"][:10], "first_seen": today,
            "manifest": {key: manifest[key] for key in kind.keys}}


def fetch_icon(entry: dict, tag: str, gh: GitHub, report: Report) -> tuple[str, bytes] | None | bool:
    """(extension, bytes) of the plugin's icon at the tag; None for none; False when GitHub could not be read."""
    for path in ICONS:
        try:
            data = gh.file_at(entry["repository"], tag, path)
        except NETWORK_ERRORS as exc:
            report.add("error", entry["id"], None, f"could not read {path}: {exc}")
            return False
        if data is None:
            continue
        problem = check_icon(path, data)
        if problem:
            report.add("refused", entry["id"], tag, f"{problem}; the generic icon is used")
            return None
        return path.rsplit(".", 1)[1], data
    return None


def fetch_material(entry: dict, tag: str, gh: GitHub, report: Report) -> dict | bool:
    """README, CHANGELOG and screenshots at the tag, for the plugin's page; False when GitHub could not be read."""
    repo, pid = entry["repository"], entry["id"]
    try:
        readme = gh.file_at(repo, tag, "README.md") or b""
        log = gh.file_at(repo, tag, "CHANGELOG.md") or b""
        listing = gh.list_dir(repo, tag, "website/screenshots")
    except NETWORK_ERRORS as exc:
        report.add("error", pid, None, f"could not read the website material: {exc}; the page is kept")
        return False
    shots = []
    for item in sorted((item for item in listing if item["name"].lower().endswith(".png")),
                       key=lambda item: item["name"]):
        if len(shots) == SCREENSHOTS:
            report.add("refused", pid, tag, f"more than {SCREENSHOTS} screenshots; the rest are left out")
            break
        if item["size"] > SCREENSHOT_BYTES:
            report.add("refused", pid, tag, f"screenshot {item['name']} is larger than 1 MB")
            continue
        try:
            data = gh.file_at(repo, tag, f"website/screenshots/{item['name']}")
        except NETWORK_ERRORS as exc:
            report.add("error", pid, None, f"could not read a screenshot: {exc}; the page is kept")
            return False
        if not data or data[:8] != PNG:
            report.add("refused", pid, tag, f"screenshot {item['name']} is not a PNG")
            continue
        shots.append((re.sub(r"[^A-Za-z0-9._-]", "-", item["name"]), data))
    return {"tag": tag, "readme": readme.decode("utf-8", "replace"), "changelog": log.decode("utf-8", "replace"),
            "screenshots": shots}


def build(registry: list[dict], gh: GitHub, pins: dict, previous: dict[str, dict], site_url: str, today: str,
          full_check: bool, report: Report) -> tuple[list[dict], dict, dict]:
    """Catalogue entries for every registry plugin with a listable release (hidden ones carry "_hidden"), the
    icons to write: {id: (extension, bytes) | None (none) | False (keep what is there)}, and the listed plugins'
    page material: {id: material | False (keep the page)}."""
    plugins, icons, materials = [], {}, {}
    for entry in registry:
        pid = entry["id"]
        try:
            releases = gh.releases(entry["repository"])
        except NETWORK_ERRORS as exc:
            report.add("error", pid, None, f"could not list releases: {exc}; the previous entry is kept")
            if pid in previous:
                plugins.append({**previous[pid], "_hidden": entry.get("hidden", False),
                                "_repository": entry["repository"]})
                icons[pid] = materials[pid] = False
            continue
        listed = list_releases(entry, releases, gh, pins, today, full_check, report)
        if not listed:
            report.add("error", pid, None, "no release can be listed")
            continue
        newest_tag = listed[0][1]["tag_name"]
        manifest = pins[pid][listed[0][0]["version"]]["manifest"]
        plugin = {
            "id": pid,
            "name": manifest["name"],
            "summary": manifest["summary"],
            "homepage": f"{site_url}plugins/{pid}/",
            "source": f"https://github.com/{entry['repository']}",
            "license": manifest["license"],
            "maintainer": entry["maintainer"],
            "recommended": entry.get("recommended", False),
            "needs": manifest["needs"],
            "network": manifest["network"],
            "releases": [release for release, _ in listed],
            "_hidden": entry.get("hidden", False),
            "_repository": entry["repository"],
        }
        icon = fetch_icon(entry, newest_tag, gh, report)
        icons[pid] = icon
        if icon is False and "icon" in previous.get(pid, {}):
            plugin["icon"] = previous[pid]["icon"]
        elif icon:
            plugin["icon"] = f"{site_url}plugins/{pid}/icon.{icon[0]}"
        if not plugin["_hidden"]:
            materials[pid] = fetch_material(entry, newest_tag, gh, report)
        plugins.append(plugin)
    plugins.sort(key=lambda plugin: (not plugin["recommended"], plugin["name"].lower()))
    return plugins, icons, materials


def build_themes(registry: list[dict], gh: GitHub, pins: dict, previous: dict[str, dict], site_url: str,
                 today: str, full_check: bool, report: Report) -> tuple[list[dict], dict]:
    """Catalogue entries for every registry theme with a listable release (hidden ones carry "_hidden"), and the
    previews to write: {id: bytes | None (none) | False (keep what is there)}. A preview is read from a package
    only when its version is pinned, so the newest version's preview stays until a newer one replaces it."""
    themes, previews = [], {}
    for entry in registry:
        tid, who = entry["id"], f"theme {entry['id']}"
        try:
            releases = gh.releases(entry["repository"])
        except NETWORK_ERRORS as exc:
            report.add("error", who, None, f"could not list releases: {exc}; the previous entry is kept")
            if tid in previous:
                themes.append({**previous[tid], "_hidden": entry.get("hidden", False)})
                previews[tid] = False
            continue
        found = {}
        listed = list_releases(entry, releases, gh, pins, today, full_check, report, THEME, found)
        if not listed:
            report.add("error", who, None, "no release can be listed")
            continue
        newest = listed[0][0]["version"]
        manifest = pins[tid][newest]["manifest"]
        theme = {
            "id": tid,
            "name": manifest["name"],
            "summary": manifest["summary"],
            "homepage": f"{site_url}themes/{tid}/",
            "source": f"https://github.com/{entry['repository']}",
            "license": manifest["license"],
            "maintainer": entry["maintainer"],
            "recommended": entry.get("recommended", False),
            "layout": manifest["layout"],
            "releases": [release for release, _ in listed],
            "_hidden": entry.get("hidden", False),
        }
        previews[tid] = found.get(newest, False)
        if previews[tid] is False and "preview" in previous.get(tid, {}):
            theme["preview"] = previous[tid]["preview"]
        elif previews[tid]:
            theme["preview"] = f"{site_url}themes/{tid}/preview.png"
        themes.append(theme)
    themes.sort(key=lambda theme: (not theme["recommended"], theme["name"].lower()))
    return themes, previews


def catalogue(plugins: list[dict], site_url: str, now: str, hidden: bool, themes: list[dict] = ()) -> dict:
    keys = ("id", "name", "summary", "homepage", "source", "icon", "license", "maintainer", "recommended",
            "needs", "network", "releases")
    theme_keys = ("id", "name", "summary", "homepage", "source", "preview", "license", "maintainer", "recommended",
                  "layout", "releases")
    doc = {
        "schema": 1,
        "generated": now,
        "plugins_page": f"{site_url}plugins/",
        "plugins": [{key: plugin[key] for key in keys if key in plugin}
                    for plugin in plugins if hidden or not plugin["_hidden"]],
    }
    shown = [{key: theme[key] for key in theme_keys if key in theme}
             for theme in themes if hidden or not theme["_hidden"]]
    if shown:   # no "themes" key until there is a theme to list
        doc["themes"] = shown
    return doc


def validate(doc: dict) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker())
    return [f"{'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
            for error in validator.iter_errors(doc)]


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def write_catalogue(path: Path, doc: dict) -> bool:
    """Write the catalogue unless only "generated" would change, so a run without news commits nothing."""
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if {**old, "generated": None} == {**doc, "generated": None}:
            return False
    return write_if_changed(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def write_icons(icons: dict, keep: set[str]) -> None:
    for pid, icon in icons.items():
        if icon is False:
            continue
        for old in (OUT / pid).glob("icon.*"):
            if not icon or old.suffix != f".{icon[0]}":
                old.unlink()
        if icon:
            path = OUT / pid / f"icon.{icon[0]}"
            if not path.exists() or path.read_bytes() != icon[1]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(icon[1])
    for folder in OUT.iterdir():
        if folder.is_dir() and folder.name not in keep:
            for old in folder.glob("icon.*"):
                old.unlink()


def write_previews(previews: dict, keep: set[str]) -> None:
    """Copy the themes' previews to docs/themes/<id>/preview.png; previews of themes no longer in the catalogue
    go. Touches nothing without a theme."""
    for tid, picture in previews.items():
        path = THEME_OUT / tid / "preview.png"
        if picture is False:
            continue
        if not picture:
            path.unlink(missing_ok=True)
        elif not path.exists() or path.read_bytes() != picture:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(picture)
    if THEME_OUT.exists():
        for folder in THEME_OUT.iterdir():
            if folder.is_dir() and folder.name not in keep:
                (folder / "preview.png").unlink(missing_ok=True)


def write_pages(plugins: list[dict], materials: dict) -> None:
    """The listed plugins' pages and screenshots, the cards on /plugins/; pages of plugins no longer listed go."""
    listed = [plugin for plugin in plugins if not plugin["_hidden"]]
    for plugin in listed:
        material = materials.get(plugin["id"])
        if not material:
            continue
        folder = OUT / plugin["id"]
        write_if_changed(folder / "index.md", pages.page(plugin, material, plugin["_repository"]))
        shots = dict(material["screenshots"])
        for old in (folder / "screenshots").glob("*"):
            if old.name not in shots:
                old.unlink()
        for name, data in shots.items():
            path = folder / "screenshots" / name
            if not path.exists() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    names = {plugin["id"] for plugin in listed}
    for folder in OUT.iterdir():
        if folder.is_dir() and folder.name not in names:
            (folder / "index.md").unlink(missing_ok=True)
            for old in (folder / "screenshots").glob("*"):
                old.unlink()
    index = OUT / "index.md"
    write_if_changed(index, pages.replace_cards(index.read_text(encoding="utf-8"), pages.cards(listed)))


def site_url() -> str:
    match = re.search(r"^site_url:\s*(\S+)", MKDOCS.read_text(encoding="utf-8"), re.MULTILINE)
    if not match or not match.group(1).startswith("https://"):
        raise RegistryError("mkdocs.yml has no https site_url")
    return match.group(1).rstrip("/") + "/"


def previous_entries(key: str = "plugins") -> dict[str, dict]:
    path = OUT / "index-test.json"
    if not path.exists():
        return {}
    return {entry["id"]: entry for entry in json.loads(path.read_text(encoding="utf-8")).get(key, [])}


def summary(report: Report, plugins: list[dict], themes: list[dict] = ()) -> str:
    lines = ["## Plugin catalogue", ""]
    for plugin in plugins:
        hidden = " (hidden)" if plugin["_hidden"] else ""
        lines.append(f"- **{plugin['id']}**{hidden}: {', '.join(r['version'] for r in plugin['releases'])}")
    if themes:
        lines += ["", "### Themes", ""]
        for theme in themes:
            hidden = " (hidden)" if theme["_hidden"] else ""
            lines.append(f"- **{theme['id']}**{hidden}: {', '.join(r['version'] for r in theme['releases'])}")
    if report.problems:
        lines += ["", "### Problems", ""]
        lines += [f"- {p['kind']}: {p['plugin']} {p['version'] or ''}: {p['message']}" for p in report.problems]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, gh: GitHub | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="build and validate, write nothing")
    parser.add_argument("--full-check", action="store_true", help="re-hash every pinned asset")
    parser.add_argument("--report", type=Path, help="write the problems found to this JSON file")
    args = parser.parse_args(argv)

    gh = gh or GitHub(os.environ.get("GITHUB_TOKEN"))
    report = Report()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    try:
        registry = load_registry(REGISTRY.read_text(encoding="utf-8"))
        theme_registry = load_registry(REGISTRY.read_text(encoding="utf-8"), "theme")
        base = site_url()
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    pins = json.loads(PINS.read_text(encoding="utf-8")) if PINS.exists() else {}
    theme_pins = json.loads(THEME_PINS.read_text(encoding="utf-8")) if THEME_PINS.exists() else {}
    plugins, icons, materials = build(registry, gh, pins, previous_entries(), base, now.date().isoformat(),
                                      args.full_check, report)
    themes, previews = build_themes(theme_registry, gh, theme_pins, previous_entries("themes"), base,
                                    now.date().isoformat(), args.full_check, report)
    stamp = now.isoformat().replace("+00:00", "Z")
    public, test = catalogue(plugins, base, stamp, False, themes), catalogue(plugins, base, stamp, True, themes)
    invalid = validate(public) + validate(test)

    if args.report:
        args.report.write_text(json.dumps({"problems": report.problems}, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary(report, plugins, themes))
    if invalid:
        print("error: the catalogue does not match the schema:\n  " + "\n  ".join(invalid), file=sys.stderr)
        return 1
    if args.check:
        listed = {plugin["id"] for plugin in plugins}
        missing = [entry["id"] for entry in registry if entry["id"] not in listed]
        listed_themes = {theme["id"] for theme in themes}
        missing += [f"theme {entry['id']}" for entry in theme_registry if entry["id"] not in listed_themes]
        if missing:
            print(f"error: no listable release for {', '.join(missing)}", file=sys.stderr)
            return 1
        return 0

    write_if_changed(PINS, json.dumps(pins, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    if any(theme_pins.values()) or THEME_PINS.exists():   # created only when there is something to pin
        write_if_changed(THEME_PINS, json.dumps(theme_pins, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    write_catalogue(OUT / "index.json", public)
    write_catalogue(OUT / "index-test.json", test)
    write_icons(icons, {plugin["id"] for plugin in plugins})
    write_pages(plugins, materials)
    write_previews(previews, {theme["id"] for theme in themes})
    write_if_changed(HEARTBEAT, f"{now:%Y-%m}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
