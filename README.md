# AISecKG — Cybersecurity Knowledge Graph Dataset

Refer to Paper:
### [AISecKG: Knowledge Graph Dataset for Cybersecurity Education](https://ceur-ws.org/Vol-3433/paper6.pdf)

- Named-entity annotated dataset for cybersecurity entities
- Triple dataset to create knowledge graphs for cybersecurity education
- BERT model to extract custom named entities
- **Neo4j integration** to explore the graph visually

---

## Ontology Views

**User View:**
![ontology_user_view](https://user-images.githubusercontent.com/54346120/223224352-f4c5dfea-b843-4ecb-908b-62f1fd51faa5.png)

**Attacker View:**
![ontology_attacker_view](https://user-images.githubusercontent.com/54346120/223224642-64b6c708-cbec-4711-a69f-3bfce73388d7.png)

**Security View:**
![ontology_security_view](https://user-images.githubusercontent.com/54346120/223224862-d858feba-0947-4b99-97b9-6712751b2f34.png)

---

## Project Structure

```
AISecKG-cybersecurity-dataset-main/
├── src/
│   ├── kg_builder.py               # Builds NetworkX KG from CSV files
│   ├── query_engine.py             # Answers questions using the KG
│   ├── main_pipeline.py            # End-to-end pipeline
│   ├── answer_cissp_questions.py   # CISSP question answering
│   ├── neo4j/
│   │   ├── neo4j_integration.py    # ← NEW: Import KG into Neo4j
│   │   └── __init__.py
│   └── scraper/
│       └── cissp_scraper.py
├── data/
│   ├── knowledge_graph/
│   │   ├── all_entity_info.csv     # 963 entities with type/category
│   │   ├── all_triples.csv         # 729 (subject, relation, object) triples
│   │   └── all_relation_info.csv   # 9 relation types
│   ├── datasource/                 # 6 original university lab documents
│   └── qa/                         # CISSP + EB guide questions and answers
├── models/
│   ├── kg/                         # KG notebooks and visualizations
│   └── ner/                        # BERT NER model files
├── ontology/                       # Ontology description and diagrams
└── requirements.txt
```

---

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Build the Knowledge Graph

```bash
python src/kg_builder.py
```

### 3. Answer Questions

```bash
python src/main_pipeline.py
```

---

## Neo4j Integration (New)

Explore the knowledge graph visually in Neo4j Browser.

### Step 1 — Get Neo4j

**Option A: Neo4j Desktop (local, recommended for development)**
1. Download from https://neo4j.com/download/
2. Install and open Neo4j Desktop
3. Click **New** → **Create project** → **Add** → **Local DBMS**
4. Set a password (you will need it below)
5. Click **Start**

**Option B: Neo4j AuraDB (free cloud database)**
1. Go to https://neo4j.com/cloud/platform/aura-graph-database/
2. Click **Start Free**
3. Create a free instance
4. Save the connection URI and password shown on screen

### Step 2 — Install the driver

```bash
pip install neo4j
```

### Step 3 — Run the import

```bash
# Local Neo4j (default password is "password" - change to yours)
python src/neo4j/neo4j_integration.py

# Custom credentials
python src/neo4j/neo4j_integration.py bolt://localhost:7687 neo4j yourpassword

# AuraDB
python src/neo4j/neo4j_integration.py neo4j+s://xxxx.databases.neo4j.io neo4j yourAuraPassword
```

**Or from Python:**

```python
from src.kg_builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder()
kg.build_graph()
kg.to_neo4j(password="yourpassword")
```

### Step 4 — Open Neo4j Browser

Go to http://localhost:7474 and paste any of these queries:

```cypher
// Everything connected to Snort
MATCH (n {name: 'Snort'})-[r]-(m) RETURN n, r, m

// All detection tools
MATCH (n:Entity {nist_csf: 'DETECT', type: 'tool'})
RETURN n.name, n.difficulty LIMIT 20

// Multi-hop: tool detects attack that exploits vulnerability
MATCH (t:Entity)-[:CAN_DETECT]->(a)-[:CAN_EXPLOIT]->(v)
RETURN t.name AS tool, a.name AS attack, v.name AS vulnerability LIMIT 15

// NIST CSF coverage
MATCH (n:Entity) RETURN n.nist_csf, count(n) AS count ORDER BY count DESC

// Search by keyword (full-text index)
CALL db.index.fulltext.queryNodes('entity_search', 'intrusion detection')
YIELD node, score RETURN node.name, node.type, score ORDER BY score DESC LIMIT 10

// All beginner-level entities
MATCH (n:Entity {difficulty: 'beginner'}) RETURN n.name, n.type LIMIT 25

// Entities mapped to MITRE ATT&CK Discovery tactic
MATCH (n:Entity {mitre_tactic: 'Discovery'}) RETURN n.name, n.type
```

### What Each Entity Gets in Neo4j

Every node has these properties after import:

| Property | Example | Source |
|----------|---------|--------|
| `name` | `Snort` | AISecKG |
| `type` | `tool` | AISecKG |
| `category` | `application` | AISecKG |
| `description` | `Cybersecurity tool: Snort` | AISecKG |
| `nist_csf` | `DETECT` | NIST CSF 2.0 (auto-mapped) |
| `mitre_tactic` | `Discovery` | MITRE ATT&CK (auto-mapped) |
| `blooms_level` | `3` | Bloom's Taxonomy |
| `difficulty` | `intermediate` | Bloom's Taxonomy |
| `prerequisites` | `networking, operating systems` | Domain logic |
| `framework_tags` | `NIST:DETECT BLOOM:3 UCO:tool` | Combined |

---

## Dataset

| File | Contents |
|------|----------|
| `all_entity_info.csv` | 963 entities: name, type, category, description |
| `all_triples.csv` | 729 triples: e1, relation, e2 |
| `all_relation_info.csv` | 9 relation types: uses, can_detect, can_exploit, has_a, is_a, can_harm, can_expose, can_analyze, part_of, implements |

---

## Citation

**MLA:**
Agrawal, Garima, et al. "AISecKG: Knowledge Graph Dataset for Cybersecurity Education." AAAI-MAKE 2023 (2023).

**BibTeX:**
```bibtex
@article{agrawal2023aiseckg,
  title={AISecKG: Knowledge Graph Dataset for Cybersecurity Education},
  author={Agrawal, Garima and Pal, Kuntal and Deng, Yuli and Liu, Huan and Baral, Chitta},
  journal={AAAI-MAKE 2023: Challenges Requiring the Combination of Machine Learning 2023},
  year={2023}
}
```
