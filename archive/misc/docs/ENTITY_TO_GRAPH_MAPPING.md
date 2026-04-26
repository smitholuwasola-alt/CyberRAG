# Entity Metadata to Graph Mapping

## Key Understanding

**Important**: The graph structure uses **entity NAMES** (not IDs) as node identifiers, while entity metadata (ID, type, category) is stored separately and can be looked up when needed.

---

## Two Separate Data Structures

### 1. Entity Metadata Dictionary (`self.entities`)

Stores rich information about each entity:

```python
entities = {
    '1': {                           # Indexed by ID
        'id': '1',
        'name': 'Snort',
        'type': 'feature',
        'category': 'security tool',
        'description': 'Network intrusion detection system'
    },
    'Snort': {                       # Also indexed by name (same data)
        'id': '1',
        'name': 'Snort',
        'type': 'feature',
        'category': 'security tool',
        'description': 'Network intrusion detection system'
    }
}
```

**Purpose**: Provides metadata about entities (type, category, description)

### 2. Graph Structure (`self.graph`)

Uses entity **NAMES** as node identifiers:

```python
# Graph nodes are entity NAMES
graph.nodes = ['Snort', 'Intrusion Detection', 'network attacks', ...]

# Graph edges connect entity NAMES
graph.edges = [
    ('Snort', 'network attacks'),    # e1 (name) → e2 (name)
    ('Snort', 'Intrusion Detection')
]
```

**Purpose**: Represents relationships between entities

---

## How They Connect

### The Mapping

```
Entity Metadata (ID, name, type, category)
         ↓
    [Lookup by name]
         ↓
Graph Nodes (entity names)
         ↓
Graph Edges (name → name with relation)
```

### Example Flow

**Step 1: Entity Metadata Loaded**
```python
# From all_entity_info.csv
entities['Snort'] = {
    'id': '1',
    'name': 'Snort',
    'type': 'feature',           # ← Metadata
    'category': 'security tool', # ← Metadata
    'description': '...'
}
```

**Step 2: Triple Loaded**
```python
# From all_triples.csv
# e1, r, e2
# Snort, can_detect, network attacks

e1 = "Snort"           # ← Entity NAME (not ID!)
r = "can_detect"       # ← Relation type
e2 = "network attacks" # ← Entity NAME (not ID!)
```

**Step 3: Graph Built Using Names**
```python
# Graph nodes created using entity NAMES
graph.add_node("Snort")                    # ← Uses name, not ID "1"
graph.add_node("network attacks")          # ← Uses name

# Graph edge connects NAMES
graph.add_edge("Snort", "network attacks", relation="can_detect")
```

**Step 4: Metadata Lookup When Needed**
```python
# When querying, can look up metadata by name
entity_info = entities.get("Snort")
# Returns: {'id': '1', 'name': 'Snort', 'type': 'feature', ...}
```

---

## Why This Design?

### Graph Uses Names (Not IDs)

**Reason**: Triples file uses entity names, not IDs

**Triples CSV Structure**:
```csv
e1,r,e2
Snort,can_detect,network attacks
```

The `e1` and `e2` columns contain **entity names**, not IDs. So the graph naturally uses names as node identifiers.

### Metadata Stored Separately

**Reason**: Allows rich metadata without cluttering graph structure

- Graph stays lightweight (just names and relations)
- Metadata can be queried when needed
- Can add/update metadata without changing graph structure

---

## Complete Example

### Input Data

**all_entity_info.csv**:
```csv
entityID,entityName,entityType,entityCategory
1,Snort,feature,security tool
2,Intrusion Detection,feature,concept
3,network attacks,feature,concept
```

**all_triples.csv**:
```csv
e1,r,e2
Snort,can_detect,network attacks
Snort,uses,Intrusion Detection
```

### Processing

**1. Entity Dictionary Created**:
```python
entities = {
    '1': {'id': '1', 'name': 'Snort', 'type': 'feature', ...},
    'Snort': {'id': '1', 'name': 'Snort', 'type': 'feature', ...},
    '2': {'id': '2', 'name': 'Intrusion Detection', ...},
    'Intrusion Detection': {'id': '2', 'name': 'Intrusion Detection', ...},
    '3': {'id': '3', 'name': 'network attacks', ...},
    'network attacks': {'id': '3', 'name': 'network attacks', ...}
}
```

