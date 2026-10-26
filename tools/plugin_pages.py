"""Plugin pages (/plugins/<id>/) and the cards on /plugins/, from the catalogue and each plugin's website
material: README.md, CHANGELOG.md and website/screenshots/ at the newest listed release.

Plugin texts are third-party content rendered on this site, so they are defused before they reach MkDocs:
raw HTML and attribute lists are escaped, links other than http(s), mailto and in-page anchors are removed,
relative links point to the plugin's repository at the tag, and images become their alt text (screenshots come
from website/screenshots/ only).
"""
from __future__ import annotations

import re

CUT_HEADINGS = re.compile(r"^##\s+(development|building|contributing)\s*#*\s*$", re.IGNORECASE)
FENCE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})\s*([\w+-]*)")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]*)([^)]*)\)")
REFERENCE = re.compile(r"^(\s{0,3}\[[^\]]+\]:\s*)(\S+)(.*)$")
ENTRY = re.compile(r"^(v\d+\.\d+\.\d+) \(([^,)]*)(?:,\s*([^)]*))?\):\s*(.*)$")
CARDS_START, CARDS_END = "<!-- catalogue:cards:start -->", "<!-- catalogue:cards:end -->"
NO_PLUGINS = """!!! note "No plugins listed yet"
    The first plugins are in preparation: **Ollama** (local AI models), **Claude** (AI in the cloud) and
    **CampusOnline** (course links and admin slides for CAMPUSonline courses). They'll be listed here once
    they're released."""


def inline(text: str) -> str:
    """Plain text from plugin.toml as Markdown that shows exactly that text."""
    text = re.sub(r"([\\`*_\[\]|!])", r"\\\1", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.replace("{", "&#123;").replace("}", "&#125;")


def _url(url: str, repo: str, tag: str) -> str | None:
    """A link target that is safe here, or None to drop the link."""
    if url.startswith(("https://", "http://", "mailto:", "#")):
        return url
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) or url.startswith("//"):
        return None
    return f"https://github.com/{repo}/blob/{tag}/{url.lstrip('./')}"


def _prose(text: str, repo: str, tag: str) -> str:
    text = text.replace("<", "&lt;").replace(">", "&gt;").replace("{", "&#123;").replace("}", "&#125;")
    text = IMAGE.sub(lambda m: f"*{m.group(1)}*" if m.group(1).strip() else "", text)

    def link(match):
        target = _url(match.group(2), repo, tag)
        return match.group(1) if target is None else f"[{match.group(1)}]({target}{match.group(3)})"
    return LINK.sub(link, text)


def defuse(markdown: str, repo: str, tag: str) -> str:
    """Third-party Markdown made safe to render; headings one level down from #."""
    out, fence = [], None
    for line in markdown.splitlines():
        match = FENCE.match(line)
        if fence is None and match:
            fence = match.group(2)[0] * 3
            out.append(f"{match.group(1)}{match.group(2)}{match.group(3)}")   # no attributes on the fence
            continue
        if fence is not None:
            out.append(line)
            if line.strip().startswith(fence) and not line.strip().strip(fence[0]):
                fence = None
            continue
        reference = REFERENCE.match(line)
        if reference:
            target = _url(reference.group(2), repo, tag)
            out.append(f"{reference.group(1)}{target}{reference.group(3)}" if target else "")
            continue
        if line.startswith("# "):
            line = "#" + line
        pieces, last = [], 0
        for code in CODE_SPAN.finditer(line):
            pieces.append(_prose(line[last:code.start()], repo, tag))
            pieces.append(code.group(0))
            last = code.end()
        pieces.append(_prose(line[last:], repo, tag))
        out.append("".join(pieces))
    if fence is not None:
        out.append(fence)
    return "\n".join(out).strip()


def readme_body(readme: str) -> str:
    """The README from after its first heading to the first ## Development, Building or Contributing."""
    lines = readme.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if line.startswith("#")), 0)
    body = []
    for line in lines[start:]:
        if CUT_HEADINGS.match(line):
            break
        body.append(line)
    return "\n".join(body).strip()


