# Knowledge Graph Builder - Detailed Explanation

## Overview

The Knowledge Graph Builder transforms the AISecKG dataset (stored in CSV files) into a structured graph that can be queried and traversed. This document explains the step-by-step process.

## Input Data Structure

The dataset consists of three CSV files:

### 1. `all_entity_info.csv` - Entity Metadata
Contains information about each entity in the knowledge graph.

**Structure:**
```
entityID,entityName,entityType,entityCategory,entityDescription
1,Private key,feature,concept,
2,Session Id,feature,concept,
3,Cookies,feature,concept,
...
```

**Fields:**
- `entityID`: Unique identifier
- `entityName`: Name of the entity (e.g., "Snort", "Nmap", "Packet")
- `entityType`: Type (tool, attack, feature, data, technique, etc.)
- `entityCategory`: Category (concept, application)
- `entityDescription`: Optional description

**Example:**
- Entity ID: 27
- Name: "Tcpdump"
- Type: "tool"
- Category: "application"

### 2. `all_relation_info.csv` - Relation Types
Lists all possible relation types in the knowledge graph.

**Structure:**
```
relation
has_a
can_analyze
can_expose
can_exploit
implements
uses
is_a
can_harm
part_of
```

**Total: 9 relation types**

### 3. `all_triples.csv` - Knowledge Graph Triples
Contains the actual relationships between entities in (subject, relation, object) format.

**Structure:**
```
e1,r,e2
Attacks,can_harm,public domain
IDS,uses,Intrusion Detection
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
packet logger,is_part_of,Snort
...
```

**Format:** (Entity1, Relation, Entity2)
- `e1`: Source entity (subject)
- `r`: Relation type
- `e2`: Target entity (object)

**Example Triples:**
- `(Snort, uses, Intrusion Detection)` - Snort uses Intrusion Detection
- `(Snort, can_detect, network attacks)` - Snort can detect network attacks
- `(packet logger, is_part_of, Snort)` - packet logger is part of Snort

## Graph Building Process

### Step 1: Initialize Graph Structure

```python
self.graph = nx.MultiDiGraph()  # MultiDiGraph for multiple relations
self.entities = {}               # Entity metadata dictionary
self.relations = set()           # Set of relation types
self.triples = []                # List of all triples
```

**Why MultiDiGraph?**
- Allows multiple edges between the same two nodes
- Example: "Snort" can both "use" and "can_analyze" "traffic"
- Directed: Relations have direction (A → B is different from B → A)

### Step 2: Load Entities (`load_entities()`)

```python
def load_entities(self):
    df = pd.read_csv(f"{self.dataset_path}/all_entity_info.csv")
    for _, row in df.iterrows():
        entity_id = str(row['entityID'])
        self.entities[entity_id] = {
            'id': entity_id,
            'name': row['entityName'],
            'type': row['entityType'],
            'category': row['entityCategory'],
            'description': row.get('entityDescription', '')
        }
        # Also index by name for easier lookup
        self.entities[row['entityName']] = self.entities[entity_id]
```

**What happens:**
1. Reads `all_entity_info.csv` using pandas
2. For each row, creates an entity dictionary with metadata
3. Stores entity by both ID and name for flexible lookup
4. Result: Dictionary mapping entity names/IDs to their metadata

**Example:**
```python
self.entities['Snort'] = {
    'id': '...',
    'name': 'Snort',
    'type': 'tool',
    'category': 'application',
    'description': ''
}
```

### Step 3: Load Relations (`load_relations()`)

```python
def load_relations(self):
    df = pd.read_csv(f"{self.dataset_path}/all_relation_info.csv")
    self.relations = set(df['relation'].tolist())
```

**What happens:**
1. Reads the relation types CSV
2. Converts to a set for fast lookup
3. Result: Set of 9 relation types

**Result:**
```python
self.relations = {
    'has_a', 'can_analyze', 'can_expose', 'can_exploit',
    'implements', 'uses', 'is_a', 'can_harm', 'part_of'
}
```

### Step 4: Load Triples and Build Graph (`load_triples()`)

This is the core step that actually constructs the graph:

```python
def load_triples(self):
    df = pd.read_csv(f"{self.dataset_path}/all_triples.csv")
    
    for _, row in df.iterrows():
        e1 = str(row['e1']).strip()  # Source entity
        r = str(row['r']).strip()     # Relation
        e2 = str(row['e2']).strip()   # Target entity
        
        if e1 and r and e2:
            # Store triple
            self.triples.append((e1, r, e2))
            
            # Add nodes to graph (if not already present)
            if not self.graph.has_node(e1):
                self.graph.add_node(e1, label=e1)
            if not self.graph.has_node(e2):
                self.graph.add_node(e2, label=e2)
            
            # Add edge with relation as attribute
            self.graph.add_edge(e1, e2, relation=r, label=r)
```

**What happens for each triple:**

1. **Parse Triple**: Extract e1 (source), r (relation), e2 (target)
   - Example: `("Snort", "uses", "Intrusion Detection")`

2. **Add Nodes**: 
   - If "Snort" not in graph → add node "Snort"
   - If "Intrusion Detection" not in graph → add node "Intrusion Detection"
   - Nodes are added with a `label` attribute

3. **Add Edge**:
   - Create directed edge: Snort → Intrusion Detection
   - Store relation type as edge attribute: `relation="uses"`
   - Also store as `label` for visualization

**Visual Representation:**

```
Before:  [Snort]  [Intrusion Detection]

After:   [Snort] --uses--> [Intrusion Detection]
```

**Multiple Relations Example:**

From the triples:
- `(Snort, uses, Intrusion Detection)`
- `(Snort, can_detect, network attacks)`
- `(Snort, can_analyze, traffic)`

