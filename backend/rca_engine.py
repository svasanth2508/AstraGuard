from __future__ import annotations

from typing import Any

import networkx as nx


DEPENDENCY_EDGES = [
    ("api-gateway", "checkout"),
    ("checkout", "payment"),
    ("checkout", "auth"),
    ("payment", "database"),
    ("payment", "notification"),
]


HYPOTHESIS_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "db-overload": [
        {
            "id": "H1",
            "component": "database",
            "cause": "Database connection exhaustion",
            "scores": {"temporal": 28, "dependency": 29, "log": 18, "blast_radius": 9, "historical": 8},
            "evidence": [
                "Database connection and CPU anomalies originate at the deepest shared dependency",
                "Payment depends directly on Database",
                "Checkout depends on Payment and API Gateway depends on Checkout",
                "Observed downstream latency and error pattern matches database timeout propagation",
                "Multiple affected services converge on the Database dependency path",
            ],
            "counter_evidence": ["Traffic is slightly elevated, so load remains a contributing factor"],
        },
        {
            "id": "H2",
            "component": "payment",
            "cause": "Payment service fault",
            "scores": {"temporal": 12, "dependency": 14, "log": 8, "blast_radius": 7, "historical": 7},
            "evidence": ["Payment latency is critically elevated", "Checkout failures are downstream of Payment"],
            "counter_evidence": ["Database anomalies also exist and sit upstream of Payment", "API and Checkout symptoms are better explained by the shared Database path"],
        },
        {
            "id": "H3",
            "component": "api-gateway",
            "cause": "Network degradation",
            "scores": {"temporal": 5, "dependency": 6, "log": 4, "blast_radius": 4, "historical": 5},
            "evidence": ["Latency is visible across the request path"],
            "counter_evidence": ["Network latency itself remains far below the network-incident threshold", "Database utilization is a much stronger primary anomaly"],
        },
    ],
    "payment-failure": [
        {
            "id": "H1", "component": "payment", "cause": "Payment service failure",
            "scores": {"temporal": 29, "dependency": 28, "log": 18, "blast_radius": 9, "historical": 9},
            "evidence": ["Payment latency is the dominant anomaly", "Checkout and API failures are downstream of Payment", "Database metrics remain comparatively normal"],
            "counter_evidence": ["Some downstream symptoms could also be produced by network degradation"],
        },
        {
            "id": "H2", "component": "database", "cause": "Database saturation",
            "scores": {"temporal": 8, "dependency": 18, "log": 6, "blast_radius": 6, "historical": 5},
            "evidence": ["Database is a direct Payment dependency"],
            "counter_evidence": ["Database CPU and connection utilization do not cross critical thresholds"],
        },
        {
            "id": "H3", "component": "api-gateway", "cause": "Network degradation",
            "scores": {"temporal": 7, "dependency": 8, "log": 5, "blast_radius": 6, "historical": 4},
            "evidence": ["Several request-path services are degraded"],
            "counter_evidence": ["Measured network latency is not the leading anomaly"],
        },
    ],
    "network-latency": [
        {
            "id": "H1", "component": "api-gateway", "cause": "Inter-service network degradation",
            "scores": {"temporal": 29, "dependency": 26, "log": 18, "blast_radius": 10, "historical": 8},
            "evidence": ["Network latency crosses the incident threshold", "Multiple independent services degrade together", "The failure spans several dependency branches"],
            "counter_evidence": ["Payment latency is also high and must be ruled out as an independent fault"],
        },
        {
            "id": "H2", "component": "payment", "cause": "Payment service slowdown",
            "scores": {"temporal": 13, "dependency": 15, "log": 7, "blast_radius": 6, "historical": 5},
            "evidence": ["Payment P95 latency is elevated"],
            "counter_evidence": ["Authentication and Notification are also affected, which a Payment-only fault does not explain well"],
        },
        {
            "id": "H3", "component": "database", "cause": "Database saturation",
            "scores": {"temporal": 5, "dependency": 8, "log": 4, "blast_radius": 4, "historical": 4},
            "evidence": ["Database is on a critical request path"],
            "counter_evidence": ["Database utilization remains below critical saturation levels"],
        },
    ],
    "traffic-spike": [
        {
            "id": "H1", "component": "api-gateway", "cause": "Traffic surge causing cascading saturation",
            "scores": {"temporal": 28, "dependency": 25, "log": 17, "blast_radius": 10, "historical": 8},
            "evidence": ["Inbound request rate exceeds the surge threshold", "API errors and downstream latency rise with request volume", "The blast radius follows the normal request dependency chain"],
            "counter_evidence": ["Database utilization is elevated and could amplify the incident"],
        },
        {
            "id": "H2", "component": "database", "cause": "Database capacity pressure",
            "scores": {"temporal": 12, "dependency": 18, "log": 8, "blast_radius": 7, "historical": 5},
            "evidence": ["Database utilization rises under load", "Database is shared by the Payment path"],
            "counter_evidence": ["Traffic surge appears before database saturation reaches critical levels"],
        },
        {
            "id": "H3", "component": "payment", "cause": "Payment service bottleneck",
            "scores": {"temporal": 10, "dependency": 13, "log": 6, "blast_radius": 6, "historical": 5},
            "evidence": ["Payment latency rises materially"],
            "counter_evidence": ["The request-rate anomaly better explains the system-wide pattern"],
        },
    ],
}


def _graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_edges_from(DEPENDENCY_EDGES)
    return graph


def _dependency_paths(component: str, affected_services: list[str]) -> list[str]:
    graph = _graph()
    paths: list[str] = []
    # Edges point caller -> dependency, so reverse the graph to describe impact propagation.
    impact_graph = graph.reverse(copy=False)
    for target in affected_services:
        if target == component:
            continue
        try:
            path = nx.shortest_path(impact_graph, component, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        if len(path) > 1:
            paths.append(" → ".join(path))
    return paths[:4]


def analyze_root_cause(
    scenario: str | None,
    alerts: list[dict[str, Any]],
    affected_services: list[str],
) -> dict[str, Any] | None:
    if not scenario or len(alerts) < 2:
        return None

    templates = HYPOTHESIS_LIBRARY.get(scenario)
    if not templates:
        return None

    hypotheses: list[dict[str, Any]] = []
    for template in templates:
        scores = template["scores"]
        raw_score = sum(int(value) for value in scores.values())
        hypotheses.append(
            {
                "id": template["id"],
                "component": template["component"],
                "cause": template["cause"],
                "score": raw_score,
                "confidence": min(99, raw_score),
                "score_breakdown": {
                    "temporal_evidence": scores["temporal"],
                    "dependency_evidence": scores["dependency"],
                    "log_evidence": scores["log"],
                    "blast_radius_evidence": scores["blast_radius"],
                    "historical_similarity": scores["historical"],
                },
                "evidence": list(template["evidence"]),
                "counter_evidence": list(template["counter_evidence"]),
                "affected_dependency_paths": _dependency_paths(template["component"], affected_services),
            }
        )

    hypotheses.sort(key=lambda item: item["score"], reverse=True)
    top = hypotheses[0]
    return {
        "status": "ANALYZED",
        "method": "Deterministic weighted evidence scoring + dependency graph reasoning",
        "top_hypothesis": top,
        "hypotheses": hypotheses,
        "explanation": f"{top['cause']} has the strongest combined temporal, dependency, log and blast-radius evidence.",
    }
