"""
OSM Importer - Imports real road networks from OpenStreetMap using OSMnx
and converts them to the simulation's internal .smap format.

Usage:
    # Download by city name
    python osm_importer.py --city "Belfort, France" --output belfort_osm.smap --model cellular

    # Download by bounding box
    python osm_importer.py --bbox 47.63 47.66 6.84 6.88 --output belfort_osm.smap --model fluid

    # Simplify the network (merge nodes close together)
    python osm_importer.py --city "Belfort, France" --output belfort_simple.smap --simplify 20

Requirements:
    pip install osmnx
"""

import osmnx as ox
import argparse
import math
from typing import Dict, List, Tuple, Set
from collections import defaultdict


def download_osm_network(place_name: str, network_type: str = "drive"):
    """
    Download street network from OpenStreetMap for a given place.

    Args:
        place_name: Name of the place (e.g., "Belfort, France")
        network_type: Type of network - "drive", "walk", "bike", or "all"

    Returns:
        NetworkX MultiDiGraph from OSMnx
    """
    print(f"📡 Downloading {network_type} network for {place_name}...")

    G = ox.graph_from_place(place_name, network_type=network_type, simplify=True)

    print(f"✅ Downloaded {len(G.nodes)} nodes and {len(G.edges)} edges")
    return G


def download_osm_bbox(north: float, south: float, east: float, west: float,
                      network_type: str = "drive"):
    """
    Download street network from OpenStreetMap for a bounding box.

    Args:
        north, south, east, west: Bounding box coordinates (latitude/longitude)
        network_type: Type of network

    Returns:
        NetworkX MultiDiGraph from OSMnx
    """
    print(f"📡 Downloading {network_type} network for bbox...")
    G = ox.graph_from_bbox(north, south, east, west, network_type=network_type, simplify=True)
    print(f"✅ Downloaded {len(G.nodes)} nodes and {len(G.edges)} edges")
    return G


def project_to_utm(G):
    """
    Project the graph to UTM coordinates for better distance calculations.

    Args:
        G: OSMnx graph with lat/lon coordinates

    Returns:
        Graph with UTM coordinates (in meters)
    """
    print("🗺️  Projecting to UTM coordinates...")
    G_proj = ox.project_graph(G)
    return G_proj


def simplify_nodes(nodes: Dict, edges: List, min_distance: float = 10.0):
    """
    Simplify the network by merging nodes that are very close together.

    Args:
        nodes: Dictionary of node_id -> (x, y)
        edges: List of (src, dst, distance, props)
        min_distance: Minimum distance between nodes (in meters)

    Returns:
        Tuple of (simplified_nodes, simplified_edges)
    """
    if min_distance <= 0:
        return nodes, edges

    print(f"🔧 Simplifying network (min distance: {min_distance}m)...")

    # Create mapping of nodes to their cluster representative
    node_to_cluster = {}
    clusters = []

    node_list = list(nodes.items())
    used = set()

    for i, (node_id, (x, y)) in enumerate(node_list):
        if node_id in used:
            continue

        # Start a new cluster with this node as representative
        cluster = [node_id]
        used.add(node_id)

        # Find all nearby nodes to merge
        for j, (other_id, (ox, oy)) in enumerate(node_list):
            if other_id in used:
                continue

            dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2)
            if dist < min_distance:
                cluster.append(other_id)
                used.add(other_id)

        # Representative is the first node in the cluster
        representative = cluster[0]
        for node in cluster:
            node_to_cluster[node] = representative

        clusters.append((representative, cluster))

    # Create simplified nodes (use centroid of cluster)
    simplified_nodes = {}
    for representative, cluster in clusters:
        if len(cluster) == 1:
            simplified_nodes[representative] = nodes[representative]
        else:
            # Calculate centroid
            x_sum = sum(nodes[nid][0] for nid in cluster)
            y_sum = sum(nodes[nid][1] for nid in cluster)
            simplified_nodes[representative] = (x_sum / len(cluster), y_sum / len(cluster))

    # Remap edges
    simplified_edges = []
    seen_edges = set()

    for src, dst, distance, props in edges:
        new_src = node_to_cluster.get(src, src)
        new_dst = node_to_cluster.get(dst, dst)

        # Skip self-loops
        if new_src == new_dst:
            continue

        # Skip duplicate edges (keep first occurrence)
        edge_key = (new_src, new_dst)
        if edge_key in seen_edges:
            continue

        seen_edges.add(edge_key)

        # Recalculate distance if nodes were merged
        if new_src != src or new_dst != dst:
            x1, y1 = simplified_nodes[new_src]
            x2, y2 = simplified_nodes[new_dst]
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        simplified_edges.append((new_src, new_dst, distance, props))

    print(f"✅ Simplified: {len(nodes)} → {len(simplified_nodes)} nodes, {len(edges)} → {len(simplified_edges)} edges")

    return simplified_nodes, simplified_edges


