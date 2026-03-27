# Entity Relevance Scoring: How It Works

## Overview

Entity relevance scoring is the process of ranking all entities in the knowledge graph by how relevant they are to a given question. This happens in Stage 3 of the query engine pipeline.

---

## The Scoring Method

### Method: `find_relevant_entities(question)`

**Purpose**: Score and rank all entities by relevance to the question

**Returns**: List of `(entity_name, score)` tuples, sorted by score (highest first), top 10

---

## Step-by-Step Scoring Process

### Step 1: Prepare Inputs

```python
def find_relevant_entities(self, question: str):
    # Get key terms extracted from question
    key_terms = self.extract_key_terms(question)
    # Example: {"Snort", "network", "intrusion"}
    
    # Preprocess question to get tokens
    question_tokens = set(self.preprocess_text(question))
    # Example: {"tool", "detect", "network", "intrusion"}
    
    entity_scores = []
```

**What We Have**:
- `key_terms`: Set of entity names found in question
- `question_tokens`: Set of preprocessed tokens from question
- `question_lower`: Lowercase version of question

---

### Step 2: Iterate Through All Entities

```python
for entity_name, entity_data in self.kg.entities.items():
    if isinstance(entity_name, str):
        score = 0.0  # Start with zero score
        entity_lower = entity_name.lower()
        question_lower = question.lower()
```

**What Happens**: For each entity in the knowledge graph, initialize score to 0.0

---

### Step 3: Scoring Rule 1 - Exact Match (+10.0 points)

```python
# Exact match
if entity_name in key_terms:
    score += 10.0
```

**What It Checks**: Is the entity name in the set of key terms extracted from the question?

**Example**:
```
Question: "What does Snort use for intrusion detection?"
Key Terms: {"Snort", "intrusion", "detection", "Intrusion Detection"}

Entity: "Snort"
Check: "Snort" in {"Snort", "intrusion", ...} → TRUE
Score: +10.0

Entity: "Nmap"
Check: "Nmap" in {"Snort", "intrusion", ...} → FALSE
Score: +0.0
```

**Why**: Exact matches are the strongest signal - the entity is explicitly mentioned.

---

### Step 4: Scoring Rule 2 - Substring Match (+5.0 points)

```python
# Partial match in question
if entity_lower in question_lower:
    score += 5.0
```

**What It Checks**: Does the entity name appear as a substring anywhere in the question?

**Example**:
```
Question: "What does Snort use for intrusion detection?"
Question Lower: "what does snort use for intrusion detection?"

Entity: "Snort"
Check: "snort" in "what does snort use..." → TRUE
Score: +5.0

Entity: "Intrusion Detection"
Check: "intrusion detection" in "what does snort use for intrusion detection?" → TRUE
Score: +5.0

Entity: "network attacks"
Check: "network attacks" in "what does snort use..." → FALSE
Score: +0.0
```

**Why**: Even if not in key_terms, substring match indicates relevance.

**Note**: This can overlap with Rule 1 (exact match also matches substring), so an entity can get both +10.0 and +5.0 = 15.0 points.

---

### Step 5: Scoring Rule 3 - Token Overlap (+2.0 per token)

```python
# Token overlap
entity_tokens = set(self.preprocess_text(entity_name))
overlap = len(question_tokens & entity_tokens)
if overlap > 0:
    score += overlap * 2.0
```

**What It Checks**: How many words overlap between the entity name and the question?

**Process**:
1. Preprocess entity name to get tokens
2. Find intersection of question tokens and entity tokens
3. Count overlapping tokens
4. Add 2.0 points per overlapping token

**Example**:
```
Question: "What tool can detect network intrusions?"
Question Tokens: {"tool", "detect", "network", "intrusion"}

Entity: "network attacks"
Entity Tokens: {"network", "attack"}
Overlap: {"network"} → 1 token
Score: +2.0

Entity: "Intrusion Detection"
Entity Tokens: {"intrusion", "detection"}
Overlap: {"intrusion"} → 1 token
Score: +2.0

Entity: "network intrusion detection"
Entity Tokens: {"network", "intrusion", "detection"}
Overlap: {"network", "intrusion"} → 2 tokens
Score: +4.0 (2 tokens × 2.0)
```

**Why**: Shared words indicate semantic similarity, even if not exact matches.

---

### Step 6: Scoring Rule 4 - Type/Category Match (+3.0 points)

```python
# Type-based matching
if isinstance(entity_data, dict):
    entity_type = entity_data.get('type', '').lower()
    entity_category = entity_data.get('category', '').lower()
    
    # Check if question mentions entity type
    if entity_type in question_lower or entity_category in question_lower:
        score += 3.0
```

**What It Checks**: Does the question mention the entity's type or category?

**Process**:
1. Get entity type and category from entity metadata
2. Check if type or category appears in question (case-insensitive)
3. If yes, add 3.0 points

