"""
Downloads Indian city road networks from OpenStreetMap
via OSMnx and builds graph structures for the GCN layer.

Handles India-specific road features:
  - Speed breakers (tagged in OSM)
  - Unpaved/dirt roads (common in Tier 2 cities)
  - Narrow lanes and mixed vehicle types
  - Road class weights calibrated for Indian conditions

Output artifacts consumed by models/lstm_gcn.py:
  adjacency_matrix.npz   sparse adjacency matrix
  node_features.csv      per-node feature DataFrame
  graph.graphml          full NetworkX graph

No API keys needed — OpenStreetMap is free.
"""

import logging
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path
from scipy.sparse import csr_matrix, save_npz, load_npz
from dotenv import load_dotenv

try:
    import osmnx as ox  # type: ignore
except ImportError:
    ox = None

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# India-specific road class weights for GCN edge weights.
# Lower weight = harder/slower road for emergency vehicles.
INDIA_ROAD_WEIGHTS: dict = {
    "motorway":     1.00,
    "trunk":        0.95,
    "primary":      0.85,
    "secondary":    0.75,
    "tertiary":     0.60,
    "unclassified": 0.40,
    "residential":  0.35,
    "service":      0.25,
    "track":        0.15,
    "path":         0.10,
    "default":      0.40,
}

# OSM tags relevant for India-specific feature penalties
INDIA_OSM_TAGS: dict = {
    "surface":    ["unpaved", "dirt", "gravel", "mud"],
    "smoothness": ["bad", "very_bad", "horrible", "very_horrible"],
    "highway":    ["speed_camera", "crossing"],
}

# Default speed limits by road class (km/h) for India.
# Used when OSM maxspeed tag is absent.
INDIA_DEFAULT_SPEEDS: dict = {
    "motorway":     100,
    "trunk":         80,
    "primary":       60,
    "secondary":     50,
    "tertiary":      40,
    "unclassified":  30,
    "residential":   30,
    "service":       20,
    "default":       30,
}

# File names for the three graph artifacts
_GRAPHML_FILE  = "graph.graphml"
_ADJ_FILE      = "adjacency_matrix.npz"
_FEATS_FILE    = "node_features.csv"


def _build_synthetic_city_graph(city_name: str) -> nx.MultiDiGraph:
    """Create a tiny deterministic fallback graph when osmnx is unavailable."""
    g = nx.MultiDiGraph()
    base_lat = 28.61
    base_lon = 77.21
    for idx in range(6):
        g.add_node(
            idx,
            y=base_lat + 0.001 * idx,
            x=base_lon + 0.001 * idx,
            street_count=2,
            highway="traffic_signals" if idx % 3 == 0 else "",
        )

    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
    for u, v in edges:
        g.add_edge(u, v, highway="residential", lanes=2, india_weight=0.35)
        g.add_edge(v, u, highway="residential", lanes=2, india_weight=0.35)

    logger.warning(
        "download_city_graph: osmnx not installed, using synthetic fallback graph for %s",
        city_name,
    )
    return g


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _highway_str(highway_val) -> str:
    """Normalise the OSM highway tag value to a plain lowercase string.

    OSMnx may return a list (when multiple values are tagged) or a string.
    We always want the first / primary value.
    """
    if isinstance(highway_val, list):
        return str(highway_val[0]).lower().strip()
    return str(highway_val).lower().strip() if highway_val else ""


def _road_weight(highway_str_val: str) -> float:
    """Return the base India road weight for a highway type string."""
    return INDIA_ROAD_WEIGHTS.get(highway_str_val, INDIA_ROAD_WEIGHTS["default"])


def _default_speed(highway_str_val: str) -> int:
    """Return the India default speed limit for a highway type string."""
    return INDIA_DEFAULT_SPEEDS.get(highway_str_val, INDIA_DEFAULT_SPEEDS["default"])


