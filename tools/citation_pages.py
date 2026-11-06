"""Citation format pages (/citations/<id>/) and the cards on /citations/, from the catalogue and each format's
README.md and CHANGELOG.md at the newest listed release. The text is third-party content, defused exactly as
plugin pages are (plugin_pages.defuse).
"""
from __future__ import annotations

import plugin_pages as pages
from plugin_pages import _range, changelog, defuse, inline, readme_body

# The house format is built in, not a package: it is not in the catalogue (its id is reserved), and its page,
# docs/citations/default/, is hand-written. Only its card is generated here, first on the page.
BUILTIN_CARD = """-   **[SlideMage house format](default/index.md)** · *Built in*

    Comes with SlideMage, nothing to install. The default: used by every deck unless a template or deck chooses
    another format.

    [![](default/preview.png){ loading=lazy }](default/index.md)

    Built in: comes with SlideMage, nothing to install
"""


def page(citation: dict, material: dict, repo: str) -> str:
    """The Markdown of /citations/<id>/."""
    tag, newest = material["tag"], citation["releases"][0]
    name = inline(citation["name"])
    lines = [f"# {name}", "", inline(citation["summary"]), ""]
    if "preview" in citation:
        lines += [f"![The reference list of {name} on a slide](preview.png){{ loading=lazy }}", ""]
    lines += ['!!! success "Nothing leaves your computer"',
              "    A citation format is a TeX file; it contains no program and contacts no network service.", "",
              f"Works with SlideMage {_range(newest['requires_slidemage'])}.", "", "## Installing", "",
              "In SlideMage: **Settings → Plugins → Citation formats → Add from GitHub…**, "
              f"and type `{inline(repo)}`.", "",
              f"By hand: download [{name} {newest['version']}]({newest['url']}) "
              f"({max(1, round(newest['size'] / 1024))} kB), then choose "
              "**Settings → Plugins → Citation formats → Add from file…**.", "",
              "## Using it", "",
              "In a template (between `\\input{SlideMage_setup}` and `\\input{SlideMage_base}`) or in a deck "
              "(before `\\SMUseBibliography`):", "",
              "```latex", f"\\renewcommand{{\\SMCitationFormat}}{{{citation['id']}}}", "```"]
    body = defuse(readme_body(material["readme"]), repo, tag)
    if body:
        lines += ["", "## About this format", "", body]
    lines += ["", "## Versions", "", "| Version | SlideMage | Released | Download |", "|---|---|---|---|"]
    for release in citation["releases"]:
        notes = f" · [notes]({release['notes_url']})" if release.get("notes_url") else ""
        lines.append(f"| {release['version']} | {_range(release['requires_slidemage'])} | {release['published']} "
                     f"| [.smcite]({release['url']}){notes} |")
    log = changelog(material["changelog"], repo, tag)
    if log:
        lines += ["", "## Changelog", "", log]
    lines += ["", "---", "",
              f"Maintained by {inline(citation['maintainer'])} · License {inline(citation['license'])} · "
              f"[Source]({citation['source']})", ""]
    return "\n".join(lines)


def cards(citations: list[dict]) -> str:
    """The cards on /citations/: the built-in house format first, then the listed formats, recommended first as the
    catalogue orders them."""
    out = ['<div class="grid cards" markdown>', "", BUILTIN_CARD]
    for citation in citations:
        newest = citation["releases"][0]
        recommended = " · *Recommended*" if citation["recommended"] else ""
        out += [f"-   **[{inline(citation['name'])}]({citation['id']}/index.md)**{recommended}", "",
                f"    {inline(citation['summary'])}", ""]
        if "preview" in citation:
            out += [f"    [![]({citation['id']}/preview.png){{ loading=lazy }}]({citation['id']}/index.md)", ""]
        out += [f"    Version {newest['version']} · SlideMage {_range(newest['requires_slidemage'])} · "
                f"by {inline(citation['maintainer'])}", ""]
    out.append("</div>")
    return "\n".join(out)
