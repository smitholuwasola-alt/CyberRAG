# Exact Process: How Knowledge Graph is Constructed from Triples

## Overview

This document explains **exactly** how the `load_triples()` method transforms CSV triples into a NetworkX graph structure.

---

## Step-by-Step Construction Process

### Initial State

Before processing triples:
```python
self.graph = nx.MultiDiGraph()  # Empty graph
self.triples = []                # Empty list
```

**Graph State**: 
- Nodes: `[]` (empty)
- Edges: `[]` (empty)

---

### Step 1: Read Triples CSV File

**Code**:
```python
df = pd.read_csv(f"{self.dataset_path}/all_triples.csv")
```

**Input File Structure** (`all_triples.csv`):
```csv
e1,r,e2
Attacks,can_harm,public domain
IDS,uses,Intrusion Detection
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
packet logger,is_part_of,Snort
```

**Result**: DataFrame with 3 columns: `e1`, `r`, `e2`

---

### Step 2: Iterate Through Each Row

**Code**:
```python
for _, row in df.iterrows():
    e1 = str(row['e1']).strip()  # Subject entity (source)
    r = str(row['r']).strip()     # Relation type
    e2 = str(row['e2']).strip()  # Object entity (target)
```

**For each triple row, extract**:
- `e1`: Subject entity (will become source node)
- `r`: Relation type (will become edge label)
- `e2`: Object entity (will become target node)

**Example (Row 1)**:
```python
e1 = "Attacks"
r = "can_harm"
e2 = "public domain"
```

---

### Step 3: Validate Triple

**Code**:
```python
if e1 and r and e2:
    # Process triple
```

**What It Does**:
- Checks that all three components are non-empty
- Skips rows with missing data
- Only processes valid triples

**Example**:
- ✅ Valid: `("Snort", "can_detect", "network attacks")`
- ❌ Invalid: `("Snort", "", "network attacks")` → Skipped

---

### Step 4: Store Triple in List

**Code**:
```python
self.triples.append((e1, r, e2))
```

**What It Does**:
- Stores the triple as a tuple in the `triples` list
- Preserves the original triple data
- Used later for queries and exports

**Result After Row 1**:
```python
self.triples = [
    ("Attacks", "can_harm", "public domain")
]
```

---

### Step 5: Create Source Node (e1)

**Code**:
```python
if not self.graph.has_node(e1):
    self.graph.add_node(e1, label=e1)
```

**What It Does**:
- Checks if node `e1` already exists in graph
- If NOT exists: Creates new node with name `e1`
- Adds `label` attribute (same as node name)

**Example (Row 1: "Attacks")**:
```python
# Check: Does "Attacks" node exist?
# No → Create it
graph.add_node("Attacks", label="Attacks")
```

**Graph State After Step 5**:
```
Nodes: ["Attacks"]
Edges: []
```

**Visual**:
```
[Attacks]
```

---

### Step 6: Create Target Node (e2)

**Code**:
```python
if not self.graph.has_node(e2):
    self.graph.add_node(e2, label=e2)
```

**What It Does**:
- Checks if node `e2` already exists
- If NOT exists: Creates new node with name `e2`
- Adds `label` attribute

**Example (Row 1: "public domain")**:
```python
# Check: Does "public domain" node exist?
# No → Create it
graph.add_node("public domain", label="public domain")
```

**Graph State After Step 6**:
```
Nodes: ["Attacks", "public domain"]
Edges: []
```

**Visual**:
```
[Attacks]    [public domain]
```

---

### Step 7: Create Directed Edge

**Code**:
```python
self.graph.add_edge(e1, e2, relation=r, label=r)
```

**What It Does**:
- Creates a **directed edge** from `e1` to `e2`
- Labels the edge with relation type `r`
- Stores `relation` and `label` as edge attributes

**Parameters**:
- `e1`: Source node (from)
- `e2`: Target node (to)
- `relation=r`: Edge attribute storing relation type
- `label=r`: Edge attribute for visualization

