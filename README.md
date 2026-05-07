# AISecKG-CyBOK-Enhanced: CyberRAG

**A Graph-Augmented Retrieval System for CISSP Cybersecurity Education**

> Georgia Southern University | Oluwasola Smith | AIRC 2026

---

## Overview

CyberRAG is a prototype GraphRAG (Graph-Augmented Retrieval-Augmented Generation) system built on top of the AISecKG cybersecurity knowledge graph, enriched with the CyBOK v1.1.0 (Cyber Security Body of Knowledge). The system answers CISSP multiple-choice questions by combining structured knowledge graph retrieval with a local large language model (Ollama/llama3.2), grounding every answer in verifiable graph triples rather than unconstrained model generation.

The project addresses five research gaps identified by a PRISMA-ScR scoping review of 23 cybersecurity education studies (2017–2025): absence of formal learning-outcome evaluation, lack of adaptive difficulty, poor real-time threat coverage, non-standardized ontologies, and missing learner-centered explainability.

---

## Knowledge Graph Statistics (Current Production Graph)

> Source: `data/knowledge_graph/` — CyBOK-enriched, as of latest build

| Metric | Value |
|---|---|
| Entities | **1,513** |
| Relation types | **11** |
| Triples | **10,424** |
| CyBOK knowledge areas integrated | 21 (5 categories) |
| BERT NER accuracy (base AISecKG) | 83.30% |

> Note: The `archive/misc/IMPLEMENTATION_STATUS.md` reflects an earlier baseline (963 entities, 729 triples). The figures above are from the current enriched graph.

---

## Relation Types (11)

| Relation | Meaning |
|---|---|
| `has_a` | Entity possesses a component or attribute |
| `is_a` | Subtype or classification |
| `is_part_of` | Component membership (strict containment) |
| `part_of` | Component membership (loose containment) |
| `uses` | Entity employs a tool, method, or protocol |
| `implements` | Entity fulfills a standard or pattern |
| `can_analyze` | Analytical capability |
| `can_detect` | Detection capability |
| `can_expose` | Reveals a vulnerability or flaw |
| `can_exploit` | Attack capability |
| `can_harm` | Adverse impact relationship |

---

## Architecture

```
Question (text)
       |
       v
 EnhancedQueryEngine
  - Tokenize / lemmatize / stopword removal (NLTK)
  - Lexical entity scoring:
      +10  exact name match
      +5   substring match
      +2   per overlapping token
      +3   entity type match
  - Optional SBERT semantic ranking (all-MiniLM-L6-v2, weight x14.0)
       |
       v
 collect_graph_context()
  - Top-8 ranked entities
  - 2-hop NetworkX subgraph
  - Up to 45 triples per query
  - Inter-entity shortest paths
       |
       v
 Ollama LLM (llama3.2, local)
  - Strict dual-source system prompt:
      LOGIC (graph):       cite specific triples/paths
      EXPLANATION (book):  grounded passage from textbook
      CHOICE: A / B / C / D / NONE
      CERTAINTY: high | medium | low
       |
       v
 _merge_mc() consensus scoring
  - Graph and LLM agree          -> accept agreed choice
  - Graph margin >= 5.0          -> accept graph choice
  - Graph margin >= 2.0 AND confidence >= 0.35 -> accept graph
  - Confidence < 0.22 AND margin < 1.5  -> abstain (NONE)
  - All other cases              -> fallback to graph choice
       |
       v
 Final answer + retrieval_confidence + certainty_score + consensus
```

**Retrieval confidence formula:**
```
confidence = 0.34 × (top_score / 28)
           + 0.36 × (triples / 35)
           + 0.30 × (margin / 12)
```

---

## Project Structure

