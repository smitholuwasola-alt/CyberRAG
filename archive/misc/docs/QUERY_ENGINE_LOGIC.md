# Query Engine Logic Explanation

## Overview

The `QueryEngine` class implements a multi-stage pipeline to answer cybersecurity questions by querying a knowledge graph. The engine uses semantic matching and graph traversal to find relevant information and generate answers.

## Architecture

The query engine follows a 7-stage pipeline:

1. **Text Preprocessing**
2. **Key Term Extraction**
3. **Entity Relevance Scoring**
4. **Relation Keyword Extraction**
5. **Knowledge Graph Querying**
6. **Answer Generation**
7. **Question Answering**

---

## Stage 1: Text Preprocessing (`preprocess_text`)

**Purpose**: Normalize the question text for matching

**Process**:
- Tokenizes the question into individual words
- Converts all text to lowercase for case-insensitive matching
- Removes stopwords (common words like "the", "is", "a", "an")
- Lemmatizes words to their root form (e.g., "analyzing" → "analyze", "detects" → "detect")
- Filters out non-alphanumeric tokens

**Example**:
```
Input:  "What tool can analyze network traffic?"
Output: ["tool", "analyze", "network", "traffic"]
```

**Why**: Creates a normalized representation that can be matched against knowledge graph entities regardless of grammatical variations.

---

## Stage 2: Key Term Extraction (`extract_key_terms`)

**Purpose**: Identify potential entity names mentioned in the question

**Process**:
1. Preprocesses the question text
2. Searches for entity names from the knowledge graph that appear in the question:
   - Checks if any entity name (case-insensitive) is a substring of the question
   - Only considers entities with names longer than 2 characters
3. Extracts capitalized words (likely proper nouns like "Snort", "Nmap", "TCP")
4. Returns a set of potential entity matches

**Example**:
```
Question: "What does Snort use for intrusion detection?"
Key Terms: {"Snort", "intrusion", "detection"}
```

**Why**: Identifies the specific entities the question is asking about, which are the entry points into the knowledge graph.

---

## Stage 3: Entity Relevance Scoring (`find_relevant_entities`)

**Purpose**: Rank entities by how relevant they are to the question

**Scoring Algorithm**:
For each entity in the knowledge graph, calculate a relevance score:

- **+10.0 points**: Exact entity name match in extracted key terms
- **+5.0 points**: Entity name appears as substring in question (case-insensitive)
- **+2.0 points per token**: Overlapping tokens between entity name and preprocessed question
- **+3.0 points**: Entity type or category mentioned in question (e.g., "tool", "attack", "protocol")

**Process**:
1. For each entity, calculate the score using the above rules
2. Sort entities by score (highest first)
3. Return top 10 most relevant entities

**Example**:
```
Question: "What tool detects network intrusions?"

Entity: "Snort"
- Exact match in key terms: +10.0
- Token overlap ("network"): +2.0
- Type match ("tool"): +3.0
Total Score: 15.0

Entity: "Nmap"
- Token overlap ("network"): +2.0
- Type match ("tool"): +3.0
Total Score: 5.0
```

**Why**: Prioritizes entities that are most likely to contain the answer, reducing search space and improving accuracy.

---

## Stage 4: Relation Keyword Extraction (`extract_relation_keywords`)

**Purpose**: Identify what type of relationship the question is asking about

**Process**:
Maps natural language patterns to knowledge graph relation types:

| Relation Type | Question Patterns |
|--------------|-------------------|
| `uses` | "uses", "utilizes", "employs", "applies" |
| `has_a` | "has", "contains", "includes", "consists" |
| `is_a` | "is", "are", "type of", "kind of" |
| `can_analyze` | "analyzes", "examines", "inspects", "monitors" |
| `can_detect` | "detects", "identifies", "finds", "discovers" |
| `can_exploit` | "exploits", "takes advantage" |
| `can_harm` | "harms", "damages", "affects", "impacts" |
| `is_part_of` | "part of", "component of", "belongs to" |
| `implements` | "implements", "executes", "performs" |