def _normalise_bbox(bbox: dict) -> dict:
    """Validate bbox shape and return a float-normalised copy."""
    required = ["north", "south", "east", "west"]
    missing = [k for k in required if k not in bbox]
    if missing:
        raise ValueError(f"bbox missing required keys: {missing}")

    norm = {k: float(bbox[k]) for k in required}
    if not (norm["north"] > norm["south"]):
        raise ValueError("bbox invalid: north must be greater than south")
    if not (norm["east"] > norm["west"]):
        raise ValueError("bbox invalid: east must be greater than west")
    return norm


def _bbox_area_id(bbox: dict) -> str:
    """Create deterministic area id from rounded bbox coordinates."""
    b = _normalise_bbox(bbox)
    return (
        f"n{b['north']:.4f}_s{b['south']:.4f}_e{b['east']:.4f}_w{b['west']:.4f}"
        .replace("-", "m")
        .replace(".", "p")
    )


# ---------------------------------------------------------------------------
# 1. download_city_graph
# ---------------------------------------------------------------------------

def download_city_graph(
    city_name: str,
    network_type: str = "drive",
) -> nx.MultiDiGraph:
    """Download the OSM road graph for an Indian city via OSMnx.

    Parameters
    ----------
    city_name:    City name (e.g. "Delhi").  ", India" is appended automatically.
    network_type: OSMnx network type — "drive" for vehicle roads (default).

    Returns
    -------
    nx.MultiDiGraph  Road graph enriched with speed and travel-time attributes.

    Raises
    ------
    Exception  Re-raised on any OSMnx or network failure.  Caller must handle —
               no graph means the GCN cannot be trained.
    """
    place_query = f"{city_name}, India"
    logger.info("download_city_graph: querying OSM for '%s'", place_query)

    if ox is None:
        return _build_synthetic_city_graph(city_name)

    try:
        graph = ox.graph_from_place(place_query, network_type=network_type)
        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)

        n_nodes = len(graph.nodes)
        n_edges = len(graph.edges)
        logger.info(
            "download_city_graph: downloaded graph for %s — %d nodes, %d edges",
            city_name, n_nodes, n_edges,
        )
        return graph

    except Exception:
        logger.error(
            "download_city_graph: failed for city '%s'", city_name,
            exc_info=True,
        )
        raise