**Example**:
```
Question: "What tool can detect network intrusions?"
Question Lower: "what tool can detect network intrusions?"

Entity: "Snort"
Entity Type: "feature"
Entity Category: "security tool"
Check: "tool" in question → TRUE (category contains "tool")
Score: +3.0

Entity: "Nmap"
Entity Type: "tool"
Entity Category: "security tool"
Check: "tool" in question → TRUE
Score: +3.0

Entity: "network attacks"
Entity Type: "attack"
Entity Category: "concept"
Check: "attack" in question? → FALSE
Check: "concept" in question? → FALSE
Score: +0.0
```

**Why**: If question asks for a "tool" and entity is a tool, it's likely relevant.

---

### Step 7: Store Score (if > 0)

```python
if score > 0:
    entity_scores.append((entity_name, score))
```

**What Happens**: Only entities with score > 0 are stored (filters out irrelevant entities)

---

### Step 8: Sort and Return Top 10

```python
# Sort by score
entity_scores.sort(key=lambda x: x[1], reverse=True)
return entity_scores[:10]  # Top 10 entities
```

**What Happens**:
1. Sort all scored entities by score (highest first)
2. Return top 10 most relevant entities

---

## Complete Example: Scoring Calculation

### Question: "What tool can detect network intrusions?"

### Step-by-Step for Entity "Snort"

#### Initialization
```python
entity_name = "Snort"
entity_data = {'type': 'feature', 'category': 'security tool', ...}
score = 0.0
entity_lower = "snort"
question_lower = "what tool can detect network intrusions?"
key_terms = {"Snort", "network", "intrusion"}
question_tokens = {"tool", "detect", "network", "intrusion"}
```

#### Rule 1: Exact Match
```python
Check: "Snort" in {"Snort", "network", "intrusion"} → TRUE
Score: 0.0 + 10.0 = 10.0
```

#### Rule 2: Substring Match
```python
Check: "snort" in "what tool can detect network intrusions?" → TRUE
Score: 10.0 + 5.0 = 15.0
```

#### Rule 3: Token Overlap
```python
entity_tokens = set(self.preprocess_text("Snort"))
# Preprocessing "Snort" → {"snort"}
overlap = len({"tool", "detect", "network", "intrusion"} & {"snort"})
overlap = 0
Score: 15.0 + 0.0 = 15.0
```

#### Rule 4: Type/Category Match
```python
entity_type = "feature"
entity_category = "security tool"
Check: "tool" in "what tool can detect network intrusions?" → TRUE
Score: 15.0 + 3.0 = 18.0
```

#### Final Score
```
Entity: "Snort"
Final Score: 18.0
```

---

### Example: Scoring Multiple Entities

#### Question: "What tool can detect network intrusions?"

#### Entity 1: "Snort"
```
Rule 1 (Exact): +10.0 (if "Snort" in key_terms)
Rule 2 (Substring): +5.0 ("snort" in question)
Rule 3 (Token Overlap): +0.0 (no shared tokens)
Rule 4 (Type Match): +3.0 ("tool" in question, category="security tool")
Total: 18.0
```

#### Entity 2: "Intrusion Detection"
```
Rule 1 (Exact): +0.0 (not in key_terms as exact match)
Rule 2 (Substring): +5.0 ("intrusion detection" in question)
Rule 3 (Token Overlap): +4.0 (2 tokens: "intrusion", "detection")
Rule 4 (Type Match): +0.0 (type not mentioned in question)
Total: 9.0
```

#### Entity 3: "network attacks"
```
Rule 1 (Exact): +0.0
Rule 2 (Substring): +0.0 ("network attacks" not in question)
Rule 3 (Token Overlap): +2.0 (1 token: "network")
Rule 4 (Type Match): +0.0
Total: 2.0
```

#### Entity 4: "Nmap"
```
Rule 1 (Exact): +0.0
Rule 2 (Substring): +0.0 ("nmap" not in question)
Rule 3 (Token Overlap): +0.0
Rule 4 (Type Match): +3.0 ("tool" in question, type="tool")
Total: 3.0
```

#### Final Ranking
```python
[
    ("Snort", 18.0),
    ("Intrusion Detection", 9.0),
    ("Nmap", 3.0),
    ("network attacks", 2.0),
    ...
]
```

---

## Scoring Rules Summary

| Rule | Points | Condition | Example |
|------|--------|-----------|---------|
| **Exact Match** | +10.0 | Entity name in key_terms | "Snort" mentioned → +10.0 |
| **Substring Match** | +5.0 | Entity name appears in question | "snort" in question → +5.0 |
| **Token Overlap** | +2.0 per token | Shared words between entity and question | "network" shared → +2.0 |
| **Type Match** | +3.0 | Entity type/category mentioned in question | Question has "tool", entity is tool → +3.0 |

**Maximum Possible Score**: 10.0 + 5.0 + (many tokens × 2.0) + 3.0 = Can be quite high

---

## Important Details

### 1. Case-Insensitive Matching

All string comparisons are case-insensitive:
```python
entity_lower = entity_name.lower()
question_lower = question.lower()
if entity_lower in question_lower:
    score += 5.0
```

**Why**: "Snort" and "snort" should match.

### 2. Overlapping Rules

