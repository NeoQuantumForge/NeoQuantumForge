# NeoQuantumForge

A GitHub Profile Operating System: an animated, self-drawing, always-current
profile README built from live GitHub data, rendered entirely as
GitHub-compatible SVG (no JavaScript), and refreshed automatically every day
by GitHub Actions.

> `README.md` at the repository root is **generated output**, not something
> you edit by hand. This file (`DOCS.md`) is the real documentation.

---

## What it does

On boot, the profile:

1. Prints a terminal-style boot sequence (`Initializing NeoQuantumForge...` → `System Ready.`)
2. Draws an ASCII-art portrait of you, line by line, top to bottom
3. Fades in a live dashboard (followers, stars, repos, top languages, pinned projects, ...)
4. "Types" out a simulated terminal session (`whoami`, `projects`, `skills`, ...)
5. Reveals a real GitHub contribution heatmap, week by week, with streak stats

Everything is real SVG + SMIL animation (`<animate>`, `<set>`) — the same
technique GitHub already allows in embedded images, so it renders correctly
directly on your profile page with zero external JS.

## Quick start

```bash
git clone https://github.com/<you>/NeoQuantumForge.git
cd NeoQuantumForge
pip install -r requirements.txt

# 1. Edit profile.json: set your GitHub username, name, role, links, etc.
# 2. Drop a headshot at assets/photo.jpg (or update photo.path in profile.json)
# 3. Build once locally to preview:
python main.py
```

Open the generated `README.md` in a Markdown previewer (or just push it —
GitHub renders the embedded SVGs natively) to see the result.

To go live:

1. Create a **public repository named exactly your GitHub username**
   (e.g. `github.com/octocat/octocat`) — this is what makes a README show
   up on your profile page.
2. Push this project into it.
3. In the repo's Settings → Secrets → Actions, add a `PROFILE_TOKEN`
   personal access token with `read:user` scope (needed for pinned
   repositories and the contribution calendar, which the REST API can't
   expose — only GraphQL can, and GraphQL requires a token even for public
   data). Without it, the profile falls back to public REST data only
   (no pinned repos / no heatmap).
4. The included workflow (`.github/workflows/update-profile.yml`) runs
   daily and on every push to `profile.json` or `scripts/**`, rebuilding
   and committing the refreshed assets automatically.

## Configuration

Everything lives in `profile.json` — nothing is hardcoded in the engines.
Key sections:

| Section       | Controls |
|---------------|----------|
| `github`      | username, token env var |
| `identity`    | display name, role, tagline, location, focus |
| `photo`       | path to the source headshot |
| `social_links`| badges rendered in the README footer |
| `theme`       | all colors + font family |
| `animation`   | boot/typing/reveal speeds (ms) |
| `dashboard`   | which widgets to show, pinned/featured repo overrides |
| `ascii`       | charset, columns, contrast, gamma, brightness, reveal speed |
| `terminal`    | prompt string, typing speed, custom commands (supports `auto:pinned_repositories`, `auto:top_languages`, `auto:languages`) |
| `layout`      | panel widths/heights, mobile breakpoint |

## Architecture

```
main.py                    orchestrates the full pipeline
scripts/
  config.py                typed profile.json loader
  utils.py                 logging, JSON cache w/ TTL, retry decorator, formatters
  github.py                single GitHub REST+GraphQL client (all API calls live here)
  svg_engine.py             reusable SVG primitives + SMIL animation helpers
  ascii_engine.py           photo -> processed grayscale -> ASCII grid -> SVG
  dashboard_engine.py       GitHub data -> dashboard rows -> SVG
  terminal_engine.py        typing simulation -> SVG
  heatmap_engine.py         contribution calendar -> heatmap SVG + streak calc
  fetch_profile.py          \
  fetch_repositories.py      |  thin wrappers around github.py,
  fetch_activity.py          |  one responsibility each, per the
  fetch_contributions.py     |  project's "no duplicated GitHub logic
  fetch_languages.py        /   anywhere else" rule
  build_ascii.py            \
  build_dashboard.py         |  glue: fetch + engine -> write assets/*.svg
  build_terminal.py          |
  build_heatmap.py          /
  build_readme.py           boot.svg + final README.md assembly
  demo_data.py              offline fallback data (no crash without a token/network)
assets/                     generated SVGs + your source photo live here
cache/                      JSON response cache (TTL-based, gitignored contents optional)
data/                       reserved for any additional generated data files
.github/workflows/
  update-profile.yml        daily automated rebuild + commit
```

**Every** SVG in this project is built through `svg_engine.py`. No other
module constructs raw SVG strings — this is what the project spec calls
"no duplicated SVG generation anywhere else," and it's what makes it
possible to re-theme the whole profile by editing exactly one config
section (`theme` in `profile.json`).

## Design language

GitHub Dark, terminal/hacker aesthetic, monochrome with a single blue
accent. No RGB cycling, no glitch effects, no glow — deliberately subtle,
professional, and legible.

## Performance & resilience

* Full rebuild targets **under 10 seconds** (`main.py` logs a warning if
  exceeded).
* All GitHub calls go through a TTL'd JSON cache; a live-fetch failure
  falls back to the last good cached response, and — if there is no cache
  at all yet (e.g. first run right after cloning, no token configured) —
  falls back further to clearly-labeled demo data so the build never
  crashes.
* Repository pagination is capped defensively at 1000 repos; the ASCII
  engine and heatmap both degrade gracefully to whatever image/data size
  is available.

## Extending it

* **New dashboard fields**: add a case to `field_map` in
  `dashboard_engine.build_dashboard_rows`, then reference its key in
  `profile.json → dashboard.widgets`.
* **New terminal commands**: add an entry to `profile.json → terminal.commands`
  (static output list, or `"auto:<key>"` sourced from
  `terminal_engine.build_terminal_context`).
* **New SVG widgets**: build them from `svg_engine.py` primitives and drop
  the resulting `.svg` into the README template in `build_readme.py`.

## License

MIT — see `LICENSE`.
