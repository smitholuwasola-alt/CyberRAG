# Use of `all_relation_info.csv`

## Overview

The `all_relation_info.csv` file defines the **vocabulary of relation types** (the "schema") that can exist in the knowledge graph. While it doesn't build the graph structure, it serves several important purposes.

---

## What It Contains

**File Structure**:
```csv
relation
uses
can_detect
can_analyze
can_exploit
can_harm
is_a
has_a
is_part_of
implements
can_expose
```

**Purpose**: Lists all valid relation types that can appear in triples.

---

## Uses in the Codebase

### 1. **Schema Definition & Storage**

**Location**: `kg_builder.py` - `load_relations()`

**Code**:
```python
def load_relations(self):
    df = pd.read_csv(f"{self.dataset_path}/all_relation_info.csv")
    self.relations = set(df['relation'].tolist())
    # Result: {'uses', 'can_detect', 'is_a', 'has_a', ...}
```

**What It Does**:
- Loads all relation types into a set
- Stores them in `self.relations` for reference
- Provides a complete list of valid relation types

**Why Important**:
- Documents what relations are valid in the knowledge graph
- Provides a reference for what relation types exist
- Enables schema-aware operations

---

### 2. **Relation Filtering in Queries**

**Location**: `kg_builder.py` - `find_related_entities()`

**Code**:
```python
def find_related_entities(self, entity_name: str, relation_type: str = None):
    """Find entities related to a given entity"""
    related = []
    
    # Find outgoing edges
    for neighbor in self.graph.successors(entity_name):
        for edge_data in self.graph[entity_name][neighbor].values():
            rel = edge_data.get('relation', '')
            # ← FILTER by relation_type if provided
            if not relation_type or rel == relation_type:
                related.append((neighbor, rel, 'outgoing'))
    
    # Find incoming edges
    for neighbor in self.graph.predecessors(entity_name):
        for edge_data in self.graph[neighbor][entity_name].values():
            rel = edge_data.get('relation', '')
            # ← FILTER by relation_type if provided
            if not relation_type or rel == relation_type:
                related.append((neighbor, rel, 'incoming'))
    
    return related
```

**What It Does**:
- Allows filtering related entities by specific relation type
- If `relation_type` is provided, only returns entities connected via that relation
- If `relation_type` is `None`, returns all related entities

**Example Usage**:
```python
# Get all entities related to "Snort"
all_related = kg.find_related_entities("Snort")
# Returns: [('network attacks', 'can_detect', 'outgoing'), 
#           ('Intrusion Detection', 'uses', 'outgoing'), ...]

# Get only entities connected via "can_detect" relation
detects_only = kg.find_related_entities("Snort", relation_type="can_detect")
# Returns: [('network attacks', 'can_detect', 'outgoing')]
```

**Why Important**:
- Enables targeted queries (e.g., "What can Snort detect?" vs "What does Snort use?")
- Allows filtering by relation semantics
- Supports more precise knowledge retrieval

---

### 3. **Graph Persistence (Save/Load)**

**Location**: `kg_builder.py` - `save_graph()` and `load_graph()`

**Code**:
```python
def save_graph(self, filename: str = "knowledge_graph.pkl"):
    with open(filename, 'wb') as f:
        pickle.dump({
            'graph': self.graph,
            'entities': self.entities,
            'relations': list(self.relations),  # ← Saved with graph
            'triples': self.triples
        }, f)

def load_graph(self, filename: str = "knowledge_graph.pkl"):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
        self.graph = data['graph']
        self.entities = data['entities']
        self.relations = set(data['relations'])  # ← Restored from saved file
        self.triples = data['triples']
```

**What It Does**:
- Saves the relations set along with the graph
- Restores relations when loading a saved graph
- Ensures relations are available even after loading from pickle

**Why Important**:
- Maintains schema information with saved graphs
- Allows filtering operations even after loading from file
- Preserves complete knowledge graph state

---

### 4. **Graph Export (JSON Format)**

**Location**: `kg_builder.py` - `export_to_json()`

**Code**:
```python
def export_to_json(self, filename: str = "knowledge_graph.json"):
    graph_data = {
        'nodes': [],
        'edges': [],
        'entities': self.entities,
        'relations': list(self.relations)  # ← Included in export
    }
    # ... add nodes and edges ...
    json.dump(graph_data, f, indent=2)
```

**What It Does**:
- Includes relations list in JSON export
- Provides schema information in exported format
- Makes relation types available to external tools

**Why Important**:
- Enables other tools to know what relations are valid
- Provides complete graph metadata in export
- Supports interoperability with other systems