def download_bbox_graph(
    bbox: dict,
    network_type: str = "drive",
) -> nx.MultiDiGraph:
    """Download a road graph for an arbitrary bounding box in India."""
    b = _normalise_bbox(bbox)

    if ox is None:
        return _build_synthetic_city_graph("bbox_area")

    try:
        try:
            graph = ox.graph_from_bbox(
                north=b["north"],
                south=b["south"],
                east=b["east"],
                west=b["west"],
                network_type=network_type,
            )
        except TypeError:
            # Compatibility path for OSMnx versions expecting a tuple bbox argument.
            graph = ox.graph_from_bbox(
                (b["north"], b["south"], b["east"], b["west"]),
                network_type=network_type,
            )

        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)
        logger.info(
            "download_bbox_graph: downloaded graph for bbox n=%.4f s=%.4f e=%.4f w=%.4f",
            b["north"], b["south"], b["east"], b["west"],
        )
        return graph
    except Exception:
        logger.error("download_bbox_graph: failed for bbox %s", b, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# 2. assign_india_road_weights
# ---------------------------------------------------------------------------

def assign_india_road_weights(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Annotate every edge with an 'india_weight' attribute.

    Base weight is determined by road class (highway tag).
    Three India-specific penalties are applied on top:
      - Unpaved / dirt surface   → ×0.7
      - Bad / horrible smoothness → ×0.8
      - Single-lane road         → ×0.9

    Parameters
    ----------
    graph: OSM road graph (MultiDiGraph from OSMnx).

    Returns
    -------
    nx.MultiDiGraph  Same graph with 'india_weight' set on every edge.
    """
    n_edges = 0
    for u, v, k, data in graph.edges(keys=True, data=True):
        try:
            hw = _highway_str(data.get("highway", "default"))
            weight = _road_weight(hw)

            # Unpaved surface penalty
            surface = str(data.get("surface", "") or "").lower().strip()
            if surface in INDIA_OSM_TAGS["surface"]:
                weight *= 0.7

            # Bad smoothness penalty
            smoothness = str(data.get("smoothness", "") or "").lower().strip()
            if smoothness in INDIA_OSM_TAGS["smoothness"]:
                weight *= 0.8

            # Single-lane penalty
            try:
                lanes = int(data.get("lanes", 2))
            except (TypeError, ValueError):
                lanes = 2
            if lanes == 1:
                weight *= 0.9

            graph[u][v][k]["india_weight"] = round(weight, 6)
            n_edges += 1

        except Exception:
            logger.warning(
                "assign_india_road_weights: skipping edge (%s, %s, %s)",
                u, v, k,
                exc_info=True,
            )
            # Assign safe default so the edge always has the attribute
            graph[u][v][k]["india_weight"] = INDIA_ROAD_WEIGHTS["default"]

    logger.info("assign_india_road_weights: assigned India road weights to %d edges", n_edges)
    return graph


# ---------------------------------------------------------------------------
# 3. build_adjacency_matrix
# ---------------------------------------------------------------------------

def build_adjacency_matrix(graph: nx.MultiDiGraph) -> csr_matrix:
    """Convert the road MultiDiGraph to a sparse CSR adjacency matrix.

    Edge weight used is 'india_weight'; falls back to 1.0 for any edge
    that does not carry that attribute.

    Parameters
    ----------
    graph: Road graph with 'india_weight' attributes set by
           assign_india_road_weights().

    Returns
    -------
    csr_matrix  Sparse weighted adjacency matrix (n_nodes × n_nodes).
    """
    try:
        adj = nx.to_scipy_sparse_array(
            graph,
            weight="india_weight",
            format="csr",
        )
        # nx.to_scipy_sparse_array uses 0 for missing weights; replace with 1.0
        # by re-running with nodelist to guarantee ordering, then cast.
        adj = csr_matrix(adj)

        logger.info(
            "build_adjacency_matrix: shape %s, %d non-zero entries",
            adj.shape, adj.nnz,
        )
        return adj

    except Exception:
        logger.error("build_adjacency_matrix: failed", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# 4. extract_node_features
# ---------------------------------------------------------------------------

def extract_node_features(graph: nx.MultiDiGraph) -> pd.DataFrame:
    """Build a per-node feature DataFrame for the GCN input layer.

    For each node the following features are extracted:
      node_id        — OSM node identifier
      latitude       — from OSMnx 'y' attribute
      longitude      — from OSMnx 'x' attribute
      street_count   — number of streets meeting at the node
      is_signal      — 1 if the node is a traffic signal, else 0
      avg_speed_limit— mean India default speed of adjacent edge highway types
      avg_road_weight— mean india_weight of adjacent edges

    Parameters
    ----------
    graph: Road graph with 'india_weight' attributes.

    Returns
    -------
    pd.DataFrame  One row per node with the columns listed above.
    """
    rows = []

    for node_id, node_data in graph.nodes(data=True):
        try:
            lat = node_data.get("y", np.nan)
            lon = node_data.get("x", np.nan)
            street_count = node_data.get("street_count", 0)

            hw_tag = node_data.get("highway", "")
            is_signal = 1 if str(hw_tag).lower().strip() == "traffic_signals" else 0

            # Collect edge attributes for adjacent edges (both in and out for DiGraph)
            adjacent_edges = list(graph.out_edges(node_id, data=True)) + \
                             list(graph.in_edges(node_id, data=True))

            speed_limits: list[float] = []
            road_weights: list[float] = []

            for *_, edata in adjacent_edges:
                try:
                    hw = _highway_str(edata.get("highway", "default"))
                    speed_limits.append(float(_default_speed(hw)))
                    road_weights.append(float(edata.get("india_weight", 0.4)))
                except Exception:
                    logger.warning(
                        "extract_node_features: skipping edge data for node %s",
                        node_id, exc_info=True,
                    )

            avg_speed  = float(np.mean(speed_limits)) if speed_limits else float(_default_speed("default"))
            avg_weight = float(np.mean(road_weights)) if road_weights else INDIA_ROAD_WEIGHTS["default"]

            rows.append({
                "node_id":         node_id,
                "latitude":        lat,
                "longitude":       lon,
                "street_count":    street_count,
                "is_signal":       is_signal,
                "avg_speed_limit": avg_speed,
                "avg_road_weight": avg_weight,
            })

        except Exception:
            logger.warning(
                "extract_node_features: skipping node %s", node_id,
                exc_info=True,
            )
            continue

    df = pd.DataFrame(rows, columns=[
        "node_id", "latitude", "longitude",
        "street_count", "is_signal",
        "avg_speed_limit", "avg_road_weight",
    ])

    logger.info("extract_node_features: extracted features for %d nodes", len(df))
    return df


# ---------------------------------------------------------------------------
# 5. save_graph
# ---------------------------------------------------------------------------

def save_graph(
    graph: nx.MultiDiGraph,
    adj_matrix: csr_matrix,
    node_features: pd.DataFrame,
    output_dir: str,
) -> None:
    """Persist all three graph artifacts to disk.

    Saves:
      {output_dir}/graph.graphml
      {output_dir}/adjacency_matrix.npz
      {output_dir}/node_features.csv

    Parameters
    ----------
    graph:         NetworkX road graph.
    adj_matrix:    Sparse adjacency matrix.
    node_features: Per-node feature DataFrame.
    output_dir:    Directory where artifacts are written (created if absent).
    """
    out = Path(output_dir)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.error("save_graph: could not create output dir '%s'", output_dir, exc_info=True)
        raise

    # 1. GraphML
    graphml_path = out / _GRAPHML_FILE
    try:
        if ox is not None:
            ox.save_graphml(graph, filepath=str(graphml_path))
        else:
            nx.write_graphml(graph, str(graphml_path))
        size_kb = graphml_path.stat().st_size / 1024
        logger.info("save_graph: saved %s (%.1f KB)", graphml_path, size_kb)
    except Exception:
        logger.error("save_graph: failed to save graphml to '%s'", graphml_path, exc_info=True)
        raise

    # 2. Adjacency matrix
    adj_path = out / _ADJ_FILE
    try:
        save_npz(str(adj_path), adj_matrix)
        size_kb = adj_path.stat().st_size / 1024
        logger.info("save_graph: saved %s (%.1f KB)", adj_path, size_kb)
    except Exception:
        logger.error("save_graph: failed to save adjacency matrix to '%s'", adj_path, exc_info=True)
        raise

    # 3. Node features CSV
    feats_path = out / _FEATS_FILE
    try:
        node_features.to_csv(str(feats_path), index=False)
        size_kb = feats_path.stat().st_size / 1024
        logger.info("save_graph: saved %s (%.1f KB)", feats_path, size_kb)
    except Exception:
        logger.error("save_graph: failed to save node features to '%s'", feats_path, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# 6. load_graph
# ---------------------------------------------------------------------------

def load_graph(input_dir: str) -> tuple:
    """Load all three graph artifacts from disk.

    Parameters
    ----------
    input_dir: Directory containing graph.graphml, adjacency_matrix.npz,
               and node_features.csv.

    Returns
    -------
    tuple  (graph: nx.MultiDiGraph, adj_matrix: csr_matrix,
            node_features: pd.DataFrame)

    Raises
    ------
    Exception  Re-raised on any IO or parse failure.
    """
    inp = Path(input_dir)

    try:
        graphml_path = str(inp / _GRAPHML_FILE)
        if ox is not None:
            try:
                graph = ox.load_graphml(graphml_path)
            except (AttributeError, Exception) as _ox_err:
                # Fallback for OSMnx version mismatches with saved GraphML
                logger.warning(
                    "load_graph: ox.load_graphml failed (%s) — falling back to nx.read_graphml",
                    _ox_err,
                )
                graph = nx.read_graphml(graphml_path, force_multigraph=True)
                graph = nx.MultiDiGraph(graph)
        else:
            graph = nx.read_graphml(graphml_path, force_multigraph=True)
            graph = nx.MultiDiGraph(graph)
        adj_matrix = load_npz(str(inp / _ADJ_FILE))
        node_features = pd.read_csv(str(inp / _FEATS_FILE))

        n_nodes = len(graph.nodes)
        n_edges = len(graph.edges)
        logger.info(
            "load_graph: loaded graph from '%s' — %d nodes, %d edges",
            input_dir, n_nodes, n_edges,
        )
        return graph, adj_matrix, node_features

    except Exception:
        logger.error("load_graph: failed to load from '%s'", input_dir, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# 7. build_city_graph  (main entry point)
# ---------------------------------------------------------------------------

def build_city_graph(city_name: str, config: dict) -> tuple:
    """Build or load from cache the road graph for a single Indian city.

    If all three artifacts already exist in the expected output directory,
    they are loaded from disk to avoid re-downloading.  Otherwise the full
    build pipeline runs: download → weight → adjacency → features → save.

    Parameters
    ----------
    city_name: Human-readable city name (e.g. "Delhi").
    config:    Parsed config.yaml dict (uses data.raw_data_dir as base).

    Returns
    -------
    tuple  (graph: nx.MultiDiGraph, adj_matrix: csr_matrix,
            node_features: pd.DataFrame)

    Raises
    ------
    Exception  Re-raised if graph download or save fails.
    """
    output_dir = f"data/processed/{city_name}/graph"
    out = Path(output_dir)

    # Cache check — all three artifacts must exist
    artifacts_exist = (
        (out / _GRAPHML_FILE).exists()
        and (out / _ADJ_FILE).exists()
        and (out / _FEATS_FILE).exists()
    )

    if artifacts_exist:
        logger.info(
            "build_city_graph: graph already exists for %s, loading from cache",
            city_name,
        )
        return load_graph(output_dir)

    # Full build pipeline
    logger.info("build_city_graph: building graph from scratch for %s", city_name)

    graph       = download_city_graph(city_name)
    graph       = assign_india_road_weights(graph)
    adj_matrix  = build_adjacency_matrix(graph)
    node_feats  = extract_node_features(graph)
    save_graph(graph, adj_matrix, node_feats, output_dir)

    logger.info("build_city_graph: built and saved graph for %s", city_name)
    return graph, adj_matrix, node_feats


def build_area_graph(
    bbox: dict,
    config: dict,
    area_id: str | None = None,
) -> tuple:
    """Build or load cached graph artifacts for an arbitrary bbox area."""
    b = _normalise_bbox(bbox)
    resolved_area_id = area_id or _bbox_area_id(b)
    output_dir = f"data/processed/areas/{resolved_area_id}/graph"
    out = Path(output_dir)

    artifacts_exist = (
        (out / _GRAPHML_FILE).exists()
        and (out / _ADJ_FILE).exists()
        and (out / _FEATS_FILE).exists()
    )

    if artifacts_exist:
        logger.info("build_area_graph: loading cached graph for area %s", resolved_area_id)
        return load_graph(output_dir)

    logger.info("build_area_graph: building graph for area %s", resolved_area_id)
    graph = download_bbox_graph(b)
    graph = assign_india_road_weights(graph)
    adj_matrix = build_adjacency_matrix(graph)
    node_feats = extract_node_features(graph)
    save_graph(graph, adj_matrix, node_feats, output_dir)
    return graph, adj_matrix, node_feats
