"""
Quick Neo4j health check for AISecKG GraphRAG.

Uses NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD (defaults: bolt://localhost:7687, neo4j, password).

Exit code: 0 if graph responds and has Entity nodes, 1 otherwise.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    try:
        from neo4j_graph_retriever import Neo4jGraphRetriever
    except ImportError as e:
        print("FAIL: could not import neo4j_graph_retriever:", e)
        return 1

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    print(f"Testing Neo4j at {uri} ...")
    r = Neo4jGraphRetriever()
    if not r.ok:
        print("FAIL: Neo4j driver could not connect (is the database started? password correct?).")
        print("  Start Neo4j Desktop / Aura, then import: python src/neo4j/neo4j_integration.py")
        return 1

    try:
        n = r._run("MATCH (e:Entity) RETURN count(e) AS c")
        rel = r._run("MATCH ()-[x]->() RETURN count(x) AS c")
        ec = n[0]["c"] if n else 0
        rc = rel[0]["c"] if rel else 0
        print(f"OK: Connected. Entities={ec}, relationships={rc}")
        if ec == 0:
            print("WARN: Graph is empty — run: python src/neo4j/neo4j_integration.py <uri> <user> <password>")
            r.close()
            return 1
    except Exception as e:
        print("FAIL: Query error:", e)
        r.close()
        return 1
    finally:
        r.close()

    print("Neo4j graph is working for GraphRAG retrieval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