def normalize_coordinates(nodes: Dict) -> Tuple[Dict, float, float]:
    """
    Normalize coordinates to start from (0, 0).

    Args:
        nodes: Dictionary of node_id -> (x, y)

    Returns:
        Tuple of (normalized_nodes, min_x, min_y)
    """
    if not nodes:
        return {}, 0, 0

    min_x = min(data[0] for data in nodes.values())
    min_y = min(data[1] for data in nodes.values())

    normalized = {}
    for node_id, (x, y) in nodes.items():
        normalized[node_id] = (x - min_x, y - min_y)

    return normalized, min_x, min_y


def extract_graph_data(G):
    """
    Extract nodes and edges from OSMnx graph.

    Args:
        G: Projected OSMnx graph

    Returns:
        Tuple of (nodes_dict, edges_list)
        nodes_dict: {node_id: (x, y)}
        edges_list: [(src, dst, distance, properties)]
    """
    print("📊 Extracting graph data...")

    nodes = {}
    for node_id, data in G.nodes(data=True):
        x = data['x']
        y = data['y']
        nodes[str(node_id)] = (x, y)

    edges = []
    for u, v, key, data in G.edges(keys=True, data=True):
        src = str(u)
        dst = str(v)

        # Calculate distance
        x1, y1 = nodes[src]
        x2, y2 = nodes[dst]
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Extract properties
        props = {
            'length': data.get('length', distance),
            'speed_kph': data.get('maxspeed', 50),  # Default 50 km/h
            'highway': data.get('highway', 'unclassified'),
            'oneway': data.get('oneway', False)
        }

        edges.append((src, dst, distance, props))

    return nodes, edges


def detect_bidirectional_edges(edges: List) -> Tuple[List, Set]:
    """
    Detect which edges have a counterpart in the opposite direction.

    Args:
        edges: List of (src, dst, distance, props)

    Returns:
        Tuple of (edges_list, bidirectional_set)
        bidirectional_set contains tuples of (src, dst) for bidirectional edges
    """
    edge_dict = {}
    for src, dst, distance, props in edges:
        edge_dict[(src, dst)] = (distance, props)

    bidirectional = set()
    processed = set()

    for src, dst, distance, props in edges:
        if (src, dst) in processed:
            continue

        # Check if reverse edge exists
        if (dst, src) in edge_dict:
            bidirectional.add((src, dst))
            bidirectional.add((dst, src))
            processed.add((src, dst))
            processed.add((dst, src))

    return edges, bidirectional