The graph becomes:
```
[Snort] --uses--> [Intrusion Detection]
[Snort] --can_detect--> [network attacks]
[Snort] --can_analyze--> [traffic]
```

### Step 5: Complete Build Process (`build_graph()`)

```python
def build_graph(self):
    print("Building knowledge graph...")
    self.load_entities()      # Step 1: Load entity metadata
    self.load_relations()     # Step 2: Load relation types
    self.load_triples()       # Step 3: Build graph structure
    print("Knowledge graph built successfully!")
```

## Graph Structure Result

After building, you have:

### Nodes (Entities)
- **Total**: ~964 unique entities
- **Examples**: "Snort", "Nmap", "Packet", "Intrusion Detection", "network attacks"
- **Attributes**: Each node has a `label` attribute

### Edges (Relations)
- **Total**: ~730 edges (one per triple)
- **Direction**: Directed (A → B)
- **Attributes**: Each edge has `relation` and `label` attributes
- **Multiple edges**: Same pair of nodes can have multiple edges with different relations

### Example Subgraph

From the triples:
```
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
packet logger,is_part_of,Snort
Packet Decoder,is_part_of,Snort
Preprocessor,is_part_of,Snort
Detection Engine,is_part_of,Snort
```

The graph structure:
```
                    [Intrusion Detection]
                            ↑
                            | uses
                    [Snort] ────────────────┐
                    /  |  \                  │
         is_part_of    |    is_part_of        │ can_detect
         /             |             \        │
[packet logger]  [Packet Decoder]  [Preprocessor]  [Detection Engine]
                                                      ↓
                                              [network attacks]
```

## Query Capabilities

Once built, the graph supports various queries:

### 1. Entity Search
```python
kg.search_entities("Snort")
# Returns: ["Snort", "Snort rules", "Snort Status", ...]
```

### 2. Find Related Entities
```python
kg.find_related_entities("Snort")
# Returns: [
#   ("Intrusion Detection", "uses", "outgoing"),
#   ("network attacks", "can_detect", "outgoing"),
#   ("traffic", "can_analyze", "outgoing"),
#   ...
# ]
```

### 3. Find Paths
```python
kg.get_path_between_entities("Snort", "network attacks", max_length=2)
# Returns: [["Snort", "network attacks"]]
```

### 4. Get Subgraph
```python
kg.get_subgraph(["Snort", "Nmap"], depth=2)
# Returns: Subgraph containing Snort, Nmap, and their neighbors
```

## Data Flow Summary

```
CSV Files
    │
    ├── all_entity_info.csv ──┐
    │                         │
    ├── all_relation_info.csv─┤
    │                         │
    └── all_triples.csv ──────┤
                              │
                              ▼
                    KnowledgeGraphBuilder
                              │
                              ├── load_entities() ──→ entities dictionary
                              │
                              ├── load_relations() ─→ relations set
                              │
                              └── load_triples() ───→ NetworkX Graph
                              │
                              ▼
                    NetworkX MultiDiGraph
                    (Nodes + Edges with attributes)
                              │
                              ▼
                    Query Methods Available
                    (search, find_related, get_path, etc.)
```

## Key Design Decisions

### 1. Why MultiDiGraph?
- **Multiple Relations**: Same entities can have multiple relationship types
- **Example**: "Snort" → "traffic" can have both "uses" and "can_analyze"

### 2. Why Directed Graph?
- **Direction Matters**: "A uses B" ≠ "B uses A"
- **Semantic Correctness**: Relations have clear direction

### 3. Why Store Entities Separately?
- **Rich Metadata**: Entity info (type, category) not stored in graph nodes
- **Fast Lookup**: Dictionary lookup is O(1) vs graph traversal
- **Flexible Indexing**: Can search by ID or name

### 4. Why Store Triples List?
- **Backup Reference**: Original triple format preserved
- **Easy Export**: Can regenerate CSV from triples
- **Debugging**: Can verify graph matches source data

## Example: Building Graph for "Snort"

**Input Triples:**
```
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
Snort,can_analyze,traffic
packet logger,is_part_of,Snort
Packet Decoder,is_part_of,Snort
```

**Graph Construction:**
1. Add node "Snort"
2. Add node "Intrusion Detection"
3. Add edge: Snort → Intrusion Detection (relation="uses")
4. Add node "network attacks"
5. Add edge: Snort → network attacks (relation="can_detect")
6. Add node "traffic"
7. Add edge: Snort → traffic (relation="can_analyze")
8. Add node "packet logger"
9. Add edge: packet logger → Snort (relation="is_part_of")
10. Add node "Packet Decoder"
11. Add edge: Packet Decoder → Snort (relation="is_part_of")

**Result:**
- 5 nodes: Snort, Intrusion Detection, network attacks, traffic, packet logger, Packet Decoder
- 5 edges with different relations
- Can query: "What does Snort use?" → "Intrusion Detection"
- Can query: "What is part of Snort?" → "packet logger", "Packet Decoder"

## Performance Characteristics

- **Loading Time**: ~1-2 seconds for 730 triples
- **Memory**: ~50-100 MB for full graph
- **Node Lookup**: O(1) average case
- **Edge Traversal**: O(degree) where degree is number of connections
- **Path Finding**: O(V + E) for simple paths

## Conclusion

The Knowledge Graph Builder transforms flat CSV data into a rich, queryable graph structure. The process is straightforward:
1. Load entity metadata
2. Load relation types
3. Build graph from triples (nodes + edges)

This structure enables powerful queries like finding related entities, discovering paths, and extracting subgraphs - all essential for the question-answering system.
