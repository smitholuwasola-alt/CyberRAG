# Knowledge Graph Querying Guide

## Overview

Once a knowledge graph is built, you can query it in multiple ways to extract information, find relationships, and answer questions. This document explains all the querying methods available in the system.

---

## Query Methods Available

The knowledge graph supports several types of queries:

1. **Entity Information Retrieval** - Get metadata about entities
2. **Related Entity Discovery** - Find connected entities
3. **Entity Search** - Search entities by name
4. **Path Finding** - Find connections between entities
5. **Subgraph Extraction** - Extract focused subgraphs
6. **Question Answering** - Natural language queries

---

## 1. Entity Information Retrieval

### Method: `get_entity_info(entity_name)`

**Purpose**: Retrieve metadata about a specific entity

**How It Works**:
```python
entity_info = kg_builder.get_entity_info("Snort")
```

**Returns**:
```python
{
    'id': '1',
    'name': 'Snort',
    'type': 'feature',
    'category': 'security tool',
    'description': 'Network intrusion detection system'
}
```

**Use Cases**:
- Get entity type/category for classification
- Retrieve entity descriptions
- Access entity metadata for scoring in queries

**Example**:
```python
# Get information about Snort
info = kg.get_entity_info("Snort")
print(f"Type: {info['type']}")
print(f"Category: {info['category']}")
```

---

## 2. Related Entity Discovery

### Method: `find_related_entities(entity_name, relation_type=None)`

**Purpose**: Find all entities connected to a given entity

**How It Works**:
1. Locates the entity in the graph
2. Finds all **outgoing edges** (entities this entity points to)
3. Finds all **incoming edges** (entities that point to this entity)
4. Optionally filters by relation type
5. Returns list of (related_entity, relation, direction) tuples

**Parameters**:
- `entity_name`: The entity to find relations for
- `relation_type`: Optional filter (e.g., "can_detect", "uses")

**Returns**:
```python
[
    ('network attacks', 'can_detect', 'outgoing'),
    ('Intrusion Detection', 'uses', 'outgoing'),
    ('packet logger', 'is_part_of', 'incoming')
]
```

**Code Logic**:
```python
def find_related_entities(self, entity_name: str, relation_type: str = None):
    related = []
    
    # Find outgoing edges (entity → other entities)
    for neighbor in self.graph.successors(entity_name):
        for edge_data in self.graph[entity_name][neighbor].values():
            rel = edge_data.get('relation', '')
            if not relation_type or rel == relation_type:
                related.append((neighbor, rel, 'outgoing'))
    
    # Find incoming edges (other entities → entity)
    for neighbor in self.graph.predecessors(entity_name):
        for edge_data in self.graph[neighbor][entity_name].values():
            rel = edge_data.get('relation', '')
            if not relation_type or rel == relation_type:
                related.append((neighbor, rel, 'incoming'))
    
    return related
```

**Examples**:

**Example 1: Find All Related Entities**
```python
# Find all entities related to Snort
related = kg.find_related_entities("Snort")
# Returns: All entities connected to Snort (both directions)
```

**Example 2: Filter by Relation Type**
```python
# Find only entities that Snort can detect
detects = kg.find_related_entities("Snort", relation_type="can_detect")
# Returns: [('network attacks', 'can_detect', 'outgoing')]
```

**Example 3: Find What Uses an Entity**
```python
# Find entities that use Intrusion Detection
users = kg.find_related_entities("Intrusion Detection", relation_type="uses")
# Returns: [('Snort', 'uses', 'incoming'), ('IDS', 'uses', 'incoming')]
```

**Use Cases**:
- Discover what an entity can do (outgoing relations)
- Find what uses/contains an entity (incoming relations)
- Filter by specific relationship types
- Build entity profiles

---

## 3. Entity Search

### Method: `search_entities(query)`

**Purpose**: Search for entities by name (case-insensitive partial match)

**How It Works**:
1. Converts query to lowercase
2. Searches through all entity names
3. Checks if query appears as substring in entity name
4. Returns top 20 matches

**Parameters**:
- `query`: Search string (e.g., "snort", "intrusion")

**Returns**:
```python
['Snort', 'Intrusion Detection', 'network intrusion']
```

