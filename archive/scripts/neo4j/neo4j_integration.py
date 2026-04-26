"""
neo4j_integration.py
====================
Imports the AISecKG Knowledge Graph into Neo4j.

Reads directly from the dataset files in this zip:
    data/knowledge_graph/all_entity_info.csv
    data/knowledge_graph/all_triples.csv
    data/knowledge_graph/all_relation_info.csv

Works with Neo4j Desktop (local) or Neo4j AuraDB (cloud free tier).

HOW TO RUN:
-----------
1. Install Neo4j Desktop from https://neo4j.com/download/
   OR create a free cloud database at https://neo4j.com/cloud/aura/

2. Install the Python driver:
      pip install neo4j

3. Start your Neo4j database and note your password.

4. Run from the project root:
      python src/neo4j/neo4j_integration.py

   Or with custom credentials:
      python src/neo4j/neo4j_integration.py bolt://localhost:7687 neo4j yourpassword

5. Open Neo4j Browser at http://localhost:7474 to explore the graph.

WHAT GETS IMPORTED:
-------------------
  - 963 Entity nodes, each labeled with:
      * entityType (tool, attack, technique, feature, data, system, app, function...)
      * entityCategory (concept, application, role)
      * NIST CSF function (IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER, GOVERN)
      * MITRE ATT&CK tactic name
      * Bloom's Taxonomy level (1-6) and difficulty (beginner/intermediate/advanced)
      * Prerequisite concepts
  - 729 Relationships (typed by relation: USES, CAN_DETECT, CAN_EXPLOIT, etc.)
  - Full-text search index on entity name and description
  - Indexes on type, difficulty, NIST function for fast filtering

SAMPLE CYPHER QUERIES (paste in Neo4j Browser):
-----------------------------------------------
# See everything connected to Snort:
MATCH (n:Entity {name: 'Snort'})-[r]-(m) RETURN n, r, m

# All detection tools:
MATCH (n:Entity {nist_csf: 'DETECT', type: 'tool'}) RETURN n.name, n.difficulty

# Multi-hop: tools that detect attacks that exploit vulnerabilities:
MATCH (t:Entity)-[:CAN_DETECT]->(a)-[:CAN_EXPLOIT]->(v)
RETURN t.name AS tool, a.name AS attack, v.name AS vulnerability

# NIST CSF coverage breakdown:
MATCH (n:Entity) RETURN n.nist_csf, count(n) AS count ORDER BY count DESC

# Advanced-level entities by MITRE tactic:
MATCH (n:Entity {difficulty: 'advanced'})
WHERE n.mitre_tactic <> ''
RETURN n.mitre_tactic, collect(n.name) AS entities

# Full-text search (after running the integration script):
CALL db.index.fulltext.queryNodes('entity_search', 'intrusion detection')
YIELD node, score RETURN node.name, node.type, score ORDER BY score DESC LIMIT 10
"""

import csv
import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("Neo4jIntegration")

# ── Paths ──────────────────────────────────────────────────────────────────────
# Works whether run from src/neo4j/ or project root
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent          # AISecKG-cybersecurity-dataset-main/
DATA_KG = PROJECT_ROOT / "data" / "knowledge_graph"

ENTITY_CSV  = DATA_KG / "all_entity_info.csv"
TRIPLES_CSV = DATA_KG / "all_triples.csv"
RELATION_CSV = DATA_KG / "all_relation_info.csv"


# ── Ontology mappings (inline so no extra imports needed) ──────────────────────

# NIST CSF 2.0 keyword -> function mapping
NIST_KEYWORDS = {
    "DETECT":   ["detect","monitor","ids","snort","alert","anomaly","scan","nmap","intrusion","log"],
    "PROTECT":  ["firewall","encrypt","authenticate","access control","vpn","ssl","tls","protect","hash","password","certificate"],
    "RESPOND":  ["respond","incident","patch","mitigate","contain","forensic","investigate"],
    "IDENTIFY": ["identify","vulnerability","cve","risk","asset","audit","assessment","reconnaissance"],
    "GOVERN":   ["policy","governance","compliance","regulation","cissp","standard","management"],
    "RECOVER":  ["recover","backup","restore","continuity","resilience"],
}

