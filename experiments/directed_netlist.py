"""Direction-aware Yosys netlist conversion for the placement pipeline.

Turns one module of a Yosys ``write_json`` netlist into a node-link JSON in
the same style as ``testcases/p1.json`` (cells first, I/O ports last as pads,
net nodes after the modules) but at **named-net** granularity: every entry of
``netnames`` becomes one net node whose members are the cells and ports
touching its bits, and whose ``"driver"`` attribute is the single module that
drives the net (a cell output pin or an input port).  The driver attribute is
what lets ``nnsplace`` measure worst wire length on driver -> sink wires only.

``read_directed_json`` re-reads such a file into a ``Netlist`` and attaches
the same per-net driver map as ``netlist.net_driver``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def yosys_module_to_node_link(
    data: Dict[str, Any], module_name: str, num_pads: Optional[int] = None
) -> Dict[str, Any]:
    """Convert one Yosys module to a directed node-link JSON dict."""
    module_data = data["modules"][module_name]
    cell_names = list(module_data["cells"].keys())
    port_names = list(module_data["ports"].keys())
    num_cells = len(cell_names)
    num_ports = len(port_names) if num_pads is None else num_pads

    bit_to_net: Dict[int, str] = {}
    netnames = module_data.get("netnames", {})
    for net_name, net_info in netnames.items():
        for bit in net_info["bits"]:
            bit_to_net[bit] = net_name

    def pad_id(index: int) -> int:
        return num_cells + index

    net_members: Dict[str, set[int]] = {}
    net_driver: Dict[str, set[int]] = {}

    def remember(net_name: str, module_id: int) -> None:
        net_members.setdefault(net_name, set()).add(module_id)

    def remember_driver(net_name: str, module_id: int) -> None:
        net_driver.setdefault(net_name, set()).add(module_id)

    for index, port_info in enumerate(module_data["ports"].values()):
        direction = port_info.get("direction")
        for bit in port_info["bits"]:
            net_name = bit_to_net.get(bit)
            if net_name is None:
                continue
            remember(net_name, pad_id(index))
            if direction == "input":
                remember_driver(net_name, pad_id(index))

    for cell_index, (_, cell_info) in enumerate(module_data["cells"].items()):
        port_directions = cell_info.get("port_directions", {})
        for port_name, bits in cell_info.get("connections", {}).items():
            direction = port_directions.get(port_name)
            for bit in bits:
                if not isinstance(bit, int):
                    continue
                net_name = bit_to_net.get(bit)
                if net_name is None:
                    continue
                remember(net_name, cell_index)
                if direction == "output":
                    remember_driver(net_name, cell_index)

    modules = list(range(num_cells + num_ports))
    net_nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, int]] = []
    net_id = len(modules)
    for net_name in net_members:
        members = net_members[net_name]
        if len(members) < 2:
            continue
        drivers = net_driver.get(net_name)
        driver = None
        if drivers and len(drivers) == 1 and next(iter(drivers)) in members:
            driver = next(iter(drivers))
        net_nodes.append({"id": net_id, "driver": driver})
        for module_id in members:
            links.append({"source": module_id, "target": net_id})
        net_id += 1

    node_ids = [{"id": m} for m in modules] + net_nodes
    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "num_modules": len(modules),
            "num_nets": len(net_nodes),
            "num_pads": num_ports,
        },
        "nodes": node_ids,
        "edges": links,
    }


def yosys_file_to_node_link(
    filename: str, module_name: Optional[str] = None, output: Optional[str] = None
) -> Dict[str, Any]:
    """Convert a Yosys JSON file (one module) and optionally write the JSON."""
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    if module_name is None:
        module_name = list(data["modules"].keys())[0]
    result = yosys_module_to_node_link(data, module_name)
    if output:
        with open(output, "w", encoding="utf-8", newline="\n") as file:
            json.dump(result, file)
    return result


def read_directed_json(filename: Any) -> Any:
    """Read a directed node-link JSON into a Netlist with ``net_driver`` set.

    ``filename`` may be a path or an already loaded node-link dict.
    """
    import networkx as nx

    from netlistx.netlist import Netlist

    data = filename if isinstance(filename, dict) else json.load(
        open(filename, encoding="utf-8")
    )
    num_modules = data["graph"]["num_modules"]
    num_nets = data["graph"]["num_nets"]
    num_pads = data["graph"]["num_pads"]

    graph = nx.Graph()
    graph.add_nodes_from(range(num_modules + num_nets))
    for link in data.get("edges") or data.get("links"):
        graph.add_edge(link["source"], link["target"])
    for node in data["nodes"]:
        if "driver" in node:
            graph.nodes[node["id"]]["driver"] = node["driver"]

    netlist = Netlist(
        graph, range(num_modules), range(num_modules, num_modules + num_nets)
    )
    netlist.num_pads = num_pads
    netlist.net_driver = {  # type: ignore[attr-defined]
        net: graph.nodes[net].get("driver") for net in netlist.nets
    }
    return netlist


def choose_runner_module(filename: str) -> str:
    """Pick a module that fits the placer's assumptions (cells + pads)."""
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    best: Optional[tuple[int, str]] = None
    for module_name, module_data in data["modules"].items():
        if "cells" not in module_data:
            continue
        num_cells = len(module_data["cells"])
        num_ports = len(module_data.get("ports", {}))
        if num_ports and num_cells:
            score = num_cells + num_ports
            if best is None or score > best[0]:
                best = (score, module_name)
    if best is None:
        raise RuntimeError(f"no suitable module in {filename}")
    return best[1]