**Code Logic**:
```python
def search_entities(self, query: str) -> List[str]:
    query_lower = query.lower()
    matches = []
    
    for entity_name, entity_data in self.entities.items():
        if isinstance(entity_name, str) and query_lower in entity_name.lower():
            if isinstance(entity_data, dict) and 'name' in entity_data:
                matches.append(entity_data['name'])
            else:
                matches.append(entity_name)
    
    return list(set(matches))[:20]  # Return top 20 matches
```

**Examples**:
```python
# Search for entities containing "snort"
results = kg.search_entities("snort")
# Returns: ['Snort', 'Snort rules', ...]

# Search for entities containing "attack"
results = kg.search_entities("attack")
# Returns: ['network attacks', 'attacks', ...]
```

**Use Cases**:
- Find entities when you know part of the name
- Discover similar entities
- Autocomplete functionality
- Entity name disambiguation

---

## 4. Path Finding

### Method: `get_path_between_entities(entity1, entity2, max_length=3)`

**Purpose**: Find paths connecting two entities

**How It Works**:
1. Checks if both entities exist in graph
2. Uses NetworkX `all_simple_paths()` to find all paths
3. Limits path length to `max_length` hops
4. Returns up to 10 paths

**Parameters**:
- `entity1`: Source entity
- `entity2`: Target entity
- `max_length`: Maximum number of hops (default: 3)

**Returns**:
```python
[
    ['Snort', 'Intrusion Detection', 'network attacks'],
    ['Snort', 'can_detect', 'network attacks']
]
```

**Code Logic**:
```python
def get_path_between_entities(self, entity1: str, entity2: str, max_length: int = 3):
    if entity1 not in self.graph or entity2 not in self.graph:
        return []
    
    try:
        paths = list(nx.all_simple_paths(self.graph, entity1, entity2, cutoff=max_length))
        return paths[:10]  # Return top 10 paths
    except:
        return []
```

**Examples**:

**Example 1: Find Direct Connection**
```python
# Find path from Snort to network attacks
paths = kg.get_path_between_entities("Snort", "network attacks", max_length=1)
# Returns: [['Snort', 'network attacks']]  # Direct edge
```

**Example 2: Find Multi-hop Paths**
```python
# Find paths up to 3 hops
paths = kg.get_path_between_entities("Snort", "Attacks", max_length=3)
# Returns: [
#     ['Snort', 'can_detect', 'network attacks', 'Attacks'],
#     ['Snort', 'Intrusion Detection', 'Attacks']
# ]
```

**Use Cases**:
- Discover indirect relationships
- Find how entities are connected
- Multi-hop reasoning
- Relationship chain analysis

---

## 5. Subgraph Extraction

### Method: `get_subgraph(entity_names, depth=2)`

**Purpose**: Extract a focused subgraph around specific entities

**How It Works**:
1. Starts with specified entities
2. Adds neighbors at depth 1, 2, ... up to `depth`
3. Extracts subgraph containing only these nodes and their edges
4. Returns NetworkX subgraph

**Parameters**:
- `entity_names`: List of entity names to center subgraph around
- `depth`: How many hops to include neighbors (default: 2)

**Returns**:
```python
# NetworkX MultiDiGraph containing only relevant nodes and edges
subgraph = kg.get_subgraph(["Snort", "Intrusion Detection"], depth=2)
```

**Code Logic**:
```python
def get_subgraph(self, entity_names: List[str], depth: int = 2):
    nodes_to_include = set(entity_names)
    
    # Add neighbors up to specified depth
    for entity in entity_names:
        if entity in self.graph:
            for d in range(1, depth + 1):
                neighbors = list(self.graph.successors(entity)) + list(self.graph.predecessors(entity))
                nodes_to_include.update(neighbors)
    
    return self.graph.subgraph(list(nodes_to_include))
```

**Examples**:
```python
# Get subgraph around Snort (includes neighbors up to 2 hops away)
subgraph = kg.get_subgraph(["Snort"], depth=2)
# Contains: Snort, its direct neighbors, and their neighbors

# Get subgraph around multiple entities
subgraph = kg.get_subgraph(["Snort", "Nmap"], depth=1)
# Contains: Both entities and their direct neighbors
```