An entity can get points from multiple rules:
```python
# Entity "Snort" in question "What does Snort use?"
# Rule 1: +10.0 (exact match in key_terms)
# Rule 2: +5.0 (substring match)
# Total: 15.0
```

### 3. Token Preprocessing

Entity names are preprocessed the same way as questions:
```python
entity_tokens = set(self.preprocess_text(entity_name))
# "Intrusion Detection" → {"intrusion", "detection"}
```

This ensures fair comparison.

### 4. Minimum Score Threshold

Only entities with score > 0 are included:
```python
if score > 0:
    entity_scores.append((entity_name, score))
```

**Why**: Filters out completely irrelevant entities.

### 5. Top 10 Limit

Only top 10 entities are returned:
```python
return entity_scores[:10]
```

**Why**: Reduces computation in later stages, focuses on most relevant entities.

---

## Edge Cases

### Case 1: Entity Name Not in Question

```
Question: "What can analyze network traffic?"
Entity: "Wireshark"

Rule 1: +0.0 (not in key_terms)
Rule 2: +0.0 (not in question)
Rule 3: +0.0 (no token overlap)
Rule 4: +3.0 (if type="tool" and "tool" in question)
Total: 3.0
```

**Result**: Still gets some points if type matches.

### Case 2: Multiple Word Entity

```
Question: "What detects intrusions?"
Entity: "Intrusion Detection System"

Rule 1: +0.0
Rule 2: +5.0 ("intrusion detection" in question)
Rule 3: +4.0 (2 tokens: "intrusion", "detection")
Rule 4: +0.0
Total: 9.0
```

**Result**: Multi-word entities can score well through substring and token overlap.

### Case 3: Short Entity Names

```python
if len(entity_lower) > 2 and entity_lower in question_lower:
    score += 5.0
```

**Why**: Prevents matching very short words (like "a", "an", "is") that might appear in many questions.

---

## Scoring Visualization

### Example: Multiple Entities Scored

```
Question: "What tool uses intrusion detection?"

Entity Scoring Results:
┌─────────────────────┬──────┬──────┬──────┬──────┬────────┐
│ Entity              │ R1   │ R2   │ R3   │ R4   │ Total   │
├─────────────────────┼──────┼──────┼──────┼──────┼────────┤
│ Snort               │ 10.0 │  5.0 │  0.0 │  3.0 │  18.0  │
│ Intrusion Detection │  0.0 │  5.0 │  4.0 │  0.0 │   9.0  │
│ IDS                 │  0.0 │  0.0 │  0.0 │  3.0 │   3.0  │
│ Nmap                │  0.0 │  0.0 │  0.0 │  3.0 │   3.0  │
│ network attacks     │  0.0 │  0.0 │  2.0 │  0.0 │   2.0  │
└─────────────────────┴──────┴──────┴──────┴──────┴────────┘

Legend:
R1 = Rule 1 (Exact Match)
R2 = Rule 2 (Substring Match)
R3 = Rule 3 (Token Overlap)
R4 = Rule 4 (Type Match)
```

---

## Code Flow Diagram

```
┌─────────────────────────────────────────┐
│ find_relevant_entities(question)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Get key_terms and question_tokens       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ For each entity in knowledge graph:     │
│   score = 0.0                           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Rule 1: Exact Match?                   │
│   if entity_name in key_terms:          │
│       score += 10.0                     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Rule 2: Substring Match?                │
│   if entity_lower in question_lower:     │
│       score += 5.0                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Rule 3: Token Overlap?                  │
│   overlap = len(question_tokens &        │
│                entity_tokens)            │
│   score += overlap * 2.0                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Rule 4: Type/Category Match?            │
│   if type/category in question:          │
│       score += 3.0                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ if score > 0:                           │
│     entity_scores.append((name, score)) │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Sort by score (highest first)           │
│ Return top 10 entities                  │
└─────────────────────────────────────────┘
```

---

## Why This Scoring System?

### Advantages

1. **Fast**: Simple string matching, no complex computations
2. **Interpretable**: Can explain why each entity scored what it did
3. **Multi-Factor**: Considers multiple signals (exact match, substring, tokens, type)
4. **Weighted**: More important signals (exact match) get higher weights

### Design Decisions

1. **Exact Match Gets Highest Weight (10.0)**: Explicit mentions are strongest signal
2. **Substring Match Gets Medium Weight (5.0)**: Partial matches still relevant
3. **Token Overlap Gets Incremental Weight (2.0 per token)**: More shared words = more relevant
4. **Type Match Gets Bonus (3.0)**: Helps when question asks for specific type

---

## Summary

Entity relevance scoring:

1. **Iterates** through all entities in knowledge graph
2. **Scores** each entity using 4 rules:
   - Exact match: +10.0
   - Substring match: +5.0
   - Token overlap: +2.0 per token
   - Type match: +3.0
3. **Filters** entities with score = 0
4. **Sorts** by score (highest first)
5. **Returns** top 10 most relevant entities

The scoring system is **heuristic-based** (rule-based) rather than learned, making it fast, interpretable, and immediately usable without training.
