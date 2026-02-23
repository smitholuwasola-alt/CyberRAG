# Knowledge Graph Building - Visual Guide

## The Transformation Process

### Input: CSV Files (Flat Data)

```
┌─────────────────────────────────────┐
│   all_entity_info.csv               │
├─────────────────────────────────────┤
│ ID │ Name      │ Type │ Category   │
├────┼───────────┼──────┼────────────┤
│ 1  │ Snort     │ tool │ application│
│ 2  │ Nmap      │ tool │ application│
│ 3  │ Packet    │ data │ concept    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   all_relation_info.csv             │
├─────────────────────────────────────┤
│ relation                            │
├─────────────────────────────────────┤
│ uses                                │
│ can_analyze                         │
│ has_a                               │
│ is_part_of                          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   all_triples.csv                   │
├─────────────────────────────────────┤
│ e1      │ r          │ e2           │
├─────────┼────────────┼──────────────┤
│ Snort   │ uses       │ Intrusion... │
│ Snort   │ can_detect │ network...   │
│ packet  │ is_part_of │ Snort        │
└─────────────────────────────────────┘
```

### Output: NetworkX Graph (Structured Data)

```
                    [Intrusion Detection]
                            ↑
                            │ uses
                    ┌───────┴───────┐
                    │               │
              [Snort]               │
              /  │  \               │
    is_part_of   │   can_detect     │
         /       │        \         │
[packet logger]  │    [network attacks]
                 │
          can_analyze
                 │
            [traffic]
```

## Step-by-Step Construction

### Step 1: Load Entities
```
CSV Row: 1,Snort,tool,application,
         ↓
Entity Dictionary:
{
  '1': {
    'id': '1',
    'name': 'Snort',
    'type': 'tool',
    'category': 'application'
  },
  'Snort': { ... }  # Also indexed by name
}
```

### Step 2: Load Relations
```
CSV: uses, can_analyze, has_a, ...
     ↓
Relations Set: {'uses', 'can_analyze', 'has_a', ...}
```

### Step 3: Build Graph from Triples

**Triple 1:** `(Snort, uses, Intrusion Detection)`
```
Before: Empty graph

After:  [Snort] --uses--> [Intrusion Detection]
```

**Triple 2:** `(Snort, can_detect, network attacks)`
```
Before: [Snort] --uses--> [Intrusion Detection]

After:  [Snort] --uses--> [Intrusion Detection]
         │
         └--can_detect--> [network attacks]
```

**Triple 3:** `(packet logger, is_part_of, Snort)`
```
Before: [Snort] --uses--> [Intrusion Detection]
         │
         └--can_detect--> [network attacks]

After:  [packet logger] --is_part_of--> [Snort] --uses--> [Intrusion Detection]
                                          │
                                          └--can_detect--> [network attacks]
```

## Data Structure Comparison

### Before (CSV - Flat)
```
Triple: Snort,uses,Intrusion Detection
Triple: Snort,can_detect,network attacks
Triple: packet logger,is_part_of,Snort
```
- No connections visible
- Hard to query relationships
- Sequential access only

### After (Graph - Structured)
```
Node: Snort
  ├─→ Edge (uses) → Node: Intrusion Detection
  ├─→ Edge (can_detect) → Node: network attacks
  └─← Edge (is_part_of) ← Node: packet logger
```
- Clear connections
- Easy to traverse
- Fast relationship queries

## Real Example: Snort Subgraph

### From Dataset Triples:
```
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
Snort,can_analyze,traffic
packet logger,is_part_of,Snort
Packet Decoder,is_part_of,Snort
Preprocessor,is_part_of,Snort
Detection Engine,is_part_of,Snort
Detection Engine,uses,detection technique
```

### Graph Structure:
```
                    [Intrusion Detection]
                            ↑
                            │ uses
                    ┌───────┴───────┐
                    │               │
              [Snort]               │
         ┌──────┼──────┐             │
         │     │      │             │
    is_part_of│      │can_detect    │
         │     │      │             │
    [packet]   │      └──→ [network │
    [logger]   │            attacks] │
               │                    │
    [Packet]   │                    │
    [Decoder]  │                    │
               │                    │
    [Preprocessor]                  │
               │                    │
    [Detection Engine]              │
               │                    │
               └──uses──→ [detection│
                          technique]│
                                    │
                            can_analyze
                                    │
                              [traffic]
```

## Code Flow Visualization

```
main()
  │
  ├─→ KnowledgeGraphBuilder.__init__()
  │     │
  │     ├─→ self.graph = nx.MultiDiGraph()
  │     ├─→ self.entities = {}
  │     ├─→ self.relations = set()
  │     └─→ self.triples = []
  │
  └─→ build_graph()
        │
        ├─→ load_entities()
        │     │
        │     ├─→ Read all_entity_info.csv
        │     ├─→ For each row:
        │     │     Create entity dict
        │     │     Store by ID and name
        │     └─→ Result: entities dictionary
        │
        ├─→ load_relations()
        │     │
        │     ├─→ Read all_relation_info.csv
        │     └─→ Result: relations set
        │
        └─→ load_triples()
              │
              ├─→ Read all_triples.csv
              ├─→ For each triple (e1, r, e2):
              │     │
              │     ├─→ Add node e1 (if new)
              │     ├─→ Add node e2 (if new)
              │     └─→ Add edge e1 → e2 with relation=r
              │
              └─→ Result: Complete graph
```

## Key Operations

### 1. Adding a Node
```python
if not self.graph.has_node("Snort"):
    self.graph.add_node("Snort", label="Snort")
```
Result: Node "Snort" exists in graph

### 2. Adding an Edge
```python
self.graph.add_edge("Snort", "Intrusion Detection", 
                    relation="uses", label="uses")
```
Result: Directed edge from Snort to Intrusion Detection

### 3. Querying
```python
# Find what Snort is connected to
neighbors = list(self.graph.successors("Snort"))
# Returns: ["Intrusion Detection", "network attacks", "traffic", ...]
```

## Statistics

After building from the dataset:
- **Entities**: ~964 unique entities
- **Triples**: ~730 relationships
- **Relations**: 9 types
- **Graph Nodes**: ~964 (one per unique entity in triples)
- **Graph Edges**: ~730 (one per triple)

## Why This Structure?

### Benefits:
1. **Fast Queries**: O(1) node lookup, O(degree) neighbor access
2. **Relationship Discovery**: Easy to find paths between entities
3. **Subgraph Extraction**: Can focus on specific domains
4. **Traversal**: Can walk the graph following relationships
5. **Visualization**: Can be visualized as a network diagram

### Use Cases:
- "What does Snort use?" → Follow "uses" edges from Snort
- "What is part of Snort?" → Follow "is_part_of" edges to Snort
- "How are Snort and Nmap related?" → Find paths between them
- "Show me all tools" → Filter entities by type="tool"
