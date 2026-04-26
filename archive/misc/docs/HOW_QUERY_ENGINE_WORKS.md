# How the Query Engine Works

## Overview

The Query Engine is a multi-stage pipeline that processes natural language questions, matches them to knowledge graph entities, retrieves relevant information, and generates answers. It uses semantic matching and graph traversal rather than deep learning, making it fast and interpretable.

---

## Architecture: The 7-Stage Pipeline

```
Question Input
     ↓
[1] Text Preprocessing
     ↓
[2] Key Term Extraction
     ↓
[3] Entity Relevance Scoring
     ↓
[4] Relation Keyword Extraction
     ↓
[5] Knowledge Graph Querying
     ↓
[6] Answer Generation
     ↓
[7] Option Matching (if applicable)
     ↓
Final Answer Output
```

---

## Stage 1: Text Preprocessing

### Method: `preprocess_text(text)`

**Purpose**: Normalize the question text for matching

**Process**:
```python
def preprocess_text(self, text: str) -> List[str]:
    # 1. Tokenize: Split into words
    tokens = word_tokenize(text.lower())
    
    # 2. Filter and lemmatize
    tokens = [
        self.lemmatizer.lemmatize(token) 
        for token in tokens 
        if token.isalnum() and token not in self.stop_words
    ]
    return tokens
```

**What Happens**:
1. **Tokenization**: "What tool detects intrusions?" → ["What", "tool", "detects", "intrusions", "?"]
2. **Lowercase**: ["what", "tool", "detects", "intrusions", "?"]
3. **Remove Stopwords**: ["tool", "detects", "intrusions"] (removes "what", "?")
4. **Lemmatization**: ["tool", "detect", "intrusion"] (reduces to root forms)

**Example**:
```
Input:  "What tools can analyze network traffic?"
Output: ["tool", "analyze", "network", "traffic"]
```

**Why**: Creates a normalized representation that can be matched against knowledge graph entities regardless of grammatical variations.

---

## Stage 2: Key Term Extraction

### Method: `extract_key_terms(question)`

**Purpose**: Identify potential entity names mentioned in the question

**Process**:
```python
def extract_key_terms(self, question: str) -> Set[str]:
    key_terms = set()
    question_lower = question.lower()
    
    # 1. Search for entity names in question
    for entity_name in self.kg.entities.keys():
        entity_lower = entity_name.lower()
        if len(entity_lower) > 2 and entity_lower in question_lower:
            key_terms.add(entity_name)
    
    # 2. Extract capitalized words (proper nouns)
    words = word_tokenize(question)
    for word in words:
        if word[0].isupper() and len(word) > 2:
            key_terms.add(word)
    
    return key_terms
```

**What Happens**:
1. **Entity Name Search**: Checks if any entity name from the knowledge graph appears in the question
2. **Capitalized Word Extraction**: Finds proper nouns (likely entity names)

**Example**:
```
Question: "What does Snort use for intrusion detection?"
Key Terms: {"Snort", "intrusion", "detection", "Intrusion Detection"}
```

**Why**: Identifies the specific entities the question is asking about, which are entry points into the knowledge graph.

---

## Stage 3: Entity Relevance Scoring

### Method: `find_relevant_entities(question)`

**Purpose**: Rank all entities by how relevant they are to the question

**Scoring Algorithm**:

For each entity in the knowledge graph, calculate a score:

| Scoring Rule | Points | Example |
|--------------|--------|---------|
| **Exact match in key terms** | +10.0 | "Snort" in key_terms → +10.0 |
| **Substring match in question** | +5.0 | "snort" appears in question → +5.0 |
| **Token overlap** | +2.0 per token | "network" in both → +2.0 |
| **Type/category match** | +3.0 | Question mentions "tool", entity type="tool" → +3.0 |

**Code Logic**:
```python
def find_relevant_entities(self, question: str):
    entity_scores = []
    
    for entity_name, entity_data in self.kg.entities.items():
        score = 0.0
        
        # Exact match
        if entity_name in key_terms:
            score += 10.0
        
        # Substring match
        if entity_lower in question_lower:
            score += 5.0
        
        # Token overlap
        entity_tokens = set(self.preprocess_text(entity_name))
        overlap = len(question_tokens & entity_tokens)
        score += overlap * 2.0
        
        # Type-based matching
        entity_type = entity_data.get('type', '').lower()
        if entity_type in question_lower:
            score += 3.0
        
        if score > 0:
            entity_scores.append((entity_name, score))
    
    # Sort and return top 10
    entity_scores.sort(key=lambda x: x[1], reverse=True)
    return entity_scores[:10]
```