# MITRE ATT&CK tactic keyword mapping
MITRE_KEYWORDS = {
    "Discovery":           ["scan","nmap","enumerate","recon","discover"],
    "Initial Access":      ["phishing","exploit","access","entry","vulnerability"],
    "Defense Evasion":     ["evade","bypass","obfuscate","stealth","hide"],
    "Credential Access":   ["password","credential","hash","kerberos","token"],
    "Execution":           ["execute","payload","script","command","run"],
    "Persistence":         ["persist","backdoor","startup","registry"],
    "Privilege Escalation":["escalate","privilege","root","admin","sudo"],
    "Lateral Movement":    ["lateral","pivot","spread","remote"],
    "Command and Control": ["c2","botnet","rat","beacon","tunnel"],
    "Impact":              ["ransomware","destroy","disrupt","encrypt","wipe","dos"],
    "Collection":          ["collect","capture","keylog","screenshot","exfil"],
}

# Bloom's level by entity type
BLOOMS_BY_TYPE = {
    "tool": 3, "attack": 4, "technique": 4,
    "feature": 2, "data": 2, "system": 3,
    "app": 3, "function": 3, "vulnerability": 4,
    "attacker": 4, "securityTeam": 3, "user": 2,
}

DIFFICULTY = {1: "beginner", 2: "beginner", 3: "intermediate",
              4: "intermediate", 5: "advanced", 6: "advanced"}

PREREQS = {
    "tool":          "networking, operating systems, command line",
    "attack":        "networking, vulnerabilities, CIA triad",
    "technique":     "networking, protocols",
    "vulnerability": "CIA triad, risk management",
    "system":        "operating systems, networking",
    "feature":       "basic computing",
    "data":          "networking, data formats",
    "app":           "operating systems, networking",
    "function":      "networking, security concepts",
    "attacker":      "networking, attack taxonomy",
    "securityTeam":  "security operations, incident response",
    "user":          "basic computing",
}


