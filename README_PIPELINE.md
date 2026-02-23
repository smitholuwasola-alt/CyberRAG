# CISSP Question Answering System

This system scrapes CISSP exam questions and answers them using the AISecKG cybersecurity knowledge graph.

## Overview

The system consists of four main components:

1. **Web Scraper** (`scraper/cissp_scraper.py`) - Scrapes CISSP questions from ExamTopics
2. **Knowledge Graph Builder** (`kg_builder.py`) - Builds a graph structure from the AISecKG dataset
3. **Query Engine** (`query_engine.py`) - Matches questions to knowledge graph and generates answers
4. **Main Pipeline** (`main_pipeline.py`) - Orchestrates the complete workflow

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the complete pipeline:

```bash
python main_pipeline.py --scrape --limit 10
```

### Step-by-Step

1. **Scrape Questions** (optional):
```bash
python scraper/cissp_scraper.py
```

2. **Build Knowledge Graph**:
```bash
python kg_builder.py
```

3. **Answer Questions**:
```python
from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine

# Build KG
kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

# Initialize query engine
engine = QueryEngine(kg)

# Answer a question
question = {
    'question': 'What is Snort used for?',
    'options': ['A. Network scanning', 'B. Intrusion Detection', 'C. Firewall', 'D. Encryption']
}
result = engine.answer_question(question)
print(result)
```

### Command Line Options

```bash
python main_pipeline.py [OPTIONS]

Options:
  --scrape          Scrape questions from website
  --no-scrape       Skip scraping (use existing questions)
  --max-pages N     Maximum pages to scrape (default: 50)
  --rebuild-kg      Force rebuild knowledge graph
  --limit N         Limit number of questions to answer
```

## Architecture

### Knowledge Graph Structure

- **Nodes**: Entities (tools, attacks, systems, features, etc.)
- **Edges**: Relations (uses, has_a, can_analyze, etc.)
- **Triples**: (Entity1, Relation, Entity2) format

### Query Process

1. **Entity Extraction**: Find relevant entities in the question
2. **Relation Matching**: Identify relation keywords
3. **Graph Traversal**: Query knowledge graph for relevant information
4. **Answer Generation**: Synthesize answer from graph data
5. **Option Matching**: Match answer to multiple choice options

## Output

The system generates:
- `cissp_questions.json` - Scraped questions
- `knowledge_graph.pkl` - Pickled knowledge graph
- `knowledge_graph.json` - JSON export of knowledge graph
- `answers.json` - Generated answers with confidence scores

## Example Output

```json
{
  "question": "What is Snort used for?",
  "answer": "Based on the knowledge graph, the question relates to: Snort.\n\nRelevant information:\n- Snort uses Intrusion Detection\n- Snort can_detect network attacks\n- Snort can_analyze traffic",
  "predicted_option": "B",
  "confidence": 0.8,
  "supporting_evidence": [
    "Snort uses Intrusion Detection",
    "Snort can_detect network attacks"
  ]
}
```

## Limitations

- The knowledge graph is domain-specific (cybersecurity tools and concepts)
- Questions outside the domain may have low confidence
- Web scraping depends on website structure
- Answer quality depends on knowledge graph coverage

## Future Improvements

- Add semantic similarity matching
- Implement neural question answering
- Expand knowledge graph with more sources
- Add confidence threshold filtering
- Support for multi-hop reasoning
