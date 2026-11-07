"""Native PPTX vector shapes and connectors for Liber diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

log = logging.getLogger("case3.slides_pptx_diagrams")

_RE_FLOWCHART = re.compile(r"^\s*(?:flowchart|graph)\s+([A-Za-z]+)", re.IGNORECASE)
_RE_CLASS_ASSIGN = re.compile(r"^\s*class\s+([A-Za-z0-9_,\s]+?)\s+([A-Za-z0-9_]+)\s*$", re.MULTILINE)
_RE_EDGE = re.compile(
    r"([A-Za-z0-9_]+)"                           # src
    r"(?:\s*(?:\[\(.*?\)\]|\(\[.*?\]\)|\{.*?\}|\[.*?\]|\(.*?\)|\(\(\(.*?\)|\(\(.*?\)|\>.*?\]))?" # optional src def
    r"(?:\s*:::\s*([A-Za-z0-9_]+))?"             # optional src class
    r"\s*(?:-->|-.->|==>|--\s*>\s*)"              # arrow
    r"(?:\|(.*?)\|)?"                             # optional edge label
    r"\s*([A-Za-z0-9_]+)"                         # dst
    r"(?:\s*(?:\[\(.*?\)\]|\(\[.*?\]\)|\{.*?\}|\[.*?\]|\(.*?\)|\(\(\(.*?\)|\(\(.*?\)|\>.*?\]))?" # optional dst def
    r"(?:\s*:::\s*([A-Za-z0-9_]+))?"             # optional dst class
)

# Extract node definition tokens: id([label]), id[label], id{label}, id[(label)], id(label) with optional :::role
_RE_NODE_DEF = re.compile(
    r"\b([A-Za-z0-9_]+)\s*(?:\[\((.*?)\)\]|\(\[(.*?)\]\)|\{(.*?)\}|\[(.*?)\]|\((.*?)\))(?:\s*:::\s*([A-Za-z0-9_]+))?"
)


@dataclass
class DiagramNode:
    id: str
    label: str
    shape: str = "rect"  # "rect" | "capsule" | "diamond" | "cylinder"
    role: str = "process"  # "start" | "process" | "decision" | "ok" | "warn" | "data"


@dataclass
class DiagramEdge:
    src: str
    dst: str
    label: str = ""


@dataclass
class DiagramGraph:
    direction: str  # "TD" | "LR"
    nodes: dict[str, DiagramNode] = field(default_factory=dict)
    edges: list[DiagramEdge] = field(default_factory=list)


def parse_mermaid_flowchart(mermaid: str) -> DiagramGraph | None:
    """Parse a Mermaid flowchart string into a structured DiagramGraph.

    Returns None if text is not a flowchart or cannot be parsed.
    """
    if not mermaid or not isinstance(mermaid, str):
        return None
    raw = mermaid.strip()
    first_line = raw.splitlines()[0].strip() if raw.splitlines() else ""
    head_match = _RE_FLOWCHART.match(first_line)
    if not head_match:
        return None

    direction = head_match.group(1).upper()
    if direction not in ("TD", "TB", "LR", "RL", "BT"):
        direction = "TD"
    if direction == "TB":
        direction = "TD"

    # Extract roles from class assignments
    node_roles: dict[str, str] = {}
    for match in _RE_CLASS_ASSIGN.finditer(raw):
        node_ids_str, role_name = match.group(1), match.group(2).lower()
        for nid in node_ids_str.split(","):
            cleaned = nid.strip()
            if cleaned:
                node_roles[cleaned] = role_name

    nodes: dict[str, DiagramNode] = {}
    edges: list[DiagramEdge] = []

    # First pass: find all explicit node shapes & labels
    for match in _RE_NODE_DEF.finditer(raw):
        nid = match.group(1)
        cyl_lbl = match.group(2)
        capsule_lbl = match.group(3)
        diamond_lbl = match.group(4)
        rect_lbl = match.group(5)
        round_lbl = match.group(6)
        inline_role = (match.group(7) or "").lower()

        shape = "rect"
        label = nid
        if cyl_lbl is not None:
            shape = "cylinder"
            label = cyl_lbl.strip()
        elif capsule_lbl is not None:
            shape = "capsule"
            label = capsule_lbl.strip()
        elif diamond_lbl is not None:
            shape = "diamond"
            label = diamond_lbl.strip()
        elif rect_lbl is not None:
            shape = "rect"
            label = rect_lbl.strip()
        elif round_lbl is not None:
            shape = "capsule"
            label = round_lbl.strip()

        # Determine role: inline :::role takes precedence over class assignment, then fallback
        role = inline_role or node_roles.get(nid)
        if not role:
            if shape == "capsule":
                role = "start"
            elif shape == "diamond":
                role = "decision"
            elif shape == "cylinder":
                role = "data"
            else:
                role = "process"

        nodes[nid] = DiagramNode(id=nid, label=label, shape=shape, role=role)

    # Second pass: parse edges and find any implicit nodes
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("%%") or line.startswith("class") or line.startswith("subgraph"):
            continue
        # Split chained edges or find matches
        # A simple scanner for X --> Y
        edge_matches = list(_RE_EDGE.finditer(line))
        for em in edge_matches:
            src = em.group(1)
            edge_lbl = (em.group(3) or "").strip()
            dst = em.group(4)
            edges.append(DiagramEdge(src=src, dst=dst, label=edge_lbl))
            if src not in nodes:
                nodes[src] = DiagramNode(id=src, label=src, shape="rect", role=node_roles.get(src, "process"))
            if dst not in nodes:
                nodes[dst] = DiagramNode(id=dst, label=dst, shape="rect", role=node_roles.get(dst, "process"))

    if not nodes:
        return None

    return DiagramGraph(direction=direction, nodes=nodes, edges=edges)
