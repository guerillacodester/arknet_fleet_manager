#!/usr/bin/env python3
"""
Route Topology Converter
------------------------
Convert unordered route segments (from QGIS GeoJSON)
into an ordered continuous polyline.

Algorithm:
  • Builds an adjacency graph of all input segments
  • Finds the largest connected component
  • Computes the longest simple path (graph diameter)
  • Outputs a compact JSON with the ordered route

Output:
  Creates <input>_ordered.geojson containing:
    {
      "route": "<route id>",
      "route_data": [[lon, lat], [lon, lat], ...]
    }

Also prints:
  • Number of processed points
  • The two terminus coordinates
"""

from typing import List, Tuple, Dict, Set
import math


# ---------------- Utilities ----------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# ---------------- Graph building ----------------

def build_graph(segments: List[List[Tuple[float, float]]]):
    graph: Dict[Tuple[float, float], Set[Tuple[float, float]]] = {}
    nodes: Set[Tuple[float, float]] = set()

    for seg in segments:
        for i in range(len(seg) - 1):
            a = tuple(seg[i])
            b = tuple(seg[i + 1])
            nodes.update([a, b])
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)

    return graph, nodes


def largest_component(nodes: Set[Tuple[float, float]], graph: Dict):
    seen, components = set(), []

    for node in nodes:
        if node in seen:
            continue
        stack, comp = [node], []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.append(cur)
            for neigh in graph.get(cur, []):
                if neigh not in seen:
                    stack.append(neigh)
        components.append(comp)

    components.sort(key=len, reverse=True)
    return set(components[0]) if components else set()


# ---------------- Longest path ----------------

def bfs_longest_path(graph: Dict, start) -> Tuple[Tuple[float, float], float, List]:
    from collections import deque

    visited = {start: (0.0, [start])}
    q = deque([start])
    farthest, maxdist, maxpath = start, 0.0, [start]

    while q:
        cur = q.popleft()
        dist, path = visited[cur]
        for neigh in graph.get(cur, []):
            if neigh not in visited:
                seglen = haversine(cur[1], cur[0], neigh[1], neigh[0])
                ndist = dist + seglen
                visited[neigh] = (ndist, path + [neigh])
                if ndist > maxdist:
                    farthest, maxdist, maxpath = neigh, ndist, path + [neigh]
                q.append(neigh)

    return farthest, maxdist, maxpath


def longest_path(graph: Dict, comp_nodes: Set[Tuple[float, float]]):
    if not comp_nodes:
        return []

    start = next(iter(comp_nodes))
    farthest, _, _ = bfs_longest_path(graph, start)
    other, _, path = bfs_longest_path(graph, farthest)
    return path


# ---------------- Public API ----------------

def build_route_topology(raw_segments: List[List[Tuple[float, float]]]) -> List[Tuple[float, float]]:
    graph, nodes = build_graph(raw_segments)
    comp_nodes = largest_component(nodes, graph)
    path = longest_path(graph, comp_nodes)
    return path


# ---------------- CLI ----------------

if __name__ == "__main__":
    import argparse, json, sys, os
    from textwrap import dedent

    parser = argparse.ArgumentParser(
        prog="convert_route.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent("""
        Convert unordered QGIS/GeoJSON route segments into an ordered polyline.

        Input:
          A GeoJSON file containing LineString or MultiLineString features.

        Processing:
          The script:
            - Builds a graph of all route segments
            - Identifies the largest connected component
            - Finds the longest continuous path (route diameter)
            - Produces an ordered route

        Output:
          - Writes <input>_ordered.geojson with compact JSON:
              {
                "route": "<route id>",
                "route_data": [[lon, lat], [lon, lat], ...]
              }
          - Prints number of points and the two terminus coordinates.
        """),
        epilog=dedent("""
        Example:
          python convert_route.py route_1.geojson

        This reads 'route_1.geojson', processes the topology,
        writes 'route_1_ordered.geojson', and prints start/stop termini.
        """)
    )

    parser.add_argument(
        "geojson",
        help="Input route GeoJSON file (must contain LineString or MultiLineString geometries)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.geojson):
        print(f"[ERROR] File not found: {args.geojson}")
        sys.exit(1)

    with open(args.geojson, "r", encoding="utf-8") as f:
        data = json.load(f)

    coords = []
    route_id = "unknown"
    if data["type"] == "FeatureCollection":
        for feat in data["features"]:
            props = feat.get("properties", {})
            if "route" in props:
                route_id = str(props["route"])
            geom = feat.get("geometry", {})
            if geom.get("type") == "LineString":
                coords.append(geom["coordinates"])
            elif geom.get("type") == "MultiLineString":
                coords.extend(geom["coordinates"])

    route = build_route_topology(coords)

    result = {
        "route": route_id,
        "route_data": route
    }

    out_file = os.path.splitext(args.geojson)[0] + "_ordered.geojson"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if route:
        start = route[0]
        end = route[-1]
        print(f"[INFO] Processed {len(route)} points into {out_file}")
        print(f"Terminus 1: Lon={start[0]:.6f}, Lat={start[1]:.6f}")
        print(f"Terminus 2: Lon={end[0]:.6f}, Lat={end[1]:.6f}")
    else:
        print("[WARN] No route built.")
