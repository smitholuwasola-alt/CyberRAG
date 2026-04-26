# Knowledge Graph Formation

## Overview

The knowledge graph is built from structured CSV files containing cybersecurity domain knowledge. The `KnowledgeGraphBuilder` class transforms these flat data files into a graph structure using NetworkX, where entities are nodes and relationships are edges.

## Data Sources

The knowledge graph is constructed from three CSV files in the `dataset/` directory:

1. **`all_entity_info.csv`** - Contains entity metadata
2. **`all_relation_info.csv`** - Contains relation type definitions
3. **`all_triples.csv`** - Contains subject-relation-object triples

---

## Step 1: Loading Entities (`load_entities`)

### Purpose
Load all entities (nodes) that will appear in the knowledge graph with their metadata.

### Process

1. **Read CSV File**: Loads `all_entity_info.csv` with columns:
   - `entityID`: Unique identifier
   - `entityName`: Name of the entity (e.g., "Snort", "Intrusion Detection")
   - `entityType`: Type classification (e.g., "feature", "app", "tool")
   - `entityCategory`: Category classification (e.g., "concept", "application", "security tool")
   - `entityDescription`: Optional description

2. **Create Entity Dictionary**: For each row, creates an entity object:
   ```python
   {
       'id': entity_id,
       'name': entity_name,
       'type': entity_type,
       'category': entity_category,
       'description': entity_description
   }
   ```

3. **Dual Indexing**: Stores entities twice for efficient lookup:
   - By `entityID`: `entities[entity_id] = entity_data`
   - By `entityName`: `entities[entity_name] = entity_data`
   
   This allows lookup by either ID or name.

### Example

**CSV Row**:
```csv
entityID,entityName,entityType,entityCategory,entityDescription
1,Snort,feature,security tool,Network intrusion detection system
```

**Result**:
```python
entities['1'] = {
    'id': '1',
    'name': 'Snort',
    'type': 'feature',
    'category': 'security tool',
    'description': 'Network intrusion detection system'
}
entities['Snort'] = { ... }  # Same data, indexed by name
```

### Why This Matters
Entities are the fundamental building blocks (nodes) of the graph. They represent cybersecurity concepts, tools, attacks, protocols, etc.

---

## Step 2: Loading Relations (`load_relations`)

### Purpose
Load all possible relationship types that can exist between entities.

### Process

1. **Read CSV File**: Loads `all_relation_info.csv` with a single column:
   - `relation`: The relation type name

2. **Store as Set**: Creates a set of all unique relation types

### Example Relations

Common relation types in the cybersecurity knowledge graph:

- `uses` - Entity A uses Entity B
- `can_detect` - Entity A can detect Entity B
- `can_analyze` - Entity A can analyze Entity B
- `can_exploit` - Entity A can exploit Entity B
- `can_harm` - Entity A can harm Entity B
- `is_a` - Entity A is a type of Entity B
- `has_a` - Entity A has Entity B as a component
- `is_part_of` - Entity A is part of Entity B
- `implements` - Entity A implements Entity B
- `can_expose` - Entity A can expose Entity B

### Example

**CSV File**:
```csv
relation
uses
can_detect
can_analyze
...
```

**Result**:
```python
relations = {'uses', 'can_detect', 'can_analyze', 'can_exploit', ...}
```

### Why This Matters
Relations define how entities connect to each other. They represent semantic relationships in the cybersecurity domain.

---

## Step 3: Loading Triples and Building Graph (`load_triples`)

### Purpose
Load subject-relation-object triples and construct the actual graph structure.

### Process

1. **Read CSV File**: Loads `all_triples.csv` with columns:
   - `e1`: Subject entity (source node)
   - `r`: Relation type (edge label)
   - `e2`: Object entity (target node)

2. **For Each Triple**:
   - Validates that all three components (e1, r, e2) are non-empty
   - Adds the triple to the `triples` list
   - **Adds nodes to graph**:
     - If `e1` doesn't exist as a node, creates it
     - If `e2` doesn't exist as a node, creates it
   - **Adds edge to graph**:
     - Creates a directed edge from `e1` to `e2`
     - Labels the edge with the relation type `r`
     - Stores relation as edge attribute