**Example**:
```
Question: "What tool can detect network intrusions?"
Extracted Relations: ["can_detect"]
```

**Why**: Helps focus the graph traversal on relevant relationship types, filtering out irrelevant connections.

---

## Stage 5: Knowledge Graph Querying (`query_knowledge_graph`)

**Purpose**: Retrieve relevant information from the knowledge graph

**Process**:
1. **Get Top Entities**: Takes the top 5 most relevant entities from Stage 3
2. **For Each Entity**:
   - Retrieves entity metadata (type, category, description)
   - Finds related entities (neighbors in the graph via outgoing/incoming edges)
   - Extracts all triples (subject-relation-object) involving this entity
3. **Path Finding**: If multiple entities found, finds paths between them (up to 3 hops)
   - Helps discover indirect relationships
   - Example: Entity A → relation → Entity B → relation → Entity C
4. **Returns Structured Data**:
   ```python
   {
       'entities': [entity_info_dicts],
       'relations': [relation_types],
       'paths': [path_lists],
       'subgraph_triples': [(subject, relation, object), ...]
   }
   ```

**Example**:
```
Question: "What does Snort use for intrusion detection?"

Top Entities: ["Snort", "Intrusion Detection"]
Retrieved:
- Snort entity info: {type: "Tool", category: "Security Tool"}
- Related: [("Intrusion Detection", "can_detect", "outgoing")]
- Triples: [("Snort", "can_detect", "Intrusion"), ("Snort", "uses", "Packet Analysis")]
- Path: Snort → can_detect → Intrusion
```

**Why**: Builds a focused subgraph containing only the knowledge relevant to answering the question, making answer generation more efficient and accurate.

---

## Stage 6: Answer Generation (`generate_answer`)

**Purpose**: Synthesize an answer from the retrieved knowledge graph information

**Process**:

### 6.1 Answer Text Construction
- Lists the top 3 relevant entities
- Includes relevant triples as supporting information
- Formats as natural language explanation

### 6.2 Confidence Calculation
- Formula: `min(number_of_matching_entities * 0.2, 1.0)`
- More entities found = higher confidence
- Capped at 1.0 (100% confidence)

**Example**:
```
Entities found: 3
Confidence: min(3 * 0.2, 1.0) = 0.6 (60%)
```

### 6.3 Option Matching (for multiple-choice questions)
If options are provided:
1. For each option (A, B, C, D):
   - Finds relevant entities in that option text
   - Sums the relevance scores of top 3 entities
2. Selects the option with the highest score
3. Returns the option letter (A, B, C, or D)

**Example**:
```
Question: "What tool detects intrusions?"
Options:
  A. Nmap (score: 5.0)
  B. Snort (score: 15.0) ← Highest
  C. Wireshark (score: 8.0)
  D. Metasploit (score: 3.0)

Predicted Option: B
```

### 6.4 Supporting Evidence Collection
- Collects all triples used in the answer
- These triples justify why the answer was selected

**Return Format**:
```python
{
    'answer_text': "Based on the knowledge graph...",
    'confidence': 0.6,
    'matched_option': 'B',
    'supporting_evidence': ["Snort can_detect Intrusion", ...],
    'kg_info': {...}
}
```

**Why**: Provides a structured, explainable answer with confidence metrics and evidence, making the system transparent and trustworthy.

---

## Stage 7: Question Answering (`answer_question`)

**Purpose**: Main entry point that orchestrates the entire pipeline

**Process**:
1. Extracts question text and options from input dictionary
2. Calls `generate_answer()` to get the result
3. Formats and returns a structured result

**Input Format**:
```python
{
    'question': "What tool can detect network intrusions?",
    'options': ["A. Nmap", "B. Snort", "C. Wireshark", "D. Metasploit"],
    'correct_answer': "B",
    'topic': "Network Security"
}
```

**Output Format**:
```python
{
    'question': "What tool can detect network intrusions?",
    'answer': "Based on the knowledge graph, the question relates to: Snort...",
    'predicted_option': 'B',
    'confidence': 0.6,
    'supporting_evidence': ["Snort can_detect Intrusion", ...],
    'options': ["A. Nmap", "B. Snort", ...]
}
```