**Example**:
```
Question: "What tool detects network intrusions?"

Entity: "Snort"
- Exact match: +10.0
- Token overlap ("network"): +2.0
- Type match ("tool"): +3.0
Total: 15.0

Entity: "Intrusion Detection"
- Substring match: +5.0
- Token overlap ("intrusion", "detection"): +4.0
Total: 9.0

Entity: "Nmap"
- Token overlap ("network"): +2.0
- Type match ("tool"): +3.0
Total: 5.0
```

**Result**: Returns top 10 entities sorted by score: `[("Snort", 15.0), ("Intrusion Detection", 9.0), ("Nmap", 5.0), ...]`

**Why**: Prioritizes entities that are most likely to contain the answer, reducing search space and improving accuracy.

---

## Stage 4: Relation Keyword Extraction

### Method: `extract_relation_keywords(question)`

**Purpose**: Identify what type of relationship the question is asking about

**Process**:
```python
def extract_relation_keywords(self, question: str) -> List[str]:
    question_lower = question.lower()
    relation_keywords = []
    
    relation_patterns = {
        'uses': ['uses', 'utilizes', 'employs', 'applies'],
        'can_detect': ['detects', 'identifies', 'finds', 'discovers'],
        'can_analyze': ['analyzes', 'examines', 'inspects', 'monitors'],
        'can_exploit': ['exploits', 'takes advantage'],
        'can_harm': ['harms', 'damages', 'affects', 'impacts'],
        'is_a': ['is', 'are', 'type of', 'kind of'],
        'has_a': ['has', 'contains', 'includes', 'consists'],
        'is_part_of': ['part of', 'component of', 'belongs to'],
        'implements': ['implements', 'executes', 'performs']
    }
    
    for relation, patterns in relation_patterns.items():
        for pattern in patterns:
            if pattern in question_lower:
                relation_keywords.append(relation)
                break
    
    return relation_keywords
```

**Example**:
```
Question: "What tool can detect network intrusions?"
Extracted Relations: ["can_detect"]
```

**Why**: Helps focus the graph traversal on relevant relationship types, filtering out irrelevant connections.

---

## Stage 5: Knowledge Graph Querying

### Method: `query_knowledge_graph(question)`

**Purpose**: Retrieve relevant information from the knowledge graph

**Process**:

#### Step 5.1: Get Top Entities
```python
relevant_entities = self.find_relevant_entities(question)
top_entities = [e[0] for e in relevant_entities[:5]]  # Top 5
```

#### Step 5.2: For Each Top Entity
```python
for entity in top_entities:
    # Get entity metadata
    entity_info = self.kg.get_entity_info(entity)
    # Returns: {'id', 'name', 'type', 'category', 'description'}
    
    # Find related entities
    related = self.kg.find_related_entities(entity)
    # Returns: [('network attacks', 'can_detect', 'outgoing'), ...]
    
    # Store in kg_info
    kg_info['entities'].append({
        'name': entity,
        'info': entity_info,
        'related': related[:5]
    })
```

#### Step 5.3: Extract Relevant Triples
```python
for e1, r, e2 in self.kg.triples:
    if entity.lower() in e1.lower() or entity.lower() in e2.lower():
        kg_info['subgraph_triples'].append((e1, r, e2))
```

#### Step 5.4: Find Paths Between Entities
```python
if len(top_entities) >= 2:
    for i in range(len(top_entities) - 1):
        paths = self.kg.get_path_between_entities(
            top_entities[i], 
            top_entities[i+1], 
            max_length=3
        )
        kg_info['paths'].extend(paths[:3])
```

**Returns**:
```python
{
    'entities': [
        {
            'name': 'Snort',
            'info': {'type': 'feature', 'category': 'security tool', ...},
            'related': [('network attacks', 'can_detect', 'outgoing'), ...]
        }
    ],
    'relations': ['can_detect'],
    'paths': [...],
    'subgraph_triples': [
        ('Snort', 'can_detect', 'network attacks'),
        ('Snort', 'uses', 'Intrusion Detection'),
        ...
    ]
}
```

**Why**: Builds a focused subgraph containing only the knowledge relevant to answering the question.

---

## Stage 6: Answer Generation

### Method: `generate_answer(question, options)`

**Purpose**: Synthesize an answer from the retrieved knowledge graph information

### Step 6.1: Build Answer Text

```python
if kg_info['entities']:
    entity_names = [e['name'] for e in kg_info['entities']]
    answer_text = f"Based on the knowledge graph, the question relates to: {', '.join(entity_names[:3])}.\n\n"
    
    # Add relevant triples
    if kg_info['subgraph_triples']:
        answer_text += "Relevant information:\n"
        for e1, r, e2 in kg_info['subgraph_triples'][:5]:
            answer_text += f"- {e1} {r} {e2}\n"
            supporting_evidence.append(f"{e1} {r} {e2}")
```

