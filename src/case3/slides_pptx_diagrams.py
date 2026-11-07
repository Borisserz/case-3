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


@dataclass
class NodeBox:
    node: DiagramNode
    x: float  # inches
    y: float  # inches
    w: float  # inches
    h: float  # inches


@dataclass
class DiagramLayout:
    direction: str
    boxes: dict[str, NodeBox] = field(default_factory=dict)
    edges: list[DiagramEdge] = field(default_factory=list)


def compute_diagram_layout(
    graph: DiagramGraph,
    left: float,
    top: float,
    width: float,
    height: float,
) -> DiagramLayout:
    """Assign 2D positions (in inches) to diagram nodes using a layered DAG layout."""
    nodes = graph.nodes
    if not nodes:
        return DiagramLayout(direction=graph.direction, boxes={}, edges=graph.edges)

    # 1. Cycle detection & forward DAG edges extraction
    adj: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in graph.edges:
        if e.src in nodes and e.dst in nodes and e.dst not in adj[e.src]:
            adj[e.src].append(e.dst)

    # DFS to find back-edges (cycles)
    visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
    back_edges: set[tuple[str, str]] = set()

    def dfs(u: str):
        visited[u] = 1
        for v in adj[u]:
            if visited.get(v, 0) == 1:
                back_edges.add((u, v))
            elif visited.get(v, 0) == 0:
                dfs(v)
        visited[u] = 2

    for nid in nodes:
        if visited.get(nid, 0) == 0:
            dfs(nid)

    # 2. Compute layer ranks via longest path on forward DAG
    ranks: dict[str, int] = {nid: 0 for nid in nodes}
    for _ in range(len(nodes)):
        changed = False
        for e in graph.edges:
            if (e.src, e.dst) in back_edges:
                continue
            if e.src in nodes and e.dst in nodes:
                if ranks[e.dst] < ranks[e.src] + 1:
                    ranks[e.dst] = ranks[e.src] + 1
                    changed = True
        if not changed:
            break

    # Group by layer
    num_layers = max(ranks.values()) + 1
    layers: dict[int, list[str]] = {layer_idx: [] for layer_idx in range(num_layers)}
    for nid, r in ranks.items():
        layers[r].append(nid)

    max_layer_size = max(len(layer_nodes) for layer_nodes in layers.values()) if layers else 1

    # 3. Geometry placement in target rectangle [left, top, width, height]
    pad = 0.15
    avail_w = max(0.5, width - 2 * pad)
    avail_h = max(0.5, height - 2 * pad)

    is_td = graph.direction in ("TD", "TB")
    boxes: dict[str, NodeBox] = {}

    if is_td:
        # TD: Primary axis is Y (layers), Secondary axis is X
        # Node dimensions
        node_h = min(0.85, avail_h / (num_layers * 1.45))
        node_w = min(1.9, avail_w / (max_layer_size * 1.25))

        # Ensure bounds fit
        if num_layers * node_h > avail_h:
            node_h = avail_h / max(1, num_layers * 1.1)
        if max_layer_size * node_w > avail_w:
            node_w = avail_w / max(1, max_layer_size * 1.1)

        # Gap between layers
        if num_layers > 1:
            gap_y = (avail_h - num_layers * node_h) / (num_layers - 1)
        else:
            gap_y = 0.0

        for layer_idx, layer_nodes in layers.items():
            if num_layers == 1:
                y = top + pad + (avail_h - node_h) / 2.0
            else:
                y = top + pad + layer_idx * (node_h + gap_y)

            k = len(layer_nodes)
            if k == 1:
                gap_x = 0.0
                layer_w = node_w
                start_x = left + pad + (avail_w - layer_w) / 2.0
            else:
                gap_x = min(0.6, (avail_w - k * node_w) / (k - 1))
                layer_w = k * node_w + (k - 1) * gap_x
                start_x = left + pad + (avail_w - layer_w) / 2.0

            for i, nid in enumerate(layer_nodes):
                x = start_x + i * (node_w + gap_x)
                boxes[nid] = NodeBox(node=nodes[nid], x=round(x, 4), y=round(y, 4), w=round(node_w, 4), h=round(node_h, 4))
    else:
        # LR: Primary axis is X (layers), Secondary axis is Y
        node_w = min(1.75, avail_w / (num_layers * 1.45))
        node_h = min(0.85, avail_h / (max_layer_size * 1.25))

        if num_layers * node_w > avail_w:
            node_w = avail_w / max(1, num_layers * 1.1)
        if max_layer_size * node_h > avail_h:
            node_h = avail_h / max(1, max_layer_size * 1.1)

        if num_layers > 1:
            gap_x = (avail_w - num_layers * node_w) / (num_layers - 1)
        else:
            gap_x = 0.0

        for layer_idx, layer_nodes in layers.items():
            if num_layers == 1:
                x = left + pad + (avail_w - node_w) / 2.0
            else:
                x = left + pad + layer_idx * (node_w + gap_x)

            k = len(layer_nodes)
            if k == 1:
                gap_y = 0.0
                layer_h = node_h
                start_y = top + pad + (avail_h - layer_h) / 2.0
            else:
                gap_y = min(0.6, (avail_h - k * node_h) / (k - 1))
                layer_h = k * node_h + (k - 1) * gap_y
                start_y = top + pad + (avail_h - layer_h) / 2.0

            for i, nid in enumerate(layer_nodes):
                y = start_y + i * (node_h + gap_y)
                boxes[nid] = NodeBox(node=nodes[nid], x=round(x, 4), y=round(y, 4), w=round(node_w, 4), h=round(node_h, 4))

    return DiagramLayout(direction=graph.direction, boxes=boxes, edges=graph.edges)



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