---

## Complete Workflow Example

**Question**: "What tool can detect network intrusions?"

### Step-by-Step Execution:

1. **Preprocessing**:
   ```
   Input: "What tool can detect network intrusions?"
   Tokens: ["tool", "detect", "network", "intrusion"]
   ```

2. **Key Term Extraction**:
   ```
   Found entities: {"Snort", "Intrusion Detection", "Network"}
   Capitalized words: {}
   ```

3. **Entity Scoring**:
   ```
   Snort: 15.0 (exact match + token overlap + type match)
   Intrusion Detection: 12.0 (token overlap + type match)
   Network: 5.0 (token overlap)
   ```

4. **Relation Extraction**:
   ```
   "detect" → "can_detect" relation
   ```

5. **Knowledge Graph Query**:
   ```
   Top entities: ["Snort", "Intrusion Detection"]
   Retrieved triples:
     - ("Snort", "can_detect", "Intrusion")
     - ("Snort", "is_a", "Network Security Tool")
   ```

6. **Answer Generation**:
   ```
   Answer text: "Based on the knowledge graph, the question relates to: Snort, Intrusion Detection.
                 Relevant information:
                 - Snort can_detect Intrusion"
   
   Confidence: 0.4 (2 entities * 0.2)
   
   Option matching:
     A. Nmap: 5.0
     B. Snort: 15.0 ← Selected
     C. Wireshark: 8.0
     D. Metasploit: 3.0
   ```

7. **Final Result**:
   ```python
   {
       'question': "What tool can detect network intrusions?",
       'answer': "Based on the knowledge graph...",
       'predicted_option': 'B',
       'confidence': 0.4,
       'supporting_evidence': ["Snort can_detect Intrusion"]
   }
   ```

---

## Design Decisions & Trade-offs

### Why Semantic Matching Instead of Deep NLP?

1. **Speed**: Direct string matching and graph traversal is faster than running large language models
2. **Interpretability**: Easy to understand why an answer was selected (can trace back to specific triples)
3. **Resource Efficiency**: No need for GPU or large model weights
4. **Accuracy on Structured Data**: Knowledge graphs are structured, so structured queries work well

### Limitations

1. **Vocabulary Mismatch**: If question uses synonyms not in the KG, may miss relevant entities
2. **Simple Scoring**: The scoring function is heuristic-based, not learned
3. **No Context Understanding**: Doesn't understand question context beyond keyword matching
4. **Fixed Confidence Formula**: Confidence calculation is simple and may not reflect true uncertainty

### Strengths

1. **Explainable**: Every answer can be traced to specific knowledge graph triples
2. **Fast**: Efficient graph operations and string matching
3. **Domain-Specific**: Tailored for cybersecurity knowledge graph structure
4. **Scalable**: Performance doesn't degrade significantly with larger graphs

---

## Key Components Summary

| Component | Purpose | Key Method |
|-----------|---------|------------|
| Text Normalization | Prepare text for matching | `preprocess_text()` |
| Entity Discovery | Find relevant entities | `extract_key_terms()`, `find_relevant_entities()` |
| Relation Mapping | Identify relationship types | `extract_relation_keywords()` |
| Graph Querying | Retrieve relevant knowledge | `query_knowledge_graph()` |
| Answer Synthesis | Generate answer from KG data | `generate_answer()` |
| Pipeline Orchestration | Coordinate all stages | `answer_question()` |

---

## Future Improvements

Potential enhancements to the query engine:

1. **Synonym Expansion**: Use word embeddings or synonym dictionaries to handle vocabulary variations
2. **Learned Scoring**: Train a model to score entity relevance instead of using heuristics
3. **Question Type Classification**: Different strategies for "what", "how", "why" questions
4. **Multi-hop Reasoning**: Better path finding for complex questions requiring multiple inference steps
5. **Confidence Calibration**: More sophisticated confidence estimation based on answer quality metrics