**Example Output**:
```
Based on the knowledge graph, the question relates to: Snort, Intrusion Detection.

Relevant information:
- Snort can_detect network attacks
- Snort uses Intrusion Detection
- Snort can_analyze traffic
```

### Step 6.2: Calculate Confidence

```python
confidence = min(len(kg_info['entities']) * 0.2, 1.0)
```

**Formula**: `min(number_of_matching_entities * 0.2, 1.0)`

**Examples**:
- 1 entity found → confidence = 0.2 (20%)
- 2 entities found → confidence = 0.4 (40%)
- 3 entities found → confidence = 0.6 (60%)
- 5+ entities found → confidence = 1.0 (100%)

**Why**: More entities found = higher confidence that the answer is correct.

### Step 6.3: Match Options (for Multiple-Choice Questions)

```python
if options:
    option_scores = []
    for i, option in enumerate(options):
        # Find entities in each option
        option_entities = self.find_relevant_entities(option)
        # Sum scores of top 3 entities
        score = sum([e[1] for e in option_entities[:3]])
        option_scores.append((chr(65 + i), option, score))  # A, B, C, D
    
    # Select option with highest score
    option_scores.sort(key=lambda x: x[2], reverse=True)
    matched_option = option_scores[0][0]  # Best option letter
```

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

**Why**: Matches each option to knowledge graph entities and selects the one with highest entity relevance.

---

## Stage 7: Question Answering (Orchestration)

### Method: `answer_question(question_data)`

**Purpose**: Main entry point that orchestrates the entire pipeline

**Process**:
```python
def answer_question(self, question_data: Dict) -> Dict:
    # Extract question and options
    question = question_data.get('question', '')
    options = question_data.get('options', [])
    
    # Generate answer (calls all previous stages)
    result = self.generate_answer(question, options)
    
    # Format and return
    return {
        'question': question,
        'answer': result['answer_text'],
        'predicted_option': result['matched_option'],
        'confidence': result['confidence'],
        'supporting_evidence': result['supporting_evidence'],
        'options': options
    }
```

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
    'confidence': 0.4,
    'supporting_evidence': ["Snort can_detect network attacks", ...],
    'options': ["A. Nmap", "B. Snort", ...]
}
```

---

## Complete Workflow Example

### Question: "What tool can detect network intrusions?"

#### Stage 1: Preprocessing
```
Input: "What tool can detect network intrusions?"
Output: ["tool", "detect", "network", "intrusion"]
```

#### Stage 2: Key Term Extraction
```
Found: {"Snort", "network", "intrusion", "Intrusion Detection"}
```

#### Stage 3: Entity Scoring
```
Snort: 15.0 points
  - Exact match: +10.0
  - Token overlap: +2.0
  - Type match: +3.0

Intrusion Detection: 9.0 points
  - Substring match: +5.0
  - Token overlap: +4.0

network attacks: 7.0 points
  - Token overlap: +4.0
  - Type match: +3.0

Top Entities: [("Snort", 15.0), ("Intrusion Detection", 9.0), ...]
```

#### Stage 4: Relation Extraction
```
Question contains "detect" → relation: "can_detect"
```

#### Stage 5: Knowledge Graph Querying
```
Top Entity: "Snort"

Entity Info:
  - type: "feature"
  - category: "security tool"

Related Entities:
  - ("network attacks", "can_detect", "outgoing")
  - ("Intrusion Detection", "uses", "outgoing")
  - ("traffic", "can_analyze", "outgoing")

Relevant Triples:
  - ("Snort", "can_detect", "network attacks")
  - ("Snort", "uses", "Intrusion Detection")
  - ("Snort", "can_analyze", "traffic")
```

#### Stage 6: Answer Generation
```
Answer Text:
"Based on the knowledge graph, the question relates to: Snort, Intrusion Detection.

Relevant information:
- Snort can_detect network attacks
- Snort uses Intrusion Detection"

Confidence: 0.4 (2 entities found)

Option Matching:
  A. Nmap: 5.0
  B. Snort: 15.0 ← Selected
  C. Wireshark: 8.0
  D. Metasploit: 3.0