**2. Graph Built Using Names**:
```python
# Nodes (using entity names from triples)
graph.nodes = ['Snort', 'network attacks', 'Intrusion Detection']

# Edges (connecting names)
graph.edges = [
    ('Snort', 'network attacks', {'relation': 'can_detect'}),
    ('Snort', 'Intrusion Detection', {'relation': 'uses'})
]
```

**3. Connection**:
```python
# When you have a graph node name, you can look up its metadata
node_name = "Snort"
metadata = entities.get(node_name)
# Returns: {'id': '1', 'name': 'Snort', 'type': 'feature', 'category': 'security tool'}

# You can also query by ID
metadata_by_id = entities.get('1')
# Returns: Same data
```

---

## What Gets Used Where?

### In Graph Structure (Nodes & Edges)

✅ **Entity Names** - Used as node identifiers
✅ **Relation Types** - Used as edge labels

❌ **Entity IDs** - NOT used in graph structure
❌ **Entity Types** - NOT stored in graph nodes (but can be looked up)
❌ **Entity Categories** - NOT stored in graph nodes (but can be looked up)

### In Entity Dictionary

✅ **Entity IDs** - Used as lookup keys
✅ **Entity Names** - Used as lookup keys (dual indexing)
✅ **Entity Types** - Stored as metadata
✅ **Entity Categories** - Stored as metadata
✅ **Entity Descriptions** - Stored as metadata

---

## Query Engine Usage

When the query engine processes a question:

### 1. Finds Entity Names in Graph
```python
# Query engine searches for entity names in question
question = "What does Snort detect?"
# Finds: "Snort" as a graph node
```

### 2. Looks Up Metadata When Needed
```python
# Can retrieve metadata for context
entity_info = kg_builder.get_entity_info("Snort")
# Returns: {'type': 'feature', 'category': 'security tool', ...}

# Uses type/category for scoring relevance
if entity_info.get('type') in question:
    score += 3.0  # Type-based matching bonus
```

### 3. Traverses Graph Using Names
```python
# Graph traversal uses entity names
related = kg_builder.find_related_entities("Snort")
# Returns: [('network attacks', 'can_detect', 'outgoing'), ...]
```

---

## Summary Table

| Component | What It Stores | Key Identifier | Used In |
|-----------|---------------|----------------|---------|
| **Entity Dictionary** | ID, name, type, category, description | ID or Name | Metadata lookup |
| **Graph Nodes** | Entity names only | Entity Name | Graph structure |
| **Graph Edges** | Source name → Target name + relation | Entity Names | Graph structure |
| **Triples** | (subject name, relation, object name) | Entity Names | Graph construction |

---

## Key Takeaway

**The graph structure uses entity NAMES, not IDs.**

- **Triples** connect entity names: `(Snort, can_detect, network attacks)`
- **Graph nodes** are entity names: `['Snort', 'network attacks']`
- **Graph edges** connect names: `Snort → network attacks`
- **Entity metadata** (ID, type, category) is stored separately and can be looked up by name when needed

This design allows:
- ✅ Graph to be built directly from triples (which use names)
- ✅ Metadata to be queried separately when needed
- ✅ Type/category information to be used for scoring without cluttering the graph

---

## Code Evidence

Looking at `load_triples()`:

```python
e1 = str(row['e1']).strip()  # ← Entity NAME from CSV
r = str(row['r']).strip()    # ← Relation type
e2 = str(row['e2']).strip() # ← Entity NAME from CSV

# Graph uses NAMES directly
graph.add_node(e1, label=e1)  # ← e1 is a name, not ID
graph.add_node(e2, label=e2)  # ← e2 is a name, not ID
graph.add_edge(e1, e2, relation=r)  # ← Connects names
```

The entity metadata (ID, type, category) is loaded separately and can be accessed via `get_entity_info(entity_name)` when needed, but the graph structure itself only uses names.