def calculate_edge_params(distance: float, props: dict, model: str, tps: float):
    """
    Calculate edge parameters based on distance and properties.

    Args:
        distance: Edge distance in meters
        props: Edge properties from OSM
        model: "cellular" or "fluid"
        tps: Ticks per second of the simulation

    Returns:
        Dictionary of parameters for the edge
    """
    # Safely parse speed limit, defaulting to 50 km/h
    raw_speed = props.get('speed_kph', 50)
    speed_kph = 50.0

    if isinstance(raw_speed, list):
        raw_speed = raw_speed[0]

    if isinstance(raw_speed, str):
        try:
            speed_kph = float(raw_speed.split()[0])
        except (ValueError, IndexError):
            speed_kph = 50.0
    elif isinstance(raw_speed, (int, float)):
        speed_kph = float(raw_speed)

    speed_ms = speed_kph / 3.6  # Speed in meters per second
    speed_m_per_tick = speed_ms / tps

    if model == "cellular":
        cell_size = 7.5  # meters per cell
        vmax = max(1, int(speed_m_per_tick / cell_size))  # vmax in cells/tick

        # prob_slow depends on road type
        highway_type = props.get('highway', 'unclassified')
        if highway_type in ['motorway', 'trunk', 'primary']:
            prob_slow = 0.05
        elif highway_type in ['secondary', 'tertiary']:
            prob_slow = 0.15
        else:
            prob_slow = 0.25

        return {
            'distance': max(1, int(distance / cell_size)),  # Distance in cells
            'vmax': vmax,
            'prob_slow': prob_slow
        }

    else:  # fluid
        vmax = max(0.1, speed_m_per_tick)  # vmax in meters/tick

        # density_max depends on road type
        highway_type = props.get('highway', 'unclassified')
        if highway_type in ['motorway', 'trunk', 'primary']:
            density_max = 0.3
        elif highway_type in ['secondary', 'tertiary']:
            density_max = 0.5
        else:
            density_max = 0.8

        return {
            'distance': max(1, int(distance)),
            'vmax': round(vmax, 2),
            'density_max': density_max
        }


