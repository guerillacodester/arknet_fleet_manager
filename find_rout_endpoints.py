#!/usr/bin/env python3
"""
find_route_termini.py
---------------------
Given a LineString/MultiLineString GeoJSON, find the two route termini by:
  1) building a weighted graph from all segments,
  2) selecting the largest connected component,
  3) computing the graph diameter (longest shortest path) via 2x Dijkstra.
This is robust even when there are multiple spurs/branches (degree=1 > 2).
"""

import sys, os, json, math, heapq
from collections import defaultdict, deque

# --- geo utils ---------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def round_pt(pt, ndigits=6):
    lon, lat = pt
    return (round(float(lon), ndigits), round(float(lat), ndigits))

# --- graph building ----------------------------------------------------------

def load_segments(geojson_path, ndigits=6):
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    segments = []
    for feat in gj.get("features", []):
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        if gtype == "LineString":
            coords = [round_pt(tuple(c), ndigits) for c in geom["coordinates"]]
            segments.append(coords)
        elif gtype == "MultiLineString":
            for seg in geom["coordinates"]:
                coords = [round_pt(tuple(c), ndigits) for c in seg]
                segments.append(coords)
        else:
            # ignore non-line geometries
            continue
    return segments

def build_weighted_graph(segments):
    """
    adjacency: dict[node] -> dict[neighbor] = weight_m
    """
    adj = defaultdict(dict)
    for seg in segments:
        for i in range(len(seg) - 1):
            (lon1, lat1) = seg[i]
            (lon2, lat2) = seg[i+1]
            w = haversine(lat1, lon1, lat2, lon2)
            if w == 0:
                continue
            # undirected
            if (lon2, lat2) not in adj[(lon1, lat1)] or adj[(lon1, lat1)][(lon2, lat2)] > w:
                adj[(lon1, lat1)][(lon2, lat2)] = w
                adj[(lon2, lat2)][(lon1, lat1)] = w
    return adj

# --- components & diameter ---------------------------------------------------

def connected_components(adj):
    seen = set()
    comps = []
    for v in adj.keys():
        if v in seen: 
            continue
        q = deque([v])
        seen.add(v)
        comp = []
        while q:
            u = q.popleft()
            comp.append(u)
            for n in adj[u].keys():
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        comps.append(comp)
    return comps

def component_total_length(adj, comp_nodes):
    # Sum each edge once
    seen_edges = set()
    total = 0.0
    for u in comp_nodes:
        for v, w in adj[u].items():
            if (v, u) in seen_edges: 
                continue
            seen_edges.add((u, v))
            total += w
    return total

def dijkstra_farthest(adj, start):
    dist = {start: 0.0}
    pq = [(0.0, start)]
    prev = {}
    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in adj[u].items():
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    # farthest node by distance
    far = max(dist.items(), key=lambda kv: kv[1])[0]
    return far, dist, prev

def extract_path(prev, end):
    path = [end]
    while end in prev:
        end = prev[end]
        path.append(end)
    path.reverse()
    return path

# --- main --------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_route_termini.py <route.geojson> [--round 6]")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    # optional rounding to consolidate tiny float differences
    ndigits = 6
    if "--round" in sys.argv:
        try:
            ndigits = int(sys.argv[sys.argv.index("--round") + 1])
        except Exception:
            print("[WARN] Bad --round value; defaulting to 6")

    segments = load_segments(path, ndigits=ndigits)
    adj = build_weighted_graph(segments)

    if not adj:
        print("[ERROR] No graph edges found.")
        sys.exit(1)

    comps = connected_components(adj)
    # choose component with maximum total length
    comp_lengths = [(component_total_length(adj, c), i) for i, c in enumerate(comps)]
    comp_idx = max(comp_lengths)[1]
    main_comp = set(comps[comp_idx])

    # pick arbitrary node from main component
    any_node = next(iter(main_comp))
    # run Dijkstra twice to get diameter endpoints
    a, _, _ = dijkstra_farthest(adj, any_node)
    b, dist_ab, prev_ab = dijkstra_farthest(adj, a)

    path_nodes = extract_path(prev_ab, b)
    total_m = dist_ab[b]

    (lon_a, lat_a) = a
    (lon_b, lat_b) = b

    print(f"[INFO] Nodes: {len(adj)}, Components: {len(comps)} (using largest)")
    print(f"[INFO] Diameter path length: {total_m/1000:.3f} km, nodes on path: {len(path_nodes)}")
    print(f"Terminus 1: Lon={lon_a:.6f}, Lat={lat_a:.6f}")
    print(f"Terminus 2: Lon={lon_b:.6f}, Lat={lat_b:.6f}")

if __name__ == "__main__":
    main()
