#!/usr/bin/env python3
"""
topology.py
-----------
Graph-based ordering of route segments into a single polyline.
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, List
from collections import deque
from geo_math import GeoMath


LonLat = Tuple[float, float]
Adj = Dict[LonLat, Set[LonLat]]


class RouteTopology:
    """
    Build an ordered route (longest path within the largest connected component)
    from unordered LineString / MultiLineString segments.
    """

    def build_graph(self, segments: List[List[LonLat]]) -> Tuple[Adj, Set[LonLat]]:
        graph: Adj = {}
        nodes: Set[LonLat] = set()
        for seg in segments:
            for i in range(len(seg) - 1):
                a, b = tuple(seg[i]), tuple(seg[i + 1])
                nodes.update((a, b))
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)
        return graph, nodes

    def largest_component(self, nodes: Set[LonLat], graph: Adj) -> Set[LonLat]:
        seen: Set[LonLat] = set()
        components: List[List[LonLat]] = []
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
                for n in graph.get(cur, ()):
                    if n not in seen:
                        stack.append(n)
            components.append(comp)
        components.sort(key=len, reverse=True)
        return set(components[0]) if components else set()

    def _bfs_longest_path(self, graph: Adj, start: LonLat) -> Tuple[LonLat, float, List[LonLat]]:
        """
        BFS variant that accumulates geodesic distance (km) along edges
        to find a farthest node and its path from `start`.
        """
        visited: Dict[LonLat, Tuple[float, List[LonLat]]] = {start: (0.0, [start])}
        q: deque[LonLat] = deque([start])
        farthest, maxdist, maxpath = start, 0.0, [start]

        while q:
            cur = q.popleft()
            dist, path = visited[cur]
            for nxt in graph.get(cur, ()):
                if nxt in visited:
                    continue
                seglen = GeoMath.haversine(cur[1], cur[0], nxt[1], nxt[0])
                ndist = dist + seglen
                visited[nxt] = (ndist, path + [nxt])
                if ndist > maxdist:
                    farthest, maxdist, maxpath = nxt, ndist, path + [nxt]
                q.append(nxt)

        return farthest, maxdist, maxpath

    def longest_path(self, graph: Adj, comp_nodes: Set[LonLat]) -> List[LonLat]:
        if not comp_nodes:
            return []
        start = next(iter(comp_nodes))
        a, _, _ = self._bfs_longest_path(graph, start)
        b, _, path = self._bfs_longest_path(graph, a)
        return path  # ordered list (lon, lat)

    # Public façade

    def build_ordered_route(self, segments: List[List[LonLat]]) -> List[LonLat]:
        graph, nodes = self.build_graph(segments)
        comp = self.largest_component(nodes, graph)
        return self.longest_path(graph, comp)

    @staticmethod
    def termini(ordered_route: List[LonLat]) -> Tuple[LonLat, LonLat]:
        if not ordered_route:
            return ((0.0, 0.0), (0.0, 0.0))
        return (ordered_route[0], ordered_route[-1])