def write_smap_file(output_path: str, nodes: Dict, edges: List,
                    bidirectional: Set, model: str, tps: float, add_spawners: bool = True):
    """
    Write the graph data to a .smap file.

    Args:
        output_path: Output file path
        nodes: Dictionary of node_id -> (x, y)
        edges: List of (src, dst, distance, props)
        bidirectional: Set of bidirectional edge pairs
        model: "cellular" or "fluid"
        tps: Ticks per second
        add_spawners: Whether to add automatic spawners
    """
    print(f"💾 Writing .smap file to {output_path}...")

    with open(output_path, 'w') as f:
        # Write header
        f.write(f"GRAPH({model}):\n")

        # Write nodes
        for node_id, (x, y) in sorted(nodes.items()):
            f.write(f"    NODE {node_id} ({x:.1f}, {y:.1f})\n")

        f.write("\n")

        # Write edges
        processed = set()
        for src, dst, distance, props in edges:
            if (src, dst) in processed:
                continue

            params = calculate_edge_params(distance, props, model, tps)

            # Check if bidirectional
            if (src, dst) in bidirectional and (dst, src) in bidirectional:
                # Write as BEDGE
                processed.add((src, dst))
                processed.add((dst, src))

                if model == "cellular":
                    f.write(f"    BEDGE {src} {dst} distance={params['distance']} "
                            f"vmax={params['vmax']} prob_slow={params['prob_slow']}\n")
                else:
                    f.write(f"    BEDGE {src} {dst} distance={params['distance']} "
                            f"vmax={params['vmax']} density_max={params['density_max']}\n")
            else:
                # Write as UEDGE
                processed.add((src, dst))

                if model == "cellular":
                    f.write(f"    UEDGE {src} {dst} distance={params['distance']} "
                            f"vmax={params['vmax']} prob_slow={params['prob_slow']}\n")
                else:
                    f.write(f"    UEDGE {src} {dst} distance={params['distance']} "
                            f"vmax={params['vmax']} density_max={params['density_max']}\n")

        # Write intersections section (detect high-degree nodes)
        f.write("\nINTERSECTIONS:\n")

        # Count incoming edges for each node
        incoming_count = defaultdict(int)
        for src, dst, _, _ in edges:
            incoming_count[dst] += 1

        # Add traffic lights to nodes with 3+ incoming edges
        for node_id, count in sorted(incoming_count.items()):
            if count >= 3:
                # Duration proportional to number of incoming roads
                duration = min(100, 30 + count * 10)
                f.write(f"    TRAFFIC_LIGHT {node_id} duration={duration}\n")

        # Write vehicles section (empty)
        f.write("\nVEHICLES:\n")

        # Write spawners section
        if add_spawners:
            f.write("\nSPAWNERS:\n")

            # Add spawners to nodes with few outgoing edges (periphery)
            outgoing_count = defaultdict(int)
            for src, dst, _, _ in edges:
                outgoing_count[src] += 1

            # Select nodes with 1-2 outgoing edges
            periphery_nodes = [node for node, count in outgoing_count.items() if 1 <= count <= 2]

            # Add spawners to ~10% of periphery nodes
            import random
            random.seed(42)  # Reproducible
            num_spawners = max(3, len(periphery_nodes) // 10)
            selected_spawners = random.sample(periphery_nodes, min(num_spawners, len(periphery_nodes)))

            for node_id in sorted(selected_spawners):
                ratio = 0.1 if outgoing_count[node_id] == 1 else 0.15
                f.write(f"    SPAWNER {node_id} ratio={ratio}\n")
        else:
            f.write("\nSPAWNERS:\n")

    print(f"✅ Successfully wrote .smap file!")


def main():
    parser = argparse.ArgumentParser(
        description="Import OpenStreetMap data to .smap format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import Belfort city center with default 20 TPS
  python osm_importer.py --city "Belfort, France" --output belfort_real.smap

  # Import for a 10 TPS simulation
  python osm_importer.py --city "Belfort, France" --tps 10 --output belfort_10tps.smap

  # Use fluid model with simplification
  python osm_importer.py --city "Belfort, France" --model fluid --simplify 15 --output belfort_fluid.smap
        """
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--city",
        type=str,
        help="City or place name (e.g., 'Belfort, France')"
    )
    input_group.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("NORTH", "SOUTH", "EAST", "WEST"),
        help="Bounding box: north south east west (latitude/longitude)"
    )

    # Output
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output .smap file path"
    )

    # Model & Simulation
    parser.add_argument(
        "--model",
        type=str,
        choices=["cellular", "fluid"],
        default="cellular",
        help="Traffic model type (default: cellular)"
    )
    parser.add_argument(
        "--tps",
        type=float,
        default=20.0,
        help="Target ticks per second for the simulation (default: 20.0)"
    )

    # Network type
    parser.add_argument(
        "--network-type",
        type=str,
        choices=["drive", "walk", "bike", "all"],
        default="drive",
        help="Type of street network (default: drive)"
    )

    # Simplification
    parser.add_argument(
        "--simplify",
        type=float,
        default=0,
        help="Simplify network by merging nodes closer than N meters (default: 0 = no simplification)"
    )

    # Spawners
    parser.add_argument(
        "--no-spawners",
        action="store_true",
        help="Don't add automatic vehicle spawners"
    )

    args = parser.parse_args()

    # Download network
    if args.city:
        G = download_osm_network(args.city, args.network_type)
    else:
        north, south, east, west = args.bbox
        G = download_osm_bbox(north, south, east, west, args.network_type)

    # Project to UTM
    G_proj = project_to_utm(G)

    # Extract data
    nodes, edges = extract_graph_data(G_proj)

    # Simplify if requested
    if args.simplify > 0:
        nodes, edges = simplify_nodes(nodes, edges, args.simplify)

    # Normalize coordinates
    nodes, _, _ = normalize_coordinates(nodes)

    # Detect bidirectional edges
    edges, bidirectional = detect_bidirectional_edges(edges)

    # Write output
    write_smap_file(
        args.output,
        nodes,
        edges,
        bidirectional,
        args.model,
        args.tps,
        add_spawners=not args.no_spawners
    )

    print("\n🎉 Done! You can now run:")
    print(f"   python src/main.py --map {args.output} --tps {args.tps} --visualizer")


if __name__ == "__main__":
    main()