---

### 5. **Query Engine Context (Indirect Use)**

**Location**: `query_engine.py` - `extract_relation_keywords()`

**Code**:
```python
def extract_relation_keywords(self, question: str) -> List[str]:
    """Extract relation keywords from question"""
    question_lower = question.lower()
    relation_keywords = []
    
    # Map question patterns to relations
    relation_patterns = {
        'uses': ['uses', 'utilizes', 'employs', 'applies'],
        'can_analyze': ['analyzes', 'examines', 'inspects', 'monitors'],
        'can_detect': ['detects', 'identifies', 'finds', 'discovers'],
        # ... more patterns ...
    }
    
    for relation, patterns in relation_patterns.items():
        for pattern in patterns:
            if pattern in question_lower:
                relation_keywords.append(relation)
                break
    
    return relation_keywords
```

**What It Does**:
- Maps natural language to relation types
- Uses relation types from the schema (implicitly)
- Helps identify what type of relationship the question is asking about

**Why Important**:
- Enables semantic understanding of questions
- Can filter graph queries by identified relation types
- Improves answer relevance

**Note**: While this doesn't directly use `self.relations`, it uses the same relation types defined in the CSV, showing the schema's importance.

---

## What It Does NOT Do

### ❌ **Graph Structure Creation**
- Relations CSV does NOT create graph nodes or edges
- Only triples CSV creates the graph structure

### ❌ **Validation of Triples**
- Does NOT validate if relations in triples are valid
- Triples are loaded as-is without checking against relations set
- No error if triple contains relation not in relations CSV

### ❌ **Required for Graph Building**
- Graph can be built without relations CSV
- Relations come from triples, not from relations CSV
- Relations CSV is informational/referential

---

## Practical Examples

### Example 1: Filtering by Relation Type

```python
# Build knowledge graph
kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

# Find all entities that Snort can detect
detects = kg.find_related_entities("Snort", relation_type="can_detect")
# Uses relations CSV to know "can_detect" is a valid filter

# Find all entities that Snort uses
uses = kg.find_related_entities("Snort", relation_type="uses")
# Uses relations CSV to know "uses" is a valid filter
```

### Example 2: Schema Inspection

```python
# Check what relation types exist
kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

print("Available relation types:")
for rel in sorted(kg.relations):
    print(f"  - {rel}")

# Output:
# Available relation types:
#   - can_analyze
#   - can_detect
#   - can_exploit
#   - can_expose
#   - can_harm
#   - has_a
#   - implements
#   - is_a
#   - is_part_of
#   - uses
```

### Example 3: Targeted Query

```python
# Question: "What can Snort detect?"
# Query engine extracts "detect" → maps to "can_detect" relation
# Uses find_related_entities("Snort", relation_type="can_detect")
# Returns only entities connected via "can_detect" relation
```

---

## Summary Table

| Use Case | Location | Purpose | Required? |
|----------|----------|---------|-----------|
| **Schema Definition** | `load_relations()` | Store valid relation types | No (informational) |
| **Relation Filtering** | `find_related_entities()` | Filter queries by relation type | No (enhancement) |
| **Graph Persistence** | `save_graph()` / `load_graph()` | Save/restore schema | No (convenience) |
| **JSON Export** | `export_to_json()` | Include schema in export | No (metadata) |
| **Query Context** | `extract_relation_keywords()` | Map questions to relations | Indirect |

---

## Key Insights

1. **Not Required for Graph Building**: The graph structure is built entirely from triples CSV
2. **Schema Reference**: Provides a vocabulary of valid relation types
3. **Enables Filtering**: Allows filtering queries by specific relation types
4. **Metadata**: Serves as documentation of what relations exist
5. **Enhancement, Not Requirement**: Improves functionality but system works without it

---

## Analogy

Think of relations CSV like a **dictionary of relationship types**:

- **Triples CSV** = The actual sentences (e.g., "Snort can_detect attacks")
- **Relations CSV** = The vocabulary list (e.g., "can_detect, uses, is_a, ...")

You can read sentences without the dictionary, but the dictionary helps you:
- Understand what words are valid
- Filter sentences by word type
- Know the complete vocabulary

---

## Conclusion

The `all_relation_info.csv` file serves as a **schema definition** that:

✅ **Enables** relation-based filtering in queries  
✅ **Documents** what relation types are valid  
✅ **Enhances** query capabilities with targeted filtering  
✅ **Preserves** schema information in saved/exported graphs  

While not strictly required for graph building, it provides valuable functionality for querying and understanding the knowledge graph structure.