**Example (Row 1)**:
```python
graph.add_edge("Attacks", "public domain", relation="can_harm", label="can_harm")
```

**Graph State After Step 7**:
```
Nodes: ["Attacks", "public domain"]
Edges: [("Attacks", "public domain", {"relation": "can_harm", "label": "can_harm"})]
```

**Visual**:
```
[Attacks] --can_harm--> [public domain]
```

---

### Step 8: Repeat for All Rows

The process repeats for each row in the CSV file.

**Example: Processing Row 2**

**Input**:
```csv
IDS,uses,Intrusion Detection
```

**Step-by-Step**:
1. Extract: `e1="IDS"`, `r="uses"`, `e2="Intrusion Detection"`
2. Validate: ✅ All present
3. Store triple: `("IDS", "uses", "Intrusion Detection")`
4. Check node "IDS": ❌ Not exists → Create node
5. Check node "Intrusion Detection": ❌ Not exists → Create node
6. Create edge: `IDS --uses--> Intrusion Detection`

**Graph State After Row 2**:
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection"]
Edges: [
    ("Attacks", "public domain", {"relation": "can_harm"}),
    ("IDS", "Intrusion Detection", {"relation": "uses"})
]
```

**Visual**:
```
[Attacks] --can_harm--> [public domain]

[IDS] --uses--> [Intrusion Detection]
```

---

### Step 9: Handle Duplicate Nodes

**Important**: If a node already exists, it's **not** recreated.

**Example: Processing Row 3**

**Input**:
```csv
Snort,uses,Intrusion Detection
```

**Process**:
1. Extract: `e1="Snort"`, `r="uses"`, `e2="Intrusion Detection"`
2. Check node "Snort": ❌ Not exists → **Create** node
3. Check node "Intrusion Detection": ✅ **Already exists** → **Skip creation**
4. Create edge: `Snort --uses--> Intrusion Detection`

**Key Point**: Node "Intrusion Detection" was created in Row 2, so it's reused here.

**Graph State After Row 3**:
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection", "Snort"]
Edges: [
    ("Attacks", "public domain", {"relation": "can_harm"}),
    ("IDS", "Intrusion Detection", {"relation": "uses"}),
    ("Snort", "Intrusion Detection", {"relation": "uses"})
]
```

**Visual**:
```
[Attacks] --can_harm--> [public domain]

[IDS] --uses--> [Intrusion Detection] <--uses-- [Snort]
```

---

### Step 10: Handle Multiple Edges Between Same Nodes

**NetworkX MultiDiGraph** allows multiple edges between the same pair of nodes.

**Example: Multiple Relations**

If we have:
```csv
Snort,uses,Intrusion Detection
Snort,can_detect,Intrusion Detection
```

**Result**: Two separate edges from "Snort" to "Intrusion Detection":
- Edge 1: `Snort --uses--> Intrusion Detection`
- Edge 2: `Snort --can_detect--> Intrusion Detection`

**Visual**:
```
[Snort] --uses--------> [Intrusion Detection]
         --can_detect-->
```

---

## Complete Example: Building Graph from 5 Triples

### Input Triples
```csv
e1,r,e2
Attacks,can_harm,public domain
IDS,uses,Intrusion Detection
Snort,uses,Intrusion Detection
Snort,can_detect,network attacks
packet logger,is_part_of,Snort
```

### Construction Process

#### After Row 1:
```
Nodes: ["Attacks", "public domain"]
Edges: [Attacks --can_harm--> public domain]
```

#### After Row 2:
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection"]
Edges: [
    Attacks --can_harm--> public domain,
    IDS --uses--> Intrusion Detection
]
```

#### After Row 3:
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection", "Snort"]
Edges: [
    Attacks --can_harm--> public domain,
    IDS --uses--> Intrusion Detection,
    Snort --uses--> Intrusion Detection
]
```

