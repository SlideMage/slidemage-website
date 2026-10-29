# CampusOnline

![](icon.svg){ width="64" } Course links, admin slides and session-aware rendering for CAMPUSonline courses.

!!! info "What leaves your computer"
    This plugin contacts:

    - The CAMPUSonline server of the linked course

## Requirements

- A CAMPUSonline course page

Works with SlideMage &gt;=9.0.

## Installing

In SlideMage: **Settings → Plugins** or **Help → Plugins…**.

By hand: download [CampusOnline 1.0.0](https://github.com/SlideMage/slidemage-plugin-campusonline/releases/download/v1.0.0/campusonline-1.0.0.smplugin) (32 kB), then choose **Settings → Plugins → Install from file…**.

## About this plugin

Connects a SlideMage deck to its course on CAMPUSonline, the course management system many universities use. It
was built for the University of Graz (UGO) and works with any CAMPUSonline server whose course pages are public.

- **Course link.** Give a deck the address of its course page in the deck's settings, on the Course tab, and open
  the page from there or from the Deck menu. The link is kept in the deck's preamble as a comment
  (`%% SlideMage course URL: …`); without the plugin the deck compiles the same.
- **Admin slides.** Generate a title slide (course title, semester, lecturers) and a table of the course's
  sessions (date, time, room) from the course's public data, in the deck's language, and insert them into the
  deck.
- **Courses that are on soon.** SlideMage renders the previews of a deck in the background; a deck whose course
  has a session within the next 7 days goes first.

**Privacy.** The plugin contacts only the CAMPUSonline server of a deck's course link, and only its public,
anonymous REST interface: no login, nothing about you or your decks is sent. It fetches a course only when you open
its Course tab or Admin slides, and keeps the session dates it got then in a file in SlideMage's cache folder; the
background renders read that file and never contact the server.

## Versions

| Version | SlideMage | Released | Download |
|---|---|---|---|
| 1.0.0 | &gt;=9.0 | 2026-10-29 | [.smplugin](https://github.com/SlideMage/slidemage-plugin-campusonline/releases/download/v1.0.0/campusonline-1.0.0.smplugin) · [notes](https://github.com/SlideMage/slidemage-plugin-campusonline/releases/tag/v1.0.0) |

## Changelog

### v1.0.0

*2026-10-29 · first release*

The CAMPUSonline features that were built into SlideMage up to 8.x, as a plugin, built on SlideMage's plugin API 1: a deck's course link, the admin slides (a title slide and a course-sessions table from the course's public data), and earlier background renders for a deck whose course has a session within 7 days.

---

Maintained by Jürgen Fleiß · License GPL-3.0-or-later · [Source](https://github.com/SlideMage/slidemage-plugin-campusonline)
