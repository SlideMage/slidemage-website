"""Build the plugin catalogue from registry/plugins.toml.

Writes docs/plugins/index.json (listed plugins) and docs/plugins/index-test.json (listed and hidden ones),
pins every published asset's SHA-256 in catalogue/pins.json, copies plugin icons to docs/plugins/<id>/ and
keeps catalogue/last-run.txt as a monthly heartbeat. One plugin's problems never block the others.

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

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "plugins.toml"
SCHEMA = ROOT / "schema" / "plugins-index.schema.json"
PINS = ROOT / "catalogue" / "pins.json"
HEARTBEAT = ROOT / "catalogue" / "last-run.txt"
OUT = ROOT / "docs" / "plugins"
MKDOCS = ROOT / "mkdocs.yml"

ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
RANGE_RE = re.compile(r"^(>=|<=|==|<|>)\s*\d+(\.\d+){0,2}(\s*,\s*(>=|<=|==|<|>)\s*\d+(\.\d+){0,2})*$")
REPO_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
COMPILED = (".pyc", ".pyo", ".so", ".pyd", ".dll", ".dylib", ".exe")
ICONS = ("website/icon.svg", "website/icon.png")
SVG_ACTIVE = re.compile(r"<script|\bon[a-z]+\s*=|javascript:|<foreignObject", re.IGNORECASE)
REGISTRY_KEYS = {"id", "repository", "maintainer", "recommended", "releases", "yanked", "hidden"}
MANIFEST_KEYS = ("name", "summary", "license", "needs", "network", "api_version", "requires_slidemage")
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


def load_registry(text: str) -> list[dict]:
    try:
        entries = tomllib.loads(text).get("plugin", [])
    except tomllib.TOMLDecodeError as exc:
        raise RegistryError(f"registry does not parse: {exc}") from exc
    seen = set()
    for entry in entries:
        pid = entry.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            raise RegistryError(f"invalid id {pid!r}")
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


def check_manifest(manifest: dict, pid: str, version: str) -> list[str]:
    """What is wrong with a plugin.toml; empty when nothing is."""
    problems = []

    def text(key, longest):
        value = manifest.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= longest:
            problems.append(f"{key} must be text of 1 to {longest} characters")

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


def check_icon(path: str, data: bytes) -> str | None:
    """Why an icon cannot be used; None when it can."""
    if path.endswith(".svg"):
        text = data.decode("utf-8", "replace")
        if "<svg" not in text:
            return "icon.svg is not an SVG"
        if SVG_ACTIVE.search(text):
            return "icon.svg contains scripts or event handlers"
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return "icon.png is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    if width != height or width < 128:
        return f"icon.png must be square and at least 128 px, it is {width}x{height}"
    return None


def list_releases(entry: dict, releases: list[dict], gh: GitHub, pins: dict, today: str, full_check: bool,
                  report: Report) -> list[tuple[dict, dict]]:
    """(catalogue release, GitHub release) for every release of one plugin that can be listed, newest first.
    Pins new versions into pins[id]."""
    pid = entry["id"]
    plugin_pins = pins.setdefault(pid, {})
    approved = entry.get("releases", "all")
    listed = []
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name", "")
        match = TAG_RE.match(tag)
        if not match:
            report.add("refused", pid, tag, "the tag is not v<MAJOR.MINOR.PATCH>")
            continue
        version = match.group(1)
        if (approved != "all" and version not in approved) or version in entry.get("yanked", []):
            continue
        name = f"{pid}-{version}.smplugin"
        assets = {asset["name"]: asset for asset in release.get("assets", [])}
        if name not in assets:
            report.add("refused", pid, version, f"no asset named {name}")
            continue
        extra = sorted(set(assets) - {name, f"{name}.sha256"})
        if extra:
            report.add("refused", pid, version, f"assets besides {name} and its .sha256: {', '.join(extra)}")
            continue
        asset, pin = assets[name], plugin_pins.get(version)
        if pin is None:
            pin = pin_new(pid, version, release, assets, gh, today, report)
            if pin is None:
                continue
            plugin_pins[version] = pin
        else:
            if asset.get("size") != pin["size"]:
                report.add("changed", pid, version,
                           f"the asset's size changed from {pin['size']} to {asset.get('size')} bytes")
                continue
            if full_check:
                try:
                    digest = hashlib.sha256(gh.download(asset["browser_download_url"])).hexdigest()
                except NETWORK_ERRORS as exc:
                    report.add("error", pid, version, f"could not re-check the asset: {exc}")
                else:
                    if digest != pin["sha256"]:
                        report.add("changed", pid, version, f"the asset's SHA-256 changed from {pin['sha256']} "
                                                            f"to {digest}")
                        continue
        manifest = pin["manifest"]
        listed.append(({
            "version": version,
            "api_version": manifest["api_version"],
            "requires_slidemage": manifest["requires_slidemage"],
            "url": asset["browser_download_url"],
            "sha256": pin["sha256"],
            "size": pin["size"],
            "published": pin["published"],
            "notes_url": release["html_url"],
        }, release))
    listed.sort(key=lambda pair: version_key(pair[0]["version"]), reverse=True)
    return listed


def pin_new(pid: str, version: str, release: dict, assets: dict, gh: GitHub, today: str,
            report: Report) -> dict | None:
    """Download, check and pin a version seen for the first time; None when it is refused."""
    name = f"{pid}-{version}.smplugin"
    try:
        data = gh.download(assets[name]["browser_download_url"])
    except NETWORK_ERRORS as exc:
        report.add("error", pid, version, f"could not download the asset: {exc}")
        return None
    digest = hashlib.sha256(data).hexdigest()
    if f"{name}.sha256" in assets:
        try:
            expected = gh.download(assets[f"{name}.sha256"]["browser_download_url"]).decode("ascii").split()[0]
        except NETWORK_ERRORS as exc:
            report.add("error", pid, version, f"could not download the .sha256 asset: {exc}")
            return None
        except (UnicodeDecodeError, IndexError):
            report.add("refused", pid, version, "the .sha256 asset is not a hash")
            return None
        if expected.lower() != digest:
            report.add("refused", pid, version, f"the .sha256 asset says {expected}, the asset hashes to {digest}")
            return None
    manifest, problems = inspect_asset(data, pid, version)
    if problems:
        report.add("refused", pid, version, "; ".join(problems))
        return None
    return {"sha256": digest, "size": len(data), "published": release["published_at"][:10], "first_seen": today,
            "manifest": {key: manifest[key] for key in MANIFEST_KEYS}}


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


def build(registry: list[dict], gh: GitHub, pins: dict, previous: dict[str, dict], site_url: str, today: str,
          full_check: bool, report: Report) -> tuple[list[dict], dict]:
    """Catalogue entries for every registry plugin with a listable release (hidden ones carry "_hidden"), and
    the icons to write: {id: (extension, bytes) | None (none) | False (keep what is there)}."""
    plugins, icons = [], {}
    for entry in registry:
        pid = entry["id"]
        try:
            releases = gh.releases(entry["repository"])
        except NETWORK_ERRORS as exc:
            report.add("error", pid, None, f"could not list releases: {exc}; the previous entry is kept")
            if pid in previous:
                plugins.append({**previous[pid], "_hidden": entry.get("hidden", False)})
                icons[pid] = False
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
        }
        icon = fetch_icon(entry, newest_tag, gh, report)
        icons[pid] = icon
        if icon is False and "icon" in previous.get(pid, {}):
            plugin["icon"] = previous[pid]["icon"]
        elif icon:
            plugin["icon"] = f"{site_url}plugins/{pid}/icon.{icon[0]}"
        plugins.append(plugin)
    plugins.sort(key=lambda plugin: (not plugin["recommended"], plugin["name"].lower()))
    return plugins, icons


def catalogue(plugins: list[dict], site_url: str, now: str, hidden: bool) -> dict:
    keys = ("id", "name", "summary", "homepage", "source", "icon", "license", "maintainer", "recommended",
            "needs", "network", "releases")
    return {
        "schema": 1,
        "generated": now,
        "plugins_page": f"{site_url}plugins/",
        "plugins": [{key: plugin[key] for key in keys if key in plugin}
                    for plugin in plugins if hidden or not plugin["_hidden"]],
    }


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


def site_url() -> str:
    match = re.search(r"^site_url:\s*(\S+)", MKDOCS.read_text(encoding="utf-8"), re.MULTILINE)
    if not match or not match.group(1).startswith("https://"):
        raise RegistryError("mkdocs.yml has no https site_url")
    return match.group(1).rstrip("/") + "/"


def previous_entries() -> dict[str, dict]:
    path = OUT / "index-test.json"
    if not path.exists():
        return {}
    return {plugin["id"]: plugin for plugin in json.loads(path.read_text(encoding="utf-8"))["plugins"]}


def summary(report: Report, plugins: list[dict]) -> str:
    lines = ["## Plugin catalogue", ""]
    for plugin in plugins:
        hidden = " (hidden)" if plugin["_hidden"] else ""
        lines.append(f"- **{plugin['id']}**{hidden}: {', '.join(r['version'] for r in plugin['releases'])}")
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
        base = site_url()
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    pins = json.loads(PINS.read_text(encoding="utf-8")) if PINS.exists() else {}
    plugins, icons = build(registry, gh, pins, previous_entries(), base, now.date().isoformat(),
                           args.full_check, report)
    stamp = now.isoformat().replace("+00:00", "Z")
    public, test = catalogue(plugins, base, stamp, False), catalogue(plugins, base, stamp, True)
    invalid = validate(public) + validate(test)

    if args.report:
        args.report.write_text(json.dumps({"problems": report.problems}, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary(report, plugins))
    if invalid:
        print("error: the catalogue does not match the schema:\n  " + "\n  ".join(invalid), file=sys.stderr)
        return 1
    if args.check:
        listed = {plugin["id"] for plugin in plugins}
        missing = [entry["id"] for entry in registry if entry["id"] not in listed]
        if missing:
            print(f"error: no listable release for {', '.join(missing)}", file=sys.stderr)
            return 1
        return 0

    write_if_changed(PINS, json.dumps(pins, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    write_catalogue(OUT / "index.json", public)
    write_catalogue(OUT / "index-test.json", test)
    write_icons(icons, {plugin["id"] for plugin in plugins})
    write_if_changed(HEARTBEAT, f"{now:%Y-%m}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