Predicted Option: B
```

#### Stage 7: Final Output
```python
{
    'question': "What tool can detect network intrusions?",
    'answer': "Based on the knowledge graph...",
    'predicted_option': 'B',
    'confidence': 0.4,
    'supporting_evidence': ["Snort can_detect network attacks"]
}
```

---

## Key Components

### 1. Domain Keywords

The query engine maintains a mapping of security domain keywords:

```python
self.domain_keywords = {
    'access_control': ['access', 'control', 'authorization', ...],
    'network': ['network', 'packet', 'traffic', ...],
    'attack': ['attack', 'exploit', 'vulnerability', ...],
    'tool': ['tool', 'scanner', 'nmap', 'snort', ...],
    'encryption': ['encryption', 'decryption', 'cipher', ...],
    'policy': ['policy', 'procedure', 'compliance', ...]
}
```

**Use**: Helps identify domain context, though not directly used in current implementation.

### 2. NLTK Tools

- **Word Tokenizer**: Splits text into words
- **Stopwords**: Removes common words ("the", "is", "a")
- **WordNet Lemmatizer**: Reduces words to root forms

**Example**:
```
"analyzing" → "analyze"
"detects" → "detect"
"intrusions" → "intrusion"
```

### 3. Scoring System

The scoring system uses **heuristic-based matching**:

- **Exact matches** get highest scores (10.0)
- **Substring matches** get medium scores (5.0)
- **Token overlap** gets incremental scores (2.0 per token)
- **Type matching** gets bonus scores (3.0)

**Why Heuristics?**
- Fast (no model training needed)
- Interpretable (can explain why entity scored high)
- Works well with structured knowledge graphs

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Question Input                            │
│  "What tool can detect network intrusions?"                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [1] Preprocessing                                           │
│  → Tokenize, lowercase, remove stopwords, lemmatize         │
│  Output: ["tool", "detect", "network", "intrusion"]          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [2] Key Term Extraction                                     │
│  → Find entity names in question                             │
│  Output: {"Snort", "network", "intrusion"}                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [3] Entity Relevance Scoring                               │
│  → Score all entities, rank by relevance                    │
│  Output: [("Snort", 15.0), ("Intrusion Detection", 9.0)]    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [4] Relation Keyword Extraction                            │
│  → Map question verbs to relation types                      │
│  Output: ["can_detect"]                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [5] Knowledge Graph Querying                               │
│  → Get entity info, related entities, triples, paths        │
│  Output: {entities: [...], triples: [...], paths: [...]}    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [6] Answer Generation                                        │
│  → Build answer text, calculate confidence, match options   │
│  Output: {answer_text, confidence, matched_option, evidence} │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  [7] Final Output                                            │
│  → Format and return complete answer                         │
│  Output: {question, answer, predicted_option, confidence}    │
└─────────────────────────────────────────────────────────────┘
```

---

## How It Connects to Knowledge Graph

### Graph Traversal Methods Used

1. **`get_entity_info(entity)`**: Retrieves entity metadata
2. **`find_related_entities(entity)`**: Finds connected entities
3. **`get_path_between_entities(e1, e2)`**: Finds paths
4. **Direct triple access**: Iterates through `self.kg.triples`

### Example: How Query Engine Uses Graph

```python
# Query engine finds "Snort" is relevant
top_entity = "Snort"

# Gets entity metadata
info = kg.get_entity_info("Snort")
# Returns: {'type': 'feature', 'category': 'security tool'}

# Finds related entities
related = kg.find_related_entities("Snort")
# Returns: [('network attacks', 'can_detect', 'outgoing'), ...]

# Extracts triples
for e1, r, e2 in kg.triples:
    if "snort" in e1.lower() or "snort" in e2.lower():
        # Found: ("Snort", "can_detect", "network attacks")
        # Use this triple in answer
```

---

## Strengths and Limitations

### Strengths

✅ **Fast**: Direct string matching and graph traversal  
✅ **Interpretable**: Can trace back to specific triples  
✅ **No Training Required**: Works immediately with knowledge graph  
✅ **Explainable**: Every answer has supporting evidence  
✅ **Domain-Specific**: Tailored for cybersecurity knowledge  

### Limitations

❌ **Vocabulary Mismatch**: Misses synonyms not in KG  
❌ **Simple Scoring**: Heuristic-based, not learned  
❌ **No Context Understanding**: Only keyword matching  
❌ **Fixed Confidence Formula**: May not reflect true uncertainty  
❌ **Limited Reasoning**: Can't handle complex multi-step reasoning  

---

## Summary

The Query Engine works by:

1. **Preprocessing** the question to normalize text
2. **Extracting** key terms and entities mentioned
3. **Scoring** all entities by relevance to question
4. **Identifying** relationship types asked about
5. **Querying** the knowledge graph for relevant information
6. **Generating** an answer from retrieved knowledge
7. **Matching** to multiple-choice options (if provided)

The entire process is **semantic matching** based - it matches question text to knowledge graph entities and relationships, then uses graph traversal to find relevant information and synthesize answers.