3. **Graph Structure**: Uses NetworkX `MultiDiGraph`:
   - **Multi**: Allows multiple edges between same pair of nodes
   - **Di**: Directed (edges have direction: e1 → e2)
   - **Graph**: Network structure

### Example

**CSV Row**:
```csv
e1,r,e2
Snort,can_detect,network attacks
```

**Graph Construction**:
```
1. Check if "Snort" node exists → Create if not
2. Check if "network attacks" node exists → Create if not
3. Add edge: Snort --[can_detect]--> network attacks
```

**Visual Representation**:
```
[Snort] --can_detect--> [network attacks]
```

### Multiple Triples Example

**CSV Rows**:
```csv
e1,r,e2
Snort,can_detect,network attacks
Snort,uses,Intrusion Detection
Snort,can_analyze,traffic
packet logger,is_part_of,Snort
```

**Resulting Graph**:
```
                    [Intrusion Detection]
                           ↑
                           | uses
                           |
                    [Snort] --can_detect--> [network attacks]
                     ↑  |
                     |  | can_analyze
                     |  ↓
[packet logger]      [traffic]
  is_part_of
```

### Why MultiDiGraph?

- **Multiple Relations**: Same entities can have multiple relationship types
  - Example: "Snort uses Intrusion Detection" AND "Snort can_detect Attacks"
- **Direction Matters**: Relations are directional
  - "Snort can_detect Attacks" ≠ "Attacks can_detect Snort"

---

## Step 4: Complete Build Process (`build_graph`)

### Orchestration

The `build_graph()` method coordinates all three loading steps:

```python
def build_graph(self):
    self.load_entities()      # Step 1: Load entity metadata
    self.load_relations()     # Step 2: Load relation types
    self.load_triples()       # Step 3: Build graph structure
```

### Execution Order

1. **Entities First**: Must load entities before triples (to understand what entities exist)
2. **Relations Second**: Load relation types (for validation/understanding)
3. **Triples Last**: Build the graph by connecting entities with relations

### Result

After `build_graph()` completes, you have:

- **Graph Structure**: NetworkX MultiDiGraph with nodes and edges
- **Entity Dictionary**: All entities indexed by ID and name
- **Relation Set**: All possible relation types
- **Triple List**: All subject-relation-object statements

---

## Graph Structure Details

### Nodes (Entities)

Each node in the graph represents an entity:
- **Node ID**: The entity name (e.g., "Snort", "Intrusion Detection")
- **Node Attributes**: Can store additional metadata (currently just `label`)

### Edges (Relations)

Each edge represents a relationship:
- **Source Node**: Subject entity (e1)
- **Target Node**: Object entity (e2)
- **Edge Attributes**:
  - `relation`: The relation type (e.g., "can_detect")
  - `label`: Same as relation (for visualization)

### Graph Properties

- **Directed**: Edges have direction (A → B ≠ B → A)
- **Multi-graph**: Multiple edges allowed between same nodes
- **Labeled**: Edges are labeled with relation types

---

## Data Flow Example

### Input Files

**all_entity_info.csv**:
```csv
entityID,entityName,entityType,entityCategory
1,Snort,feature,security tool
2,Intrusion Detection,feature,concept
3,network attacks,feature,concept
```

**all_relation_info.csv**:
```csv
relation
can_detect
uses
```

**all_triples.csv**:
```csv
e1,r,e2
Snort,can_detect,network attacks
Snort,uses,Intrusion Detection
```

### Processing Steps

1. **Load Entities**:
   ```python
   entities = {
       '1': {'id': '1', 'name': 'Snort', 'type': 'feature', ...},
       'Snort': {...},
       '2': {'id': '2', 'name': 'Intrusion Detection', ...},
       'Intrusion Detection': {...},
       ...
   }
   ```

2. **Load Relations**:
   ```python
   relations = {'can_detect', 'uses'}
   ```