```
AISecKG-CyBOK-Enhanced/
|
+-- AISecKG-cybersecurity-dataset-main/
|   |
|   +-- src/                           # Active production code
|   |   +-- graphrag_ollama.py         # GraphRAG + Ollama pipeline (primary entry point)
|   |   +-- enhanced_query_engine.py   # Lexical + SBERT semantic entity ranking
|   |   +-- kg_builder.py              # NetworkX graph loader and query API
|   |   +-- graphrag_complete.py       # Standalone GraphRAG (no Ollama required)
|   |   +-- cissp250_graphrag.py       # 250-question CISSP evaluation runner
|   |   +-- neo4j_graph_retriever.py   # Neo4j Cypher-based retrieval (optional)
|   |   +-- ocr_cissp_pdf.py           # PDF OCR for CISSP exam text extraction
|   |
|   +-- data/                          # Current production data (active)
|   |   +-- knowledge_graph/           # CyBOK-enriched knowledge graph
|   |   |   +-- all_entity_info.csv    # 1,513 entities (entityID, name, type, category)
|   |   |   +-- all_relation_info.csv  # 11 relation types
|   |   |   +-- all_triples.csv        # 10,424 (subject, relation, object) triples
|   |   |   +-- kg_triples.json        # Base triples in JSON format
|   |   |   +-- knowledge_graph.json   # Graph nodes + edges in JSON
|   |   |   +-- knowledge_graph.pkl    # Serialized NetworkX graph (fast load)
|   |   |   +-- triple_doc1.csv        # Original source triples (pre-enrichment)
|   |   +-- qa/
|   |       +-- cissp250_run.jsonl     # 250-question CISSP run trace log
|   |       +-- cissp250_answers.md    # Human-readable answers and reasoning
|   |       +-- cissp_ocr.txt          # OCR-extracted CISSP exam text
|   |       +-- traces/                # Per-question KG visualization traces
|   |           +-- q001_trace.png ... q090_trace.png (and beyond)
|   |
|   +-- archive/
|       +-- data/
|       |   +-- dataset/               # Original AISecKG CSV files (baseline)
|       |   |   +-- all_entity_info.csv     # 963 entities (pre-CyBOK)
|       |   |   +-- all_relation_info.csv   # Original 9 relation types
|       |   |   +-- all_triples.csv         # 729 original triples
|       |   |   +-- triple_doc1.csv
|       |   +-- cybok/                 # CyBOK source files
|       |   |   +-- CyBOK_v1.1.0.pdf        # Full CyBOK document
|       |   |   +-- cybok_full_text.txt     # Extracted plain text
|       |   +-- datasource/            # Original lab documents
|       |       +-- lab-cs-cns-*.docx       # CNS lab source files
|       |       +-- lab-cs-sys-*.docx       # SYS lab source files
|       |       +-- csv/ textfiles/         # Converted CSV / TXT versions
|       |
|       +-- scripts/                   # Development and utility scripts
|       |   +-- main_pipeline.py       # 4-step orchestration pipeline
|       |   +-- query_engine.py        # Baseline lexical query engine
|       |   +-- cybok_extractor.py     # CyBOK PDF -> KG triple extractor
|       |   +-- build_cybok_kg.py      # Download CyBOK + build enriched KG
|       |   +-- answer_cissp_questions.py    # Run CISSP QA batch
|       |   +-- answer_eb_guide_questions.py # Run EB Ultimate Guide QA batch (86 Qs)
|       |   +-- extract_all_questions.py     # Question extraction utility
|       |   +-- extract_pdf_questions.py     # PDF-based question parser
|       |   +-- generate_questions_from_pdf.py # LLM-assisted question generation
|       |   +-- visualize_kg.py        # Static KG visualization
|       |   +-- create_interactive_viz.py    # Interactive HTML graph viewer
|       |   +-- run_visualizations.py        # Batch visualization runner
|       |   +-- show_visualization_summary.py
|       |   +-- strict_filter.py       # Answer confidence filter
|       |   +-- triple_filter.py       # Triple quality filter
|       |   +-- test_system.py         # Component integration tests
|       |   +-- test_new_kg.py         # Knowledge graph smoke tests
|       |   +-- parse_existing_questions.py
|       |   +-- neo4j/
|       |   |   +-- neo4j_integration.py    # Import KG into Neo4j
|       |   +-- scraper/
|       |       +-- cissp_scraper.py   # ExamTopics web scraper
|       |
|       +-- qa/                        # Archive question/answer files
|       |   +-- cissp_questions.json/.csv        # Scraped CISSP questions
|       |   +-- cissp_answers.json/.csv          # CISSP answer results
|       |   +-- eb_ultimate_guide_questions.*    # 86 EB benchmark questions
|       |   +-- eb_ultimate_guide_answers.*      # EB benchmark answers
|       |   +-- cissp250_smoke.*                 # 250-question smoke test
|       |   +-- cissp_run.jsonl                  # Full run trace log
|       |   +-- demo_graded.jsonl                # Demo graded output
|       |   +-- sample_answer_key.csv
|       |   +-- traces_smoke/                    # Trace PNGs (q001–q005)
|       |
|       +-- misc/
|           +-- IMPLEMENTATION_STATUS.md   # Baseline build status (older stats)
|           +-- docs/                      # Internal technical documentation
|           |   +-- HOW_QUERY_ENGINE_WORKS.md
|           |   +-- IMPLEMENTATION_SUMMARY.md
|           |   +-- KNOWLEDGE_GRAPH_FORMATION.md
|           |   +-- KNOWLEDGE_GRAPH_QUERYING.md
|           |   +-- ENTITY_RELEVANCE_SCORING.md
|           |   +-- ANSWER_SELECTION_PROCESS.md
|           |   +-- KG_BUILDER_EXPLANATION.md
|           |   +-- ENTITY_TO_GRAPH_MAPPING.md
|           |   +-- TRIPLES_TO_GRAPH_CONSTRUCTION.md
|           |   +-- RELATIONS_CSV_USAGE.md
|           |   +-- CSV_FILES_PURPOSE.md
|           |   +-- KG_BUILDING_VISUAL.md
|           |   +-- VISUALIZATION_GUIDE.md
|           |   +-- QUICK_START.md
|           |   +-- README_PIPELINE.md
|           +-- models/
|           |   +-- ner/               # BERT NER training files (83.30% F1)
|           |   |   +-- run_ner.py, tasks.py, utils_ner.py
|           |   |   +-- train/dev/test splits (.txt, .csv)
|           |   |   +-- labels.txt     # BIO entity labels
|           |   +-- kg/                # KG construction notebooks
|           |   |   +-- kg.ipynb, clean_triples.csv, triples_gen.csv
|           |   +-- dataprep/          # Data preprocessing notebooks
|           |       +-- data-preprocess.ipynb
|           |       +-- annotated_BIO.csv, annotated_data_BI.csv
|           +-- ontology/
|               +-- Ontology Description.docx  # Entity type ontology spec
|
+-- AIRC_2026_Smith.tex            # IEEE conference paper (Overleaf-ready LaTeX)
+-- AIRC_2026_Smith_Updated.md     # Updated paper in Markdown
+-- CyberRAG_Presentation_Script.md   # Full presentation walkthrough script
+-- CyberRAG_Presentation (2).pptx    # Slide deck
+-- RQ1_Plan.docx                  # Research question planning document
+-- README.md                      # This file
```

