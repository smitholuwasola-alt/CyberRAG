"""
Neo4j-backed subgraph retrieval for GraphRAG.

Uses the same schema as ``neo4j/neo4j_integration.py`` (:Entity, typed relationships).

Environment (defaults for local Desktop):
  NEO4J_URI      default bolt://localhost:7687
  NEO4J_USER     default neo4j
  NEO4J_PASSWORD default password

Requires: pip install neo4j
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


def _tokens(question: str, max_tokens: int = 12) -> List[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", question.lower())
    stop = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our", "out",
        "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who",
        "way", "use", "that", "with", "from", "this", "what", "when", "which", "your", "into", "than",
        "then", "them", "these", "those", "about", "after", "before", "being", "each", "have", "here",
        "does", "did", "such", "only", "also", "some", "very", "just", "like", "most", "more", "much",
    }
    out = [t for t in raw if t not in stop]
    return out[:max_tokens]


def _rel_to_canonical(rel_type: str) -> str:
    """Neo4j stores USES, CAN_DETECT — map to lowercase underscore for scoring alignment."""
    return rel_type.lower().replace(" ", "_")


class Neo4jGraphRetriever:
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.driver = None
        self._connect()

    def _connect(self) -> None:
        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
        except Exception:
            self.driver = None

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.driver = None

    @property
    def ok(self) -> bool:
        return self.driver is not None

    def _run(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.driver:
            return []
        params = params or {}
        with self.driver.session() as session:
            result = session.run(cypher, params)
            return [dict(r) for r in result]

    def _fulltext_seeds(self, question: str, limit: int) -> List[Tuple[str, float]]:
        q = question.strip()
        if len(q) > 200:
            q = q[:200]
        cypher = """
        CALL db.index.fulltext.queryNodes('entity_search', $q)
        YIELD node, score
        RETURN node.name AS name, score AS score
        LIMIT $limit
        """
        try:
            rows = self._run(cypher, {"q": q, "limit": limit})
            return [(str(r["name"]), float(r["score"])) for r in rows if r.get("name")]
        except Exception:
            return []

    def _token_seeds(self, tokens: List[str], limit: int) -> List[Tuple[str, float]]:
        if not tokens:
            return []
        cypher = """
        UNWIND $tokens AS t
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS t OR toLower(e.description) CONTAINS t
        RETURN e.name AS name, count(*) AS c
        ORDER BY c DESC
        LIMIT $limit
        """
        rows = self._run(cypher, {"tokens": tokens, "limit": limit})
        return [(str(r["name"]), float(r["c"])) for r in rows if r.get("name")]

    def _merge_seed_scores(self, *lists: List[Tuple[str, float]], cap: int) -> List[Tuple[str, float]]:
        acc: Dict[str, float] = {}
        for lst in lists:
            for name, sc in lst:
                acc[name] = acc.get(name, 0.0) + float(sc)
        ranked = sorted(acc.items(), key=lambda x: -x[1])
        return ranked[:cap]

    def _neighborhood(self, names: List[str], rel_limit: int) -> List[Tuple[str, str, str]]:
        if not names or not self.driver:
            return []
        cypher = """
        UNWIND $names AS nm
        MATCH (s:Entity {name: nm})-[r]-(o:Entity)
        RETURN DISTINCT s.name AS e1, type(r) AS rt, o.name AS e2
        LIMIT $lim
        """
        rows = self._run(cypher, {"names": names, "lim": rel_limit})
        triples: List[Tuple[str, str, str]] = []
        for r in rows:
            e1, rt, e2 = r.get("e1"), r.get("rt"), r.get("e2")
            if e1 and rt and e2:
                triples.append((str(e1), _rel_to_canonical(str(rt)), str(e2)))
        return triples

    def retrieve(
        self,
        question: str,
        *,
        seed_limit: int = 14,
        rel_limit: int = 70,
        relation_intents: Optional[Set[str]] = None,
        relevant_kas: Optional[List[Tuple[str, float]]] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Returns (context_text, evidence_strings, meta_dict) compatible with GraphRAGOllama.answer_from_context.
        """
        if not self.ok:
            return "", [], {
                "triple_count": 0,
                "ranked_entities": [],
                "top_entity_score": 0.0,
                "relation_intents": sorted(relation_intents or []),
                "relevant_kas": [k[0] for k in (relevant_kas or [])][:3],
                "backend": "neo4j_offline",
                "traversal": "none",
                "path_lines": [],
                "traversal_traces": [],
                "inter_entity_paths": [],
            }

        tokens = _tokens(question)
        ft = self._fulltext_seeds(question, seed_limit)
        tk = self._token_seeds(tokens, seed_limit)
        ranked = self._merge_seed_scores(ft, tk, seed_limit)
        seed_names = [n for n, _ in ranked[:10]]

        triples = self._neighborhood(seed_names, rel_limit)
        seen = set()
        unique: List[Tuple[str, str, str]] = []
        for t in triples:
            k = (t[0].lower(), t[1], t[2].lower())
            if k not in seen:
                seen.add(k)
                unique.append(t)

        intents = set(relation_intents or [])
        if intents:
            unique.sort(
                key=lambda tr: (0 if tr[1] in intents else 1, -len(tr[0]) - len(tr[2]))
            )

        lines: List[str] = []
        lines.append("Source: Neo4j knowledge graph (AISecKG import).")
        if relevant_kas:
            lines.append("CyBOK knowledge-area hints: " + ", ".join(k[0] for k in relevant_kas[:3]))
        lines.append("Seeded entities (retrieval score): " + ", ".join(f"{n} ({s:.2f})" for n, s in ranked[:12]))
        lines.append("Triples (subject — relation — object):")
        for e1, r, e2 in unique[:55]:
            lines.append(f"  - {e1} — {r.replace('_', ' ')} — {e2}")

        ctx = "\n".join(lines)
        evidence = [f"{a} {r} {b}" for a, r, b in unique[:18]]
        top_score = float(ranked[0][1]) if ranked else 0.0
        path_lines = [
            f"{e1} —[{str(rt).replace('_', ' ')}]→ {e2}" for e1, rt, e2 in unique[:40]
        ]
        meta: Dict[str, Any] = {
            "relevant_kas": [k[0] for k in (relevant_kas or [])][:3],
            "ranked_entities": ranked[:15],
            "triple_count": len(unique),
            "relation_intents": sorted(intents),
            "top_entity_score": top_score,
            "backend": "neo4j",
            "traversal": "neo4j",
            "neo4j_seeds": seed_names,
            "path_lines": path_lines,
            "traversal_traces": [],
            "inter_entity_paths": [],
        }
        return ctx, evidence, meta
