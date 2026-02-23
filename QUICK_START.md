# Quick Start Guide

## Overview

This system provides a complete pipeline to:
1. Scrape CISSP exam questions from ExamTopics
2. Build a knowledge graph from the AISecKG cybersecurity dataset
3. Answer questions using the knowledge graph

## Installation

```bash
pip install -r requirements.txt
```

## Quick Test

Run the test script to verify everything works:

```bash
python test_system.py
```

## Usage Examples

### 1. Run Complete Pipeline (Recommended)

```bash
# Scrape questions and answer them
python main_pipeline.py --scrape --limit 10

# Or use existing questions without scraping
python main_pipeline.py --limit 10
```

### 2. Build Knowledge Graph Only

```bash
python kg_builder.py
```

This creates:
- `knowledge_graph.pkl` - Pickled graph for fast loading
- `knowledge_graph.json` - JSON export for visualization

### 3. Answer Individual Questions

```python
from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine

# Build/load knowledge graph
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
print(f"Answer: {result['answer']}")
print(f"Predicted Option: {result['predicted_option']}")
print(f"Confidence: {result['confidence']}")
```

### 4. Scrape Questions Only

```bash
python scraper/cissp_scraper.py
```

This creates `cissp_questions.json` with scraped questions.

## File Structure

```
AISecKG-cybersecurity-dataset-main/
├── dataset/                    # Original dataset files
│   ├── all_entity_info.csv
│   ├── all_relation_info.csv
│   └── all_triples.csv
├── scraper/
│   └── cissp_scraper.py       # Web scraper
├── kg_builder.py              # Knowledge graph builder
├── query_engine.py             # Question answering engine
├── main_pipeline.py            # Complete pipeline
├── test_system.py              # Test script
└── requirements.txt            # Dependencies
```

## Output Files

- `cissp_questions.json` - Scraped questions
- `knowledge_graph.pkl` - Pickled knowledge graph
- `knowledge_graph.json` - JSON export
- `answers.json` - Generated answers

## How It Works

1. **Knowledge Graph**: Built from entities, relations, and triples in the dataset
2. **Entity Matching**: Questions are analyzed to find relevant entities
3. **Graph Query**: Relevant triples and relations are retrieved
4. **Answer Generation**: Answers are synthesized from graph information
5. **Option Matching**: Best matching multiple-choice option is identified

## Troubleshooting

### Dataset not found
Ensure you're in the `AISecKG-cybersecurity-dataset-main` directory and the `dataset/` folder exists.

### Scraping fails
The website structure may have changed. The system will use sample questions if scraping fails.

### Low confidence answers
The knowledge graph is domain-specific. Questions outside cybersecurity may have low confidence.

## Next Steps

- Review `README_PIPELINE.md` for detailed documentation
- Check `answers.json` for generated answers
- Modify `query_engine.py` to improve answer quality
- Expand the knowledge graph with additional sources