#### After Row 4:
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection", "Snort", "network attacks"]
Edges: [
    Attacks --can_harm--> public domain,
    IDS --uses--> Intrusion Detection,
    Snort --uses--> Intrusion Detection,
    Snort --can_detect--> network attacks
]
```

#### After Row 5 (Final):
```
Nodes: ["Attacks", "public domain", "IDS", "Intrusion Detection", "Snort", "network attacks", "packet logger"]
Edges: [
    Attacks --can_harm--> public domain,
    IDS --uses--> Intrusion Detection,
    Snort --uses--> Intrusion Detection,
    Snort --can_detect--> network attacks,
    packet logger --is_part_of--> Snort
]
```

**Final Visual Graph**:
```
[Attacks] --can_harm--> [public domain]

[IDS] --uses--> [Intrusion Detection] <--uses-- [Snort] --can_detect--> [network attacks]
                                                                    ↑
[packet logger] --is_part_of----------------------------------------|
```

---

## Key Code Logic Explained

### Node Creation Logic
```python
if not self.graph.has_node(e1):
    self.graph.add_node(e1, label=e1)
```

**Why Check First?**
- Prevents duplicate nodes
- More efficient (no need to recreate existing nodes)
- NetworkX allows duplicate node creation, but checking is cleaner

### Edge Creation Logic
```python
self.graph.add_edge(e1, e2, relation=r, label=r)
```

**What Happens**:
- Creates directed edge: `e1 → e2`
- Stores relation type as edge attribute
- Multiple edges between same nodes are allowed (MultiDiGraph)

### Triple Storage
```python
self.triples.append((e1, r, e2))
```

**Why Store Separately?**
- Preserves original triple data
- Used for queries and exports
- Graph structure and triple list serve different purposes

---

## Graph Properties

### After Construction

**Graph Type**: `networkx.MultiDiGraph`
- **Multi**: Multiple edges allowed between same nodes
- **Di**: Directed (edges have direction)
- **Graph**: Network structure

**Node Attributes**:
- `label`: Node name (same as node ID)

**Edge Attributes**:
- `relation`: Relation type (e.g., "can_detect", "uses")
- `label`: Relation type (for visualization)

---

## Complete Code Flow

```python
def load_triples(self):
    # Step 1: Read CSV
    df = pd.read_csv(f"{self.dataset_path}/all_triples.csv")
    
    # Step 2: Process each row
    for _, row in df.iterrows():
        # Step 3: Extract triple components
        e1 = str(row['e1']).strip()
        r = str(row['r']).strip()
        e2 = str(row['e2']).strip()
        
        # Step 4: Validate
        if e1 and r and e2:
            # Step 5: Store triple
            self.triples.append((e1, r, e2))
            
            # Step 6: Create source node (if not exists)
            if not self.graph.has_node(e1):
                self.graph.add_node(e1, label=e1)
            
            # Step 7: Create target node (if not exists)
            if not self.graph.has_node(e2):
                self.graph.add_node(e2, label=e2)
            
            # Step 8: Create directed edge
            self.graph.add_edge(e1, e2, relation=r, label=r)
    
    # Step 9: Report results
    print(f"Loaded {len(self.triples)} triples")
    print(f"Graph has {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
```

---

## Important Points

1. **Nodes Created On-Demand**: Nodes are created only when they appear in triples
2. **No Duplicate Nodes**: Same entity name = same node (checked before creation)
3. **Directed Edges**: All edges have direction (e1 → e2)
4. **Multiple Edges Allowed**: Same pair of nodes can have multiple edges with different relations
5. **Triples Preserved**: Original triple data stored separately from graph structure
6. **One Pass**: Graph built in single pass through CSV file

---

## Summary

**Input**: CSV file with triples (subject, relation, object)  
**Process**: For each triple:
1. Extract subject, relation, object
2. Create subject node (if new)
3. Create object node (if new)
4. Create directed edge (subject → object) with relation label

**Output**: NetworkX MultiDiGraph with:
- Nodes = Unique entities from triples
- Edges = Relationships from triples
- Edge labels = Relation types

The graph structure is built **entirely** from the triples CSV file, with each triple becoming one or two nodes and one edge in the graph.