---

## Entity Schema

Each row in `all_entity_info.csv` has: `entityID`, `entityName`, `entityType`, `entityCategory`, `entityDescription`

**Entity types (12):** `tool`, `attack`, `feature`, `data`, `technique`, `system`, `app`, `function`, `vulnerability`, `protocol`, `standard`, `concept`

**Entity categories:** `concept`, `application`, `cybok_concept` (CyBOK-sourced entries)

### Neo4j Node Properties (optional backend)
When imported via `neo4j_integration.py`, each entity node additionally stores:

| Property | Values |
|---|---|
| `nist_csf_function` | IDENTIFY / PROTECT / DETECT / RESPOND / RECOVER / GOVERN |
| `mitre_attack_tactic` | MITRE ATT&CK tactic name |
| `blooms_level` | 1–6 (Bloom's Taxonomy) |
| `difficulty` | beginner / intermediate / advanced |
| `prerequisites` | Comma-separated prerequisite concepts |

---

## Installation

### Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com) running locally (for GraphRAG LLM synthesis)
- Neo4j (optional, for persistent graph backend)

### Install Python dependencies

```bash
pip install pandas networkx nltk numpy requests beautifulsoup4
# Optional — semantic ranking via SBERT:
pip install sentence-transformers
# Optional — Neo4j backend:
pip install neo4j
```

Download NLTK data on first run:
```python
import nltk
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')
```

### Pull Ollama model

```bash
ollama pull llama3.2
```

---

## Usage

### Answer a single question (Python API)

```python
from src.kg_builder import KnowledgeGraphBuilder
from src.graphrag_ollama import GraphRAGOllama

kg = KnowledgeGraphBuilder()   # loads data/knowledge_graph/ by default
kg.build_graph()

engine = GraphRAGOllama(kg)

result = engine.answer(
    question="Which protocol provides confidentiality for web traffic?",
    options=["A. FTP", "B. TLS", "C. SMTP", "D. ICMP"],
    certain=True
)

print(result["choice"])               # e.g. "B"
print(result["retrieval_confidence"]) # e.g. 0.72
print(result["certainty"])            # e.g. "high"
print(result["consensus"])            # e.g. "graph+llm"
```

### Run EB Ultimate Guide benchmark (86 questions)

```bash
python archive/scripts/answer_eb_guide_questions.py
```

### Run CISSP 250-question evaluation

```bash
python src/cissp250_graphrag.py
```

### Run CISSP batch (archive scraper pipeline)

```bash
python archive/scripts/answer_cissp_questions.py
```

### Build or rebuild the CyBOK-enriched knowledge graph

```bash
python archive/scripts/build_cybok_kg.py
```

This downloads `CyBOK_v1.1.0.pdf` if not present, extracts triples from all 21 knowledge areas, and merges them with the base AISecKG dataset to produce the enriched `data/knowledge_graph/` files.

### Run the 4-step baseline pipeline (scrape -> build -> query -> answer)

```bash
python archive/scripts/main_pipeline.py --scrape --limit 20
```

| Flag | Description |
|---|---|
| `--scrape` | Scrape fresh questions from ExamTopics |
| `--limit N` | Cap scraped questions at N |
| `--no-scrape` | Skip scraping, use existing question files |

### Import the knowledge graph into Neo4j (optional)

```bash
python archive/scripts/neo4j/neo4j_integration.py
```

Set `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` as environment variables before running.

### Visualize the knowledge graph

```bash
# Static matplotlib graph
python archive/scripts/visualize_kg.py

# Interactive HTML viewer
python archive/scripts/create_interactive_viz.py
```

### Run integration tests

```bash
python archive/scripts/test_system.py
python archive/scripts/test_new_kg.py
```

---

## GraphRAG Query Pipeline (6 Stages)

1. **Preprocess** — Tokenize, lemmatize, and remove stopwords (NLTK)
2. **Extract key terms** — Identify candidate entity tokens from the cleaned question
3. **Score entities** — Lexical scoring (+10 exact, +5 substring, +2/token, +3 type match) merged with optional SBERT semantic scores (weight ×14.0)
4. **Detect relation intent** — Match relation keywords to select relevant triple types
5. **Retrieve subgraph** — 2-hop expansion around top-8 entities, up to 45 triples, plus inter-entity shortest paths
6. **Generate and merge** — Ollama LLM synthesizes from graph context under strict dual-source prompt; `_merge_mc()` selects the final MCQ option

---

## Answer Consensus Rules (`_merge_mc`)

| Condition | Decision |
|---|---|
| Graph and LLM agree | Accept agreed choice |
| Graph margin >= 5.0 | Accept graph choice |
| Graph margin >= 2.0 AND confidence >= 0.35 | Accept graph choice |
| Confidence < 0.22 AND margin < 1.5 | Abstain (NONE) |
| All other cases | Fallback to graph choice |

---

## Evaluation

| Benchmark | Questions | Correct | Accuracy | Avg Confidence |
|---|---|---|---|---|
| EB Ultimate Guide | 86 | 60 | 70% | 0.40 |
| CISSP 250 | 250 | — | see `data/qa/cissp250_answers.md` | — |

---

## CyBOK Integration

`cybok_extractor.py` parses CyBOK v1.1.0 into 21 knowledge areas across 5 top-level categories, generating (subject, relation, object) triples in AISecKG format via pattern matching. `build_cybok_kg.py` merges these triples with the base dataset. The enrichment increased the graph from 729 triples to 10,424 triples and from 963 to 1,513 entities.

**CyBOK categories covered:**
- Human, Organisational and Regulatory Aspects
- Attacks and Defences
- Security Operations and Incident Management
- Software and Platform Security
- Infrastructure Security

---

## Research Context

This project is the prototype described in:

> Smith, O. (2026). *AI-Assisted Cybersecurity Education: A Scoping Review and GraphRAG Prototype*. AIRC 2026, Georgia Southern University.

The scoping review (PRISMA-ScR, 23 studies, 2017–2025) identified five open research gaps this prototype directly addresses:

| Gap | Implementation |
|---|---|
| No formal learning-outcome evaluation | Bloom's Taxonomy levels 1–6 stored per entity; difficulty tagging |
| No adaptive learning | Beginner / intermediate / advanced labels; prerequisite chains |
| No real-time threat coverage | CyBOK + MITRE ATT&CK tactic mapping per entity |
| Non-standardized ontologies | 12-type ontology + NIST CSF 2.0 function mapping |
| Learner-centered explainability lacking | Dual-source prompt: LOGIC (graph) + EXPLANATION (book) |

---

## Base Dataset Citations

> Agrawal, M., et al. (2023). *AISecKG: A Cybersecurity Knowledge Graph Dataset for Teaching and Research*. AAAI-MAKE 2023. https://doi.org/10.48550/arXiv.2305.01060

> Rashid, A., et al. (2019). *The Cyber Security Body of Knowledge (CyBOK)*. University of Bristol. https://www.cybok.org — Open Government Licence v3.0

---

## Dependencies

| Package | Purpose |
|---|---|
| `pandas` | CSV data loading and manipulation |
| `networkx` | Knowledge graph construction and traversal |
| `nltk` | Tokenization, lemmatization, stopword removal |
| `numpy` | Numerical scoring operations |
| `requests` | Ollama API calls and web requests |
| `beautifulsoup4` | HTML parsing for CISSP scraper |
| `sentence-transformers` | Optional SBERT semantic entity ranking |
| `neo4j` | Optional Neo4j graph database backend |
| `matplotlib` | Static KG visualization |

---

## License

The AISecKG dataset is subject to the license terms of the original AAAI-MAKE 2023 publication. CyBOK content is used under the Open Government Licence v3.0. All prototype code in this repository is for academic research purposes.