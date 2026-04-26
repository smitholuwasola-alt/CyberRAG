# Purpose of Each CSV File in Knowledge Graph

## Overview

While **only the triples CSV is used to build the graph structure**, the entities and relations CSV files serve important purposes beyond graph creation.

---

## 1. `all_triples.csv` - Graph Structure Builder

### Primary Purpose
**Creates the actual graph structure** (nodes and edges)

### What It Does
- Defines which entities exist as nodes (from `e1` and `e2` columns)
- Creates edges between entities (using `r` relation column)
- Builds the NetworkX graph structure

### Usage in Code
```python
# In load_triples()
e1 = row['e1']  # Source entity name
r = row['r']    # Relation type
e2 = row['e2']  # Target entity name

# Creates graph nodes
graph.add_node(e1)
graph.add_node(e2)

# Creates graph edge
graph.add_edge(e1, e2, relation=r)
```

### Example
```csv
e1,r,e2
Snort,can_detect,network attacks
```
**Result**: Creates nodes "Snort" and "network attacks", connects them with "can_detect" edge.

### Why It's Essential
✅ **Without triples, there is no graph** - no nodes, no edges, no structure

---

## 2. `all_entity_info.csv` - Metadata & Enhanced Querying

### Primary Purpose
**Stores rich metadata about entities** that enhances query engine performance

### What It Contains
- `entityID`: Unique identifier
- `entityName`: Entity name (matches names in triples)
- `entityType`: Classification (e.g., "feature", "tool", "attack")
- `entityCategory`: Category (e.g., "security tool", "concept")
- `entityDescription`: Optional description

### Usage in Code

#### A. Entity Metadata Lookup
```python
# In query_engine.py - find_relevant_entities()
entity_data = self.kg.entities.get(entity_name)
entity_type = entity_data.get('type', '')
entity_category = entity_data.get('category', '')
```

#### B. Type-Based Scoring (Query Engine)
```python
# Lines 197-202 in query_engine.py
if isinstance(entity_data, dict):
    entity_type = entity_data.get('type', '').lower()
    entity_category = entity_data.get('category', '').lower()
    
    # Check if question mentions entity type
    if entity_type in question_lower or entity_category in question_lower:
        score += 3.0  # ← BONUS SCORE for type/category match!
```

**Example**:
```
Question: "What tool detects intrusions?"
Entity: "Snort" has type="tool", category="security tool"

Scoring:
- "tool" appears in question → +3.0 points
- This helps "Snort" rank higher than entities without type match
```

#### C. Visualization
```python
# In visualize_kg.py and create_interactive_viz.py
entity_info = kg_builder.get_entity_info(entity_name)
entity_type = entity_info.get('type', 'unknown')
# Used to color-code nodes by type in visualizations
```

### Why It's Important

✅ **Improves Query Accuracy**: Type/category matching helps identify relevant entities
✅ **Provides Context**: Entity descriptions and metadata add semantic information
✅ **Enables Filtering**: Can filter entities by type/category
✅ **Visualization**: Used for node coloring and categorization in graphs

### What Happens Without It

❌ Graph would still work (built from triples)
❌ But query engine would lose type-based scoring
❌ No metadata available for entities
❌ Visualizations would have no type information

---

## 3. `all_relation_info.csv` - Schema Definition & Validation

### Primary Purpose
**Defines the vocabulary of relation types** (the "schema" of relationships)

### What It Contains
- `relation`: List of all valid relation types (e.g., "uses", "can_detect", "is_a")

### Usage in Code

#### A. Schema Definition
```python
# In load_relations()
self.relations = set(df['relation'].tolist())
# Stores: {'uses', 'can_detect', 'is_a', 'has_a', ...}
```

#### B. Relation Filtering (Optional)
```python
# In find_related_entities()
def find_related_entities(self, entity_name: str, relation_type: str = None):
    # Can filter by relation_type if provided
    if not relation_type or rel == relation_type:
        related.append((neighbor, rel, 'outgoing'))
```

#### C. Export/Serialization
```python
# When saving/loading graph
{
    'graph': self.graph,
    'entities': self.entities,
    'relations': list(self.relations),  # ← Included in saved data
    'triples': self.triples
}
```

### Why It's Important

✅ **Schema Documentation**: Defines what relations are valid in the knowledge graph
✅ **Validation**: Can check if a relation type is valid
✅ **Filtering**: Enables filtering by relation type in queries
✅ **Completeness**: Ensures all relation types are known

### What Happens Without It

❌ Graph would still work (relations come from triples)
❌ But no way to know all valid relation types
❌ Can't validate if a relation type is legitimate
❌ Harder to filter queries by relation type

---

## Summary: What Each File Does

| CSV File | Graph Creation | Query Enhancement | Other Uses |
|----------|---------------|-------------------|------------|
| **`all_triples.csv`** | ✅ **ESSENTIAL** - Creates nodes & edges | ❌ Not used | Graph structure |
| **`all_entity_info.csv`** | ❌ Not used for structure | ✅ **IMPORTANT** - Type-based scoring | Visualization, metadata lookup |
| **`all_relation_info.csv`** | ❌ Not used for structure | ⚠️ **OPTIONAL** - Schema definition | Validation, filtering |

---

## Detailed Workflow

### Graph Building Phase

```
1. load_entities()
   └─> Reads all_entity_info.csv
   └─> Creates entities dictionary with metadata
   └─> Result: entities['Snort'] = {id, name, type, category, ...}

2. load_relations()
   └─> Reads all_relation_info.csv
   └─> Creates relations set
   └─> Result: relations = {'uses', 'can_detect', ...}

3. load_triples()
   └─> Reads all_triples.csv
   └─> Creates graph nodes (from e1, e2)
   └─> Creates graph edges (e1 → e2 with relation r)
   └─> Result: Graph structure with nodes and edges
```

### Query Phase

```
Question: "What tool detects intrusions?"

1. Extract entities from question
   └─> Finds "Snort" in question

2. Score entities (uses entity metadata!)
   └─> Gets entity_data = entities['Snort']
   └─> Checks if type="tool" or category="security tool" in question
   └─> If yes: score += 3.0 ← Uses entity_info.csv!

3. Query graph structure (uses triples!)
   └─> Finds edges: Snort --can_detect--> intrusions
   └─> Uses triples.csv data (graph structure)

4. Generate answer
   └─> Combines graph results + entity metadata
```

---

## Key Insight

**You're correct**: Only triples are used for graph creation.

**But**: Entities and relations CSV files enhance the system:

1. **Entities CSV** → Improves query accuracy through type-based scoring
2. **Relations CSV** → Provides schema definition and enables filtering

### Analogy

Think of it like a library:
- **Triples CSV** = The books and their connections (the actual library)
- **Entities CSV** = The card catalog with book metadata (helps you find books)
- **Relations CSV** = The classification system (defines categories like "fiction", "non-fiction")

You could browse the library without the catalog, but the catalog makes finding books much easier!

---

## Code Evidence

### Entity Type Used in Scoring
```python
# query_engine.py, lines 195-202
# Type-based matching
if isinstance(entity_data, dict):
    entity_type = entity_data.get('type', '').lower()
    entity_category = entity_data.get('category', '').lower()
    
    # Check if question mentions entity type
    if entity_type in question_lower or entity_category in question_lower:
        score += 3.0  # ← BONUS from entity_info.csv!
```

### Relations Used for Filtering
```python
# kg_builder.py, find_related_entities()
def find_related_entities(self, entity_name: str, relation_type: str = None):
    # Can filter by relation_type
    if not relation_type or rel == relation_type:
        related.append((neighbor, rel, 'outgoing'))
```

---

## Conclusion

- **Triples CSV**: Creates the graph (essential)
- **Entities CSV**: Enhances queries with metadata (important for accuracy)
- **Relations CSV**: Defines schema (useful for validation/filtering)

All three work together to create a complete, queryable knowledge graph system!
