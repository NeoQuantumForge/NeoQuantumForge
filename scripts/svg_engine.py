"""
svg_engine.py
-------------
A single, reusable SVG rendering framework. Every visual artifact in
NeoQuantumForge (ASCII portrait, dashboard, terminal, heatmap) is composed
from the primitives defined here. No other module should build raw SVG
strings by hand -- that rule keeps the project free of duplicated
rendering logic.

Everything is GitHub-Markdown-safe: only static SVG + SMIL (<animate>,
<animateTransform>, <set>) is used, since GitHub strips <script> and
external resources from embedded SVGs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Union

from utils import xml_escape

Number = Union[int, float]


class Node:
    """Minimal XML tree node with attribute + child support."""

    def __init__(self, tag: str, **attrs: object):
        self.tag = tag
        self.attrs = {k.replace("_", "-"): v for k, v in attrs.items() if v is not None}
        self.children: List["Node"] = []
        self.text: Optional[str] = None

    def add(self, child: "Node") -> "Node":
        self.children.append(child)
        return self

    def extend(self, children: Sequence["Node"]) -> "Node":
        self.children.extend(children)
        return self

    def set_text(self, text: str) -> "Node":
        self.text = text
        return self

    def render(self, indent: int = 0) -> str:
        pad = "  " * indent
        attr_str = "".join(f' {k}="{_attr_value(v)}"' for k, v in self.attrs.items())
        if not self.children and self.text is None:
            return f"{pad}<{self.tag}{attr_str}/>"
        inner_parts = []
        if self.text is not None:
            inner_parts.append(f"{pad}  {xml_escape(self.text)}")
        for child in self.children:
            inner_parts.append(child.render(indent + 1))
        inner = "\n".join(inner_parts)
        return f"{pad}<{self.tag}{attr_str}>\n{inner}\n{pad}</{self.tag}>"


def _attr_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return xml_escape(str(v))


# ---------------------------------------------------------------------------
# Document root
# ---------------------------------------------------------------------------

class SVGDocument:
    def __init__(self, width: Number, height: Number, *, font_family: str = "monospace",
                 background: Optional[str] = None):
        self.width = width
        self.height = height
        self.root = Node(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            width=width,
            height=height,
            viewBox=f"0 0 {width} {height}",
            font_family=font_family,
        )
        self.defs = Node("defs")
        self.root.add(self.defs)
        if background:
            self.root.add(rect(0, 0, width, height, fill=background, rx=10))

    def add(self, node: Node) -> Node:
        self.root.add(node)
        return node

    def add_def(self, node: Node) -> Node:
        self.defs.add(node)
        return node

    def render(self) -> str:
        header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        return header + self.root.render()


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def rect(x: Number, y: Number, width: Number, height: Number, *, fill: str = "none",
         stroke: Optional[str] = None, stroke_width: Number = 1, rx: Number = 0,
         opacity: Number = 1, id: Optional[str] = None) -> Node:
    return Node("rect", x=x, y=y, width=width, height=height, fill=fill, stroke=stroke,
                stroke_width=stroke_width, rx=rx, opacity=opacity, id=id)


def circle(cx: Number, cy: Number, r: Number, *, fill: str = "none",
           stroke: Optional[str] = None, stroke_width: Number = 1,
           opacity: Number = 1, id: Optional[str] = None) -> Node:
    return Node("circle", cx=cx, cy=cy, r=r, fill=fill, stroke=stroke,
                stroke_width=stroke_width, opacity=opacity, id=id)


def ellipse(cx: Number, cy: Number, rx: Number, ry: Number, *, fill: str = "none",
            stroke: Optional[str] = None, opacity: Number = 1) -> Node:
    return Node("ellipse", cx=cx, cy=cy, rx=rx, ry=ry, fill=fill, stroke=stroke, opacity=opacity)


def line(x1: Number, y1: Number, x2: Number, y2: Number, *, stroke: str = "#30363d",
         stroke_width: Number = 1, opacity: Number = 1, stroke_dasharray: Optional[str] = None) -> Node:
    return Node("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke,
                stroke_width=stroke_width, opacity=opacity, stroke_dasharray=stroke_dasharray)


def path(d: str, *, fill: str = "none", stroke: Optional[str] = None,
         stroke_width: Number = 1, opacity: Number = 1, id: Optional[str] = None) -> Node:
    return Node("path", d=d, fill=fill, stroke=stroke, stroke_width=stroke_width,
                opacity=opacity, id=id)


def polygon(points: str, *, fill: str = "none", stroke: Optional[str] = None,
            opacity: Number = 1) -> Node:
    return Node("polygon", points=points, fill=fill, stroke=stroke, opacity=opacity)


def polyline(points: str, *, fill: str = "none", stroke: Optional[str] = None,
             stroke_width: Number = 1, opacity: Number = 1) -> Node:
    return Node("polyline", points=points, fill=fill, stroke=stroke,
                stroke_width=stroke_width, opacity=opacity)


def group(*, transform: Optional[str] = None, opacity: Number = 1,
          id: Optional[str] = None, clip_path: Optional[str] = None) -> Node:
    return Node("g", transform=transform, opacity=opacity, id=id, clip_path=clip_path)


def text(x: Number, y: Number, content: str, *, fill: str = "#c9d1d9",
         font_size: Number = 13, font_weight: str = "normal", font_family: Optional[str] = None,
         text_anchor: str = "start", letter_spacing: Optional[Number] = None,
         opacity: Number = 1, id: Optional[str] = None) -> Node:
    n = Node("text", x=x, y=y, fill=fill, font_size=font_size, font_weight=font_weight,
             font_family=font_family, text_anchor=text_anchor, letter_spacing=letter_spacing,
             opacity=opacity, id=id, xml_space="preserve")
    n.set_text(content)
    return n


def tspan(content: str, *, x: Optional[Number] = None, dy: Optional[Number] = None,
          fill: Optional[str] = None) -> Node:
    n = Node("tspan", x=x, dy=dy, fill=fill)
    n.set_text(content)
    return n


def image(href: str, x: Number, y: Number, width: Number, height: Number, *,
          clip_path: Optional[str] = None, opacity: Number = 1) -> Node:
    return Node("image", href=href, x=x, y=y, width=width, height=height,
                clip_path=clip_path, opacity=opacity, preserveAspectRatio="xMidYMid slice")


def clip_path_def(id: str, shape: Node) -> Node:
    cp = Node("clipPath", id=id)
    cp.add(shape)
    return cp


def linear_gradient(id: str, stops: Sequence[tuple], *, x1="0%", y1="0%", x2="100%", y2="100%") -> Node:
    grad = Node("linearGradient", id=id, x1=x1, y1=y1, x2=x2, y2=y2)
    for offset, color, opacity in stops:
        grad.add(Node("stop", offset=offset, stop_color=color, stop_opacity=opacity))
    return grad


def blur_filter(id: str, std_deviation: Number = 4) -> Node:
    f = Node("filter", id=id, x="-50%", y="-50%", width="200%", height="200%")
    f.add(Node("feGaussianBlur", in_="SourceGraphic", stdDeviation=std_deviation))
    return f


# ---------------------------------------------------------------------------
# Animation helpers (SMIL, GitHub-safe)
# ---------------------------------------------------------------------------

def animate(attribute: str, values: str, dur: str, *, begin: str = "0s",
            fill: str = "freeze", repeat_count: str = "1",
            calc_mode: Optional[str] = None) -> Node:
    return Node("animate", attributeName=attribute, values=values, dur=dur, begin=begin,
                fill=fill, repeatCount=repeat_count, calcMode=calc_mode)


def animate_transform(transform_type: str, values: str, dur: str, *, begin: str = "0s",
                       fill: str = "freeze", repeat_count: str = "1") -> Node:
    return Node("animateTransform", attributeName="transform", type=transform_type,
                values=values, dur=dur, begin=begin, fill=fill, repeatCount=repeat_count)


def set_attr(attribute: str, to: str, *, begin: str = "0s", fill: str = "freeze") -> Node:
    return Node("set", attributeName=attribute, to=to, begin=begin, fill=fill)


def fade_in(node: Node, *, delay: float = 0.0, duration: float = 0.6) -> Node:
    """Attach a fade-in animation to an element; sets initial opacity to 0."""
    node.attrs["opacity"] = 0
    node.add(animate("opacity", "0;1", f"{duration}s", begin=f"{delay}s"))
    return node


def draw_line_reveal(node: Node, *, delay: float = 0.0, duration: float = 0.5,
                      path_length: Number = 100) -> Node:
    """Classic 'self-drawing line' effect using stroke-dash animation."""
    node.attrs["stroke-dasharray"] = path_length
    node.attrs["stroke-dashoffset"] = path_length
    node.add(animate("stroke-dashoffset", f"{path_length};0", f"{duration}s", begin=f"{delay}s"))
    return node


def blink_cursor(x: Number, y: Number, *, width: Number = 8, height: Number = 14,
                  fill: str = "#58a6ff", period: str = "1s") -> Node:
    cursor = rect(x, y, width, height, fill=fill)
    cursor.add(animate("opacity", "1;1;0;0", period, begin="0s",
                        repeat_count="indefinite", fill="remove"))
    return cursor


def typing_reveal_group(lines: Sequence[str], *, x: Number, y_start: Number, line_height: Number,
                         font_size: Number, fill: str, char_duration_s: float,
                         start_delay: float, font_family: Optional[str] = None) -> tuple:
    """Builds a sequence of <text> nodes that reveal character-by-character
    using stacked <animate> on a clip-like reveal (via textLength trick is
    unreliable across renderers, so we reveal by progressively animating a
    tspan's fill from transparent per-character isn't feasible either).

    Practical, broadly-compatible approach: reveal each line as a whole
    using opacity staggered at the moment its 'typing' would have finished,
    while a companion cursor rect sweeps across each line's width to sell
    the "typing" illusion.

    Returns (list_of_text_nodes, total_duration_seconds).
    """
    nodes: List[Node] = []
    t = start_delay
    for i, line_text in enumerate(lines):
        duration = max(len(line_text), 1) * char_duration_s
        node = text(x, y_start + i * line_height, line_text, fill=fill,
                     font_size=font_size, font_family=font_family)
        node.attrs["opacity"] = 0
        node.add(animate("opacity", "0;1", "0.15s", begin=f"{t:.2f}s"))
        nodes.append(node)
        t += duration + 0.25
    return nodes, t