def _map_nist(text: str) -> str:
    scores = {fn: sum(1 for kw in kws if kw in text)
              for fn, kws in NIST_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "IDENTIFY"


def _map_mitre(text: str) -> str:
    scores = {t: sum(1 for kw in kws if kw in text)
              for t, kws in MITRE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""


def _enrich_entity(row: Dict) -> Dict:
    """Add ontology labels to a raw entity CSV row."""
    name  = row.get("entityName", "").strip()
    etype = row.get("entityType", "feature").strip()
    desc  = str(row.get("entityDescription", "") or "").strip()
    text  = f"{name} {etype} {desc}".lower()

    bl = BLOOMS_BY_TYPE.get(etype, 2)
    return {
        **row,
        "nist_csf":      _map_nist(text),
        "mitre_tactic":  _map_mitre(text),
        "blooms_level":  bl,
        "difficulty":    DIFFICULTY[bl],
        "prerequisites": PREREQS.get(etype, "basic computing"),
        "description":   desc or f"Cybersecurity {etype}: {name}",
        "framework_tags": f"NIST:{_map_nist(text)} BLOOM:{bl} UCO:{etype}",
    }


# ── Neo4j helpers ──────────────────────────────────────────────────────────────

def _rel_type(relation: str) -> str:
    """Convert relation string to a valid Neo4j relationship type."""
    return relation.upper().replace(" ", "_").replace("-", "_")


# ── Main connector ─────────────────────────────────────────────────────────────

class AISecKGNeo4j:
    """
    Imports the full AISecKG knowledge graph into Neo4j.

    Usage:
        conn = AISecKGNeo4j(uri, user, password)
        conn.run_full_import()
        conn.print_stats()
        conn.close()
    """

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "password"):
        self.uri      = uri
        self.user     = user
        self.password = password
        self.driver   = None
        self._connect()

    # ── connection ────────────────────────────────────────────

    def _connect(self):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            log.info(f"Connected to Neo4j at {self.uri}")
        except ImportError:
            log.error("neo4j package not installed. Run:  pip install neo4j")
            self.driver = None
        except Exception as e:
            log.error(f"Neo4j connection failed: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def is_connected(self) -> bool:
        return self.driver is not None

    def _run(self, query: str, params: dict = None) -> list:
        if not self.driver:
            return []
        with self.driver.session() as session:
            return list(session.run(query, params or {}))

    # ── setup ─────────────────────────────────────────────────

    def create_constraints_and_indexes(self):
        """Create uniqueness constraint and search indexes."""
        statements = [
            # Uniqueness constraint (also creates an index)
            "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            # Property indexes for fast filtering
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_nist IF NOT EXISTS FOR (e:Entity) ON (e.nist_csf)",
            "CREATE INDEX entity_diff IF NOT EXISTS FOR (e:Entity) ON (e.difficulty)",
            "CREATE INDEX entity_blooms IF NOT EXISTS FOR (e:Entity) ON (e.blooms_level)",
        ]
        for stmt in statements:
            try:
                self._run(stmt)
            except Exception as ex:
                log.debug(f"Index/constraint (may already exist): {ex}")

        # Full-text index (requires Neo4j 3.5+)
        try:
            self._run(
                "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS "
                "FOR (e:Entity) ON EACH [e.name, e.description, e.mitre_tactic, e.nist_csf]"
            )
            log.info("Full-text index created")
        except Exception as ex:
            log.debug(f"Full-text index: {ex}")

    def clear_graph(self):
        """Wipe all nodes and relationships (use with care)."""
        self._run("MATCH (n) DETACH DELETE n")
        log.info("Graph cleared")

    # ── import ────────────────────────────────────────────────

    def import_entities(self) -> int:
        """Read all_entity_info.csv and create/merge Entity nodes."""
        if not ENTITY_CSV.exists():
            log.error(f"Entity CSV not found: {ENTITY_CSV}")
            return 0

        count = 0
        with open(ENTITY_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            enriched = _enrich_entity(row)
            query = """
            MERGE (e:Entity {name: $name})
            SET e.entity_id    = $entity_id,
                e.type         = $type,
                e.category     = $category,
                e.description  = $description,
                e.nist_csf     = $nist_csf,
                e.mitre_tactic = $mitre_tactic,
                e.blooms_level = $blooms_level,
                e.difficulty   = $difficulty,
                e.prerequisites= $prerequisites,
                e.framework_tags = $framework_tags
            """
            params = {
                "name":          enriched.get("entityName", "").strip(),
                "entity_id":     enriched.get("entityID", ""),
                "type":          enriched.get("entityType", "feature").strip(),
                "category":      enriched.get("entityCategory", "concept").strip(),
                "description":   enriched.get("description", ""),
                "nist_csf":      enriched.get("nist_csf", "IDENTIFY"),
                "mitre_tactic":  enriched.get("mitre_tactic", ""),
                "blooms_level":  int(enriched.get("blooms_level", 2)),
                "difficulty":    enriched.get("difficulty", "beginner"),
                "prerequisites": enriched.get("prerequisites", ""),
                "framework_tags":enriched.get("framework_tags", ""),
            }
            if params["name"]:
                self._run(query, params)
                count += 1

        log.info(f"Imported {count} entity nodes")
        return count

    def import_triples(self) -> Tuple[int, int]:
        """
        Read all_triples.csv and create typed relationships.
        Each relation (uses, can_detect, etc.) becomes a Neo4j relationship type.
        Returns (success_count, error_count).
        """
        if not TRIPLES_CSV.exists():
            log.error(f"Triples CSV not found: {TRIPLES_CSV}")
            return 0, 0

        success = error = 0
        with open(TRIPLES_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            e1 = row.get("e1", "").strip()
            r  = row.get("r", "").strip()
            e2 = row.get("e2", "").strip()
            if not (e1 and r and e2):
                continue

            rel = _rel_type(r)
            # Dynamic relationship type requires string interpolation in Cypher
            query = f"""
            MERGE (a:Entity {{name: $e1}})
            MERGE (b:Entity {{name: $e2}})
            MERGE (a)-[rel:{rel}]->(b)
            SET rel.original = $r
            """
            try:
                self._run(query, {"e1": e1, "e2": e2, "r": r})
                success += 1
            except Exception as ex:
                error += 1
                if error <= 3:
                    log.debug(f"Triple error ({e1})-[{r}]->({e2}): {ex}")

        log.info(f"Imported {success} relationships ({error} errors)")
        return success, error

    # ── full pipeline ─────────────────────────────────────────

    def run_full_import(self, clear_first: bool = False):
        """Run the complete import pipeline."""
        print("\n" + "=" * 60)
        print("AISecKG -> Neo4j Import")
        print("=" * 60)

        if clear_first:
            self.clear_graph()

        print("\n[1/3] Creating indexes and constraints...")
        self.create_constraints_and_indexes()

        print("[2/3] Importing entities...")
        n_entities = self.import_entities()

        print("[3/3] Importing relationships...")
        n_rels, n_err = self.import_triples()

        print("\n" + "=" * 60)
        print(f"Import complete!")
        print(f"  Nodes created   : {n_entities}")
        print(f"  Relationships   : {n_rels}")
        print(f"  Errors          : {n_err}")
        print("=" * 60)

    # ── stats + queries ───────────────────────────────────────

    def print_stats(self):
        """Print summary statistics about the imported graph."""
        n_nodes = self._run("MATCH (n:Entity) RETURN count(n) AS c")
        n_rels  = self._run("MATCH ()-[r]->() RETURN count(r) AS c")
        print(f"\nGraph Statistics")
        print(f"  Total nodes        : {n_nodes[0]['c'] if n_nodes else 'N/A'}")
        print(f"  Total relationships: {n_rels[0]['c'] if n_rels else 'N/A'}")

        print("\nNIST CSF Coverage:")
        rows = self._run(
            "MATCH (n:Entity) RETURN n.nist_csf AS fn, count(n) AS c "
            "ORDER BY c DESC"
        )
        for row in rows:
            print(f"  {str(row['fn']):12s} : {row['c']} entities")

        print("\nDifficulty Distribution:")
        rows = self._run(
            "MATCH (n:Entity) RETURN n.difficulty AS d, count(n) AS c "
            "ORDER BY n.blooms_level"
        )
        for row in rows:
            print(f"  {str(row['d']):14s} : {row['c']} entities")

        print("\nRelationship Types:")
        rows = self._run(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c "
            "ORDER BY c DESC"
        )
        for row in rows:
            print(f"  {str(row['t']):20s} : {row['c']}")

    def search(self, query_text: str, limit: int = 10) -> List[Dict]:
        """Full-text entity search."""
        cypher = """
        CALL db.index.fulltext.queryNodes('entity_search', $q)
        YIELD node, score
        RETURN node.name AS name, node.type AS type,
               node.nist_csf AS nist_csf,
               node.difficulty AS difficulty,
               score
        LIMIT $limit
        """
        try:
            rows = self._run(cypher, {"q": query_text, "limit": limit})
            return [dict(r) for r in rows]
        except Exception as ex:
            log.warning(f"Full-text search failed: {ex}")
            return []

    def get_entity_neighborhood(self, entity_name: str, hops: int = 2) -> List[Dict]:
        """Return all entities within N hops."""
        cypher = f"""
        MATCH path = (s:Entity {{name: $name}})-[*1..{hops}]-(n)
        RETURN DISTINCT n.name AS name, n.type AS type,
               n.nist_csf AS nist_csf, n.difficulty AS difficulty
        LIMIT 50
        """
        return [dict(r) for r in self._run(cypher, {"name": entity_name})]

    def get_qa_context(self, entities: List[str]) -> List[Dict]:
        """Get triples for a list of entities (used by QA pipeline)."""
        cypher = """
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE a.name IN $names OR b.name IN $names
        RETURN a.name AS subject, type(r) AS relation, b.name AS object,
               a.nist_csf AS subject_nist, b.difficulty AS object_difficulty
        LIMIT 30
        """
        return [dict(r) for r in self._run(cypher, {"names": entities})]

    def export_to_json(self, output_path: str = None) -> str:
        """Export the full graph as JSON from Neo4j."""
        if output_path is None:
            output_path = str(PROJECT_ROOT / "data" / "neo4j_export.json")

        nodes_q = """
        MATCH (n:Entity)
        RETURN n.name AS name, n.type AS type, n.category AS category,
               n.description AS description, n.nist_csf AS nist_csf,
               n.mitre_tactic AS mitre_tactic, n.blooms_level AS blooms_level,
               n.difficulty AS difficulty, n.prerequisites AS prerequisites,
               n.framework_tags AS framework_tags
        """
        edges_q = """
        MATCH (a:Entity)-[r]->(b:Entity)
        RETURN a.name AS source, type(r) AS relation, b.name AS target
        """
        nodes = [dict(r) for r in self._run(nodes_q)]
        edges = [dict(r) for r in self._run(edges_q)]

        export = {
            "metadata": {
                "source": "AISecKG -> Neo4j Export",
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "frameworks": ["NIST-CSF-2.0", "MITRE-ATT&CK", "Bloom's Taxonomy"]
            },
            "nodes": nodes,
            "edges": edges
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)
        log.info(f"Graph exported to {output_path}")
        return output_path


# ── CLI entry point ────────────────────────────────────────────────────────────

def main():
    uri      = sys.argv[1] if len(sys.argv) > 1 else os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user     = sys.argv[2] if len(sys.argv) > 2 else os.getenv("NEO4J_USER", "neo4j")
    password = sys.argv[3] if len(sys.argv) > 3 else os.getenv("NEO4J_PASSWORD", "password")

    print(f"\nConnecting to Neo4j at {uri} as '{user}'...")
    conn = AISecKGNeo4j(uri=uri, user=user, password=password)

    if not conn.is_connected():
        print("\nCould not connect. Make sure Neo4j is running.")
        print("  Download Neo4j Desktop: https://neo4j.com/download/")
        print("  Free cloud DB:          https://neo4j.com/cloud/aura/")
        print(f"\n  Expected URI:  {uri}")
        print(f"  Expected user: {user}")
        print("\n  Then re-run:  python src/neo4j/neo4j_integration.py")
        sys.exit(1)

    conn.run_full_import(clear_first=False)
    conn.print_stats()

    # Export JSON from Neo4j
    out = conn.export_to_json()
    print(f"\nJSON export saved to: {out}")

    print("\nSample Cypher queries for Neo4j Browser (http://localhost:7474):")
    print("  MATCH (n {name: 'Snort'})-[r]-(m) RETURN n, r, m")
    print("  MATCH (n:Entity {nist_csf: 'DETECT'}) RETURN n.name, n.type LIMIT 20")
    print("  MATCH (a)-[:CAN_DETECT]->(b)-[:CAN_EXPLOIT]->(c) RETURN a.name,b.name,c.name LIMIT 10")
    print("  CALL db.index.fulltext.queryNodes('entity_search', 'intrusion') YIELD node RETURN node.name")

    conn.close()


if __name__ == "__main__":
    main()