3. **Load Triples & Build Graph**:
   ```python
   # Create nodes
   graph.add_node('Snort', label='Snort')
   graph.add_node('network attacks', label='network attacks')
   graph.add_node('Intrusion Detection', label='Intrusion Detection')
   
   # Create edges
   graph.add_edge('Snort', 'network attacks', relation='can_detect', label='can_detect')
   graph.add_edge('Snort', 'Intrusion Detection', relation='uses', label='uses')
   
   # Store triples
   triples = [
       ('Snort', 'can_detect', 'network attacks'),
       ('Snort', 'uses', 'Intrusion Detection')
   ]
   ```

### Final Graph Structure

```
Nodes: ['Snort', 'network attacks', 'Intrusion Detection']
Edges: 
  - Snort → network attacks (can_detect)
  - Snort → Intrusion Detection (uses)
```

---

## Graph Persistence

### Saving (`save_graph`)

Saves the complete graph state to a pickle file:

```python
{
    'graph': networkx_graph,
    'entities': entities_dict,
    'relations': relations_set,
    'triples': triples_list
}
```

**Why Pickle?**
- Preserves NetworkX graph object structure
- Fast serialization/deserialization
- Maintains all graph properties

### Loading (`load_graph`)

Restores the graph from a saved pickle file, avoiding rebuild time.

**Use Case**: If graph is already built, load it instead of rebuilding from CSV files.

---

## Graph Query Operations

Once built, the graph supports various query operations:

### 1. Get Entity Info (`get_entity_info`)
Returns metadata for a specific entity.

### 2. Find Related Entities (`find_related_entities`)
Finds all entities connected to a given entity:
- **Outgoing edges**: Entities this entity points to
- **Incoming edges**: Entities that point to this entity
- Can filter by relation type

### 3. Search Entities (`search_entities`)
Finds entities by name (case-insensitive partial match).

### 4. Get Path Between Entities (`get_path_between_entities`)
Finds all paths connecting two entities (up to specified length).

**Example**: Find path from "Snort" to "Attacks"
```
Snort → can_detect → network attacks → is_a → Attacks
```

### 5. Get Subgraph (`get_subgraph`)
Extracts a subgraph around specific entities (includes neighbors up to specified depth).

---

## Graph Statistics

After building, the graph contains:

- **Nodes**: Number of unique entities
- **Edges**: Number of triples/relationships
- **Relations**: Number of unique relation types
- **Triples**: Total number of knowledge statements

**Example Output**:
```
Loaded 964 entities
Loaded 10 relation types
Loaded 730 triples
Graph has 964 nodes and 730 edges
```

---

## Knowledge Graph Characteristics

### Domain-Specific
- Focused on cybersecurity concepts
- Entities: tools, attacks, protocols, vulnerabilities, etc.
- Relations: uses, detects, exploits, harms, etc.

### Structured Knowledge
- Explicit relationships (not inferred)
- Human-curated or extracted from structured sources
- Each triple represents a factual statement

### Queryable
- Can traverse relationships
- Can find paths between concepts
- Can extract subgraphs for specific topics

---

## Advantages of This Approach

1. **Explicit Knowledge**: All relationships are explicitly defined
2. **Fast Queries**: Graph traversal is efficient
3. **Interpretable**: Can trace back to source triples
4. **Extensible**: Easy to add new entities and relations
5. **Structured**: Maintains semantic relationships

---

## Limitations

1. **Static**: Graph doesn't learn or update automatically
2. **Coverage**: Limited to what's in the dataset
3. **No Implicit Knowledge**: Only explicit relationships stored
4. **Vocabulary**: Must match entity names exactly (case-sensitive matching)

---

## Summary

The knowledge graph formation process:

1. **Load Entities** → Create node metadata dictionary
2. **Load Relations** → Define relationship types
3. **Load Triples** → Build graph structure (nodes + edges)
4. **Result** → Queryable knowledge graph with entities as nodes and relations as edges

The graph transforms flat CSV data into a structured, queryable network that represents cybersecurity domain knowledge, enabling semantic queries and relationship traversal for question answering.
