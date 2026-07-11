"""
terminal_engine.py
-------------------
Renders terminal.svg: a simulated terminal session where commands "type"
themselves and produce output, ending with a permanently blinking cursor.
Commands are fully configurable in profile.json; a few (projects, skills,
languages) can be sourced live from GitHub data via "auto:<source>".
"""

from __future__ import annotations

from typing import Dict, List

from config import IdentityConfig, TerminalConfig, ThemeConfig
from github import Repository
from svg_engine import SVGDocument, blink_cursor, group, rect, text, animate
from utils import get_logger

log = get_logger("terminal_engine")


def _resolve_auto_output(source: str, context: Dict[str, List[str]]) -> List[str]:
    key = source.split(":", 1)[1]
    return context.get(key, [])


def _resolve_command_output(raw_output, identity: IdentityConfig,
                             context: Dict[str, List[str]]) -> List[str]:
    if isinstance(raw_output, str) and raw_output.startswith("auto:"):
        return _resolve_auto_output(raw_output, context)
    if isinstance(raw_output, list):
        resolved = []
        for line in raw_output:
            resolved.append(
                line.format(display_name=identity.display_name, role=identity.role)
                if isinstance(line, str) else str(line)
            )
        return resolved
    return [str(raw_output)]


def build_terminal_context(repos: List[Repository], pinned_names: List[str],
                            top_languages: List[str]) -> Dict[str, List[str]]:
    pinned_display = pinned_names or [r.name for r in repos[:5]]
    return {
        "pinned_repositories": pinned_display or ["\u2014"],
        "top_languages": top_languages or ["\u2014"],
        "languages": top_languages or ["\u2014"],
    }


def render_terminal_svg(term_cfg: TerminalConfig, identity: IdentityConfig,
                         context: Dict[str, List[str]], theme: ThemeConfig,
                         width: int, height: int) -> str:
    doc = SVGDocument(width, height, font_family="monospace", background="#010409")
    doc.add(rect(0, 0, width, height, fill="none", stroke=theme.border, stroke_width=1, rx=10))

    # fake window chrome
    chrome = group(id="terminal-chrome")
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        chrome.add(rect(14 + i * 16, 12, 8, 8, fill=color, rx=4))
    doc.add(chrome)
    chrome.add(text(width / 2, 19, "NeoQuantumForge — terminal", fill=theme.text_secondary,
                     font_size=10, text_anchor="middle", font_family="monospace"))

    body = group(id="terminal-body")
    doc.add(body)

    left_pad = 16
    line_height = 16
    font_size = 11.5
    y = 44

    char_dur = term_cfg.typing_speed_ms / 1000.0
    t = 0.3

    for cmd_cfg in term_cfg.commands:
        # prompt + command line, revealed as a whole once "typed"
        cmd_line = f"{term_cfg.prompt} {cmd_cfg.cmd}"
        type_duration = max(len(cmd_line), 1) * char_dur

        cmd_node = text(left_pad, y, cmd_line, fill=theme.accent, font_size=font_size,
                         font_family="monospace")
        cmd_node.attrs["opacity"] = 0
        cmd_node.add(animate("opacity", "0;1", "0.1s", begin=f"{t:.2f}s"))
        body.add(cmd_node)
        t += type_duration + 0.15
        y += line_height

        outputs = _resolve_command_output(cmd_cfg.output, identity, context)
        for out_line in outputs:
            if y > height - 30:
                break
            out_node = text(left_pad, y, str(out_line), fill=theme.text_primary,
                             font_size=font_size, font_family="monospace")
            out_node.attrs["opacity"] = 0
            out_node.add(animate("opacity", "0;1", "0.2s", begin=f"{t:.2f}s"))
            body.add(out_node)
            t += 0.35
            y += line_height

        t += 0.25
        y += line_height * 0.4
        if y > height - 30:
            break

    # final blinking cursor after the prompt, forever
    cursor_prompt = text(left_pad, y, term_cfg.prompt, fill=theme.accent, font_size=font_size,
                          font_family="monospace")
    cursor_prompt.attrs["opacity"] = 0
    cursor_prompt.add(animate("opacity", "0;1", "0.1s", begin=f"{t:.2f}s", fill="freeze"))
    body.add(cursor_prompt)

    cursor_x = left_pad + len(term_cfg.prompt) * 7.2 + 8
    cursor = blink_cursor(cursor_x, y - 11, width=7, height=13, fill=theme.accent)
    cursor.attrs["opacity"] = 0
    cursor.add(animate("opacity", "0;1", "0.1s", begin=f"{t:.2f}s", fill="freeze"))
    # re-attach the indefinite blink after appearing (nested animate begin offset)
    blink = animate("opacity", "1;1;0;0", "1s", begin=f"{t:.2f}s", repeat_count="indefinite", fill="remove")
    cursor.add(blink)
    body.add(cursor)

    return doc.render()


def build_terminal_svg(term_cfg: TerminalConfig, identity: IdentityConfig,
                        repos: List[Repository], pinned_names: List[str],
                        top_languages: List[str], theme: ThemeConfig,
                        width: int, height: int) -> str:
    context = build_terminal_context(repos, pinned_names, top_languages)
    svg = render_terminal_svg(term_cfg, identity, context, theme, width, height)
    log.info("Terminal generated with %d commands", len(term_cfg.commands))
    return svg