def changelog(text: str, repo: str, tag: str) -> str:
    """CHANGELOG.md in SlideMage's format (vX.Y.Z (date, reason): text), newest first."""
    entries, current = [], None
    for line in text.splitlines():
        match = ENTRY.match(line)
        if match:
            current = [match.groups(), []]
            entries.append(current)
        elif current is not None:
            current[1].append(line)
    if not entries:
        body = "\n".join(line for line in text.splitlines() if not line.startswith("# "))
        return defuse(re.sub(r"^#", "##", body, flags=re.MULTILINE), repo, tag)
    blocks = []
    for (version, date, reason, first), rest in reversed(entries):
        when = " · ".join(inline(part) for part in (date, reason) if part)
        text = defuse("\n".join([first, *rest]), repo, tag)
        blocks.append(f"### {version}\n\n*{when}*\n\n{text}")
    return "\n\n".join(blocks)


def _range(text: str) -> str:
    return inline(text).replace(",", ", ").replace("  ", " ")


def _icon(plugin: dict, prefix: str, width: int) -> str:
    if "icon" not in plugin:
        return ""
    return f'![]({prefix}icon.{plugin["icon"].rsplit(".", 1)[1]}){{ width="{width}" }} '


def page(plugin: dict, material: dict, repo: str) -> str:
    """The Markdown of /plugins/<id>/."""
    tag, newest = material["tag"], plugin["releases"][0]
    name = inline(plugin["name"])
    lines = [f"# {name}", "", f"{_icon(plugin, '', 64)}{inline(plugin['summary'])}", ""]
    if plugin["network"]:
        lines += ['!!! info "What leaves your computer"', "    This plugin contacts:", ""]
        lines += [f"    - {inline(item)}" for item in plugin["network"]]
    else:
        lines += ['!!! success "Nothing leaves your computer"', "    This plugin contacts no network service."]
    lines += ["", "## Requirements", ""]
    lines += [f"- {inline(item)}" for item in plugin["needs"]] or ["Nothing beyond SlideMage."]
    lines += ["", f"Works with SlideMage {_range(newest['requires_slidemage'])}.", "", "## Installing", "",
              "In SlideMage: **Settings → Plugins** or **Help → Plugins…**.", "",
              f"By hand: download [{name} {newest['version']}]({newest['url']}) "
              f"({max(1, round(newest['size'] / 1024))} kB), then choose "
              "**Settings → Plugins → Install from file…**."]
    body = defuse(readme_body(material["readme"]), repo, tag)
    if body:
        lines += ["", "## About this plugin", "", body]
    if material["screenshots"]:
        lines += ["", "## Screenshots", ""]
        lines += [f"![{name} screenshot {i}](screenshots/{file}){{ loading=lazy }}\n"
                  for i, (file, _) in enumerate(material["screenshots"], 1)]
    lines += ["", "## Versions", "", "| Version | SlideMage | Released | Download |", "|---|---|---|---|"]
    for release in plugin["releases"]:
        notes = f" · [notes]({release['notes_url']})" if release.get("notes_url") else ""
        lines.append(f"| {release['version']} | {_range(release['requires_slidemage'])} | {release['published']} "
                     f"| [.smplugin]({release['url']}){notes} |")
    log = changelog(material["changelog"], repo, tag)
    if log:
        lines += ["", "## Changelog", "", log]
    lines += ["", "---", "",
              f"Maintained by {inline(plugin['maintainer'])} · License {inline(plugin['license'])} · "
              f"[Source]({plugin['source']})", ""]
    return "\n".join(lines)


def cards(plugins: list[dict]) -> str:
    """The cards on /plugins/ for the listed plugins, recommended first as the catalogue orders them."""
    if not plugins:
        return NO_PLUGINS
    out = ['<div class="grid cards" markdown>', ""]
    for plugin in plugins:
        newest = plugin["releases"][0]
        recommended = " · *Recommended*" if plugin["recommended"] else ""
        needs = "; ".join(inline(item) for item in plugin["needs"]) or "nothing beyond SlideMage"
        network = "; ".join(inline(item) for item in plugin["network"]) or "none, nothing leaves your computer"
        out += [f"-   {_icon(plugin, plugin['id'] + '/', 40)}**[{inline(plugin['name'])}]({plugin['id']}/index.md)**"
                f"{recommended}", "",
                f"    {inline(plugin['summary'])}", "",
                f"    **Needs:** {needs}  ",
                f"    **Contacts:** {network}", "",
                f"    Version {newest['version']} · SlideMage {_range(newest['requires_slidemage'])} · "
                f"by {inline(plugin['maintainer'])}", ""]
    out.append("</div>")
    return "\n".join(out)


def replace_cards(index_md: str, block: str) -> str:
    start, end = index_md.index(CARDS_START) + len(CARDS_START), index_md.index(CARDS_END)
    return f"{index_md[:start]}\n{block}\n{index_md[end:]}"