**Use Cases**:
- Focus on specific domain areas
- Visualize entity neighborhoods
- Reduce graph complexity for analysis
- Extract context around entities

---

## 6. Question Answering (High-Level Query)

### Method: `query_knowledge_graph(question)` (in QueryEngine)

**Purpose**: Answer natural language questions using the knowledge graph

**How It Works**:
1. **Extract Key Terms**: Finds entity names mentioned in question
2. **Score Entities**: Ranks entities by relevance to question
3. **Extract Relations**: Identifies relationship types asked about
4. **Query Graph**: Retrieves relevant triples and paths
5. **Generate Answer**: Synthesizes answer from retrieved information

**Parameters**:
- `question`: Natural language question string

**Returns**:
```python
{
    'entities': [
        {
            'name': 'Snort',
            'info': {...},
            'related': [...]
        }
    ],
    'relations': ['can_detect'],
    'paths': [...],
    'subgraph_triples': [
        ('Snort', 'can_detect', 'network attacks'),
        ...
    ]
}
```

**Example**:
```python
query_engine = QueryEngine(kg_builder)
kg_info = query_engine.query_knowledge_graph("What can Snort detect?")
```

**Use Cases**:
- Answer CISSP exam questions
- Natural language queries
- Information retrieval
- Knowledge exploration

---

## Complete Query Workflow Example

### Scenario: "What tools can detect network intrusions?"

**Step 1: Search for Relevant Entities**
```python
# Search for "tool" entities
tools = kg.search_entities("tool")
# Returns: ['Snort', 'Nmap', 'IDS', ...]

# Search for "intrusion" entities
intrusions = kg.search_entities("intrusion")
# Returns: ['Intrusion Detection', 'network intrusions', ...]
```

**Step 2: Find Entities with "can_detect" Relation**
```python
# For each tool, find what it can detect
for tool in tools:
    detects = kg.find_related_entities(tool, relation_type="can_detect")
    if detects:
        print(f"{tool} can detect: {detects}")
```

**Step 3: Check for Intrusion-Related Entities**
```python
# Check if detected entities are intrusion-related
for tool in tools:
    detects = kg.find_related_entities(tool, relation_type="can_detect")
    for entity, relation, direction in detects:
        if "intrusion" in entity.lower():
            print(f"{tool} can detect {entity}")
```

**Step 4: Get Entity Information**
```python
# Get detailed info about matching tools
for tool in matching_tools:
    info = kg.get_entity_info(tool)
    print(f"{tool}: {info['type']}, {info['category']}")
```

**Step 5: Find Paths (if needed)**
```python
# Find how tools connect to intrusions
for tool in tools:
    paths = kg.get_path_between_entities(tool, "network intrusions", max_length=2)
    if paths:
        print(f"Path from {tool} to network intrusions: {paths[0]}")
```

---

## Query Patterns

### Pattern 1: "What can X do?"

**Query Strategy**:
```python
# Find outgoing relations from X
capabilities = kg.find_related_entities("X")
# Filter for action relations (can_detect, can_analyze, etc.)
actions = [r for r in capabilities if r[1].startswith('can_')]
```

### Pattern 2: "What uses X?"

**Query Strategy**:
```python
# Find incoming "uses" relations
users = kg.find_related_entities("X", relation_type="uses")
# Filter for incoming direction
incoming_users = [r for r in users if r[2] == 'incoming']
```

### Pattern 3: "How are X and Y related?"

**Query Strategy**:
```python
# Find paths between X and Y
paths = kg.get_path_between_entities("X", "Y", max_length=3)
# Analyze paths to understand relationship
```

### Pattern 4: "What is X?"

**Query Strategy**:
```python
# Get entity metadata
info = kg.get_entity_info("X")
# Get related entities
related = kg.find_related_entities("X")
# Combine information
```

---

## Graph Traversal Methods

### NetworkX Methods Used

The knowledge graph uses NetworkX's built-in graph traversal methods:

1. **`graph.successors(node)`**: Get nodes this node points to
2. **`graph.predecessors(node)`**: Get nodes that point to this node
3. **`graph.neighbors(node)`**: Get all adjacent nodes
4. **`nx.all_simple_paths(graph, source, target, cutoff)`**: Find all paths
5. **`graph.subgraph(nodes)`**: Extract subgraph

**Example**:
```python
# Direct graph access
successors = list(kg.graph.successors("Snort"))
# Returns: ['network attacks', 'Intrusion Detection', ...]

predecessors = list(kg.graph.predecessors("Snort"))
# Returns: ['packet logger', ...]
```

---

## Query Performance Considerations

### Efficient Queries

1. **Use Relation Filtering**: Filter by relation type to reduce results
   ```python
   # Efficient: Filtered query
   detects = kg.find_related_entities("Snort", relation_type="can_detect")
   
   # Less efficient: Get all then filter
   all_related = kg.find_related_entities("Snort")
   detects = [r for r in all_related if r[1] == "can_detect"]
   ```

2. **Limit Path Length**: Shorter paths are faster
   ```python
   # Efficient: Limit to 2 hops
   paths = kg.get_path_between_entities("A", "B", max_length=2)
   ```

3. **Use Subgraphs**: Extract subgraph for repeated queries
   ```python
   # Extract once, query multiple times
   subgraph = kg.get_subgraph(["Snort"], depth=2)
   # Then query subgraph directly
   ```

### Inefficient Patterns

1. **Searching All Entities**: Use specific queries when possible
2. **Very Long Paths**: Limit max_length appropriately
3. **Large Subgraphs**: Use smaller depth values

---

## Integration with Query Engine

The query engine uses these methods together:

```python
def query_knowledge_graph(self, question: str):
    # 1. Find relevant entities
    relevant_entities = self.find_relevant_entities(question)
    
    # 2. Get top entities
    top_entities = [e[0] for e in relevant_entities[:5]]
    
    # 3. For each entity, get info and related entities
    for entity in top_entities:
        entity_info = self.kg.get_entity_info(entity)
        related = self.kg.find_related_entities(entity)
        
        # 4. Get triples involving this entity
        for e1, r, e2 in self.kg.triples:
            if entity.lower() in e1.lower() or entity.lower() in e2.lower():
                # Collect relevant triples
                ...
    
    # 5. Find paths between entities
    if len(top_entities) >= 2:
        paths = self.kg.get_path_between_entities(
            top_entities[0], 
            top_entities[1], 
            max_length=3
        )
```

---

## Practical Examples

### Example 1: Find All Tools

```python
# Search for tool entities
tools = kg.search_entities("tool")

# Get details for each
for tool in tools:
    info = kg.get_entity_info(tool)
    if info.get('type') == 'tool' or info.get('category') == 'security tool':
        print(f"Tool: {tool}")
        print(f"  Type: {info.get('type')}")
        print(f"  Category: {info.get('category')}")
```

### Example 2: Build Entity Profile

```python
def build_entity_profile(entity_name):
    profile = {
        'name': entity_name,
        'info': kg.get_entity_info(entity_name),
        'outgoing': [],
        'incoming': []
    }
    
    related = kg.find_related_entities(entity_name)
    for entity, relation, direction in related:
        if direction == 'outgoing':
            profile['outgoing'].append((entity, relation))
        else:
            profile['incoming'].append((entity, relation))
    
    return profile

# Usage
snort_profile = build_entity_profile("Snort")
```

### Example 3: Find Common Connections

```python
def find_common_connections(entity1, entity2):
    # Get related entities for both
    related1 = set([r[0] for r in kg.find_related_entities(entity1)])
    related2 = set([r[0] for r in kg.find_related_entities(entity2)])
    
    # Find common entities
    common = related1 & related2
    return list(common)

# Usage
common = find_common_connections("Snort", "Nmap")
```

---

## Summary

Knowledge graph querying enables:

✅ **Entity Lookup**: Find entities by name or search  
✅ **Relationship Discovery**: Find what entities are connected  
✅ **Path Analysis**: Understand how entities relate  
✅ **Subgraph Extraction**: Focus on specific areas  
✅ **Natural Language Queries**: Answer questions in plain English  

All queries work together to provide comprehensive knowledge retrieval from the cybersecurity knowledge graph!
