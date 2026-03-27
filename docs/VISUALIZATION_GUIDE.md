# Knowledge Graph Visualization Guide

This guide explains how to create and view visualizations of the AISecKG knowledge graph.

## Quick Start

### Generate All Visualizations

```bash
python run_visualizations.py
```

This will create:
- Static PNG visualizations (matplotlib)
- Interactive HTML visualizations (pyvis)

## Visualization Types

### 1. Static Visualizations (PNG)

Created using matplotlib, saved as PNG images.

#### Statistics Visualization
```python
from visualize_kg import KGVisualizer
from kg_builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

viz = KGVisualizer(kg)
viz.visualize_statistics("visualizations/kg_statistics.png")
```

**Shows:**
- Entity types distribution
- Relation types distribution
- Node degree distribution
- Top connected entities

#### Full Graph Overview
```python
viz.visualize_full_graph_overview(
    max_nodes=100,
    save_path="visualizations/kg_overview.png"
)
```

**Shows:**
- Network layout of the entire graph
- Node sizes based on connectivity
- Only labels high-degree nodes to reduce clutter

#### Entity-Specific Network
```python
viz.visualize_entity_network(
    "Snort",
    depth=2,
    save_path="visualizations/network_snort.png"
)
```

**Shows:**
- Network around a specific entity
- All entities within specified depth
- Edge labels showing relation types
- Highlighted main entity

#### Subgraph Visualization
```python
viz.visualize_subgraph(
    ["Snort", "Nmap", "IDS"],
    depth=2,
    save_path="visualizations/subgraph.png"
)
```

**Shows:**
- Subgraph containing multiple entities
- Color-coded nodes by entity type
- Relation-colored edges
- Legend for node types

### 2. Interactive Visualizations (HTML)

Created using pyvis, saved as HTML files that can be opened in any web browser.

#### Create Interactive Visualization
```python
from create_interactive_viz import create_interactive_visualization
from kg_builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

# Full graph
create_interactive_visualization(
    kg,
    output_file="visualizations/kg_interactive_full.html"
)

# Specific entity
create_interactive_visualization(
    kg,
    entity_names=["Snort"],
    depth=2,
    output_file="visualizations/kg_interactive_snort.html"
)
```

**Features:**
- **Drag nodes** to rearrange
- **Click nodes** to see details
- **Hover over edges** to see relations
- **Zoom and pan** to explore
- **Physics simulation** for automatic layout

## Color Coding

### Node Colors (by Entity Type)
- **Tool** (Red): `#FF6B6B` - e.g., Snort, Nmap
- **Attack** (Teal): `#4ECDC4` - e.g., network attacks
- **Feature** (Light Teal): `#95E1D3` - e.g., features
- **Data** (Pink): `#F38181` - e.g., Packet, Traffic
- **Technique** (Purple): `#AA96DA` - e.g., Intrusion Detection
- **System** (Light Pink): `#FCBAD3` - e.g., systems
- **App** (Light Blue): `#A8DADC` - e.g., applications
- **Function** (Yellow): `#FFD93D` - e.g., functions
- **Vulnerability** (Dark Pink): `#FF6B9D` - e.g., vulnerabilities

### Edge Colors (by Relation Type)
- **uses**: Blue
- **has_a**: Green
- **can_analyze**: Red
- **can_detect**: Orange
- **is_part_of**: Purple
- **can_exploit**: Dark Orange
- **implements**: Teal
- **can_harm**: Dark Red

## Usage Examples

### Example 1: Visualize Snort Network
```python
from visualize_kg import KGVisualizer
from kg_builder import KnowledgeGraphBuilder

# Build graph
kg = KnowledgeGraphBuilder("dataset")
kg.build_graph()

# Create visualizer
viz = KGVisualizer(kg)

# Visualize Snort network
viz.visualize_entity_network(
    "Snort",
    depth=2,
    save_path="visualizations/snort_network.png"
)
```

### Example 2: Compare Multiple Tools
```python
# Visualize subgraph with multiple tools
viz.visualize_subgraph(
    ["Snort", "Nmap", "Metasploit", "Wireshark"],
    depth=2,
    save_path="visualizations/tools_comparison.png"
)
```

### Example 3: Interactive Exploration
```python
from create_interactive_viz import create_interactive_visualization

# Create interactive visualization
create_interactive_visualization(
    kg,
    entity_names=["Snort", "Nmap"],
    depth=2,
    output_file="visualizations/interactive_tools.html"
)

# Open the HTML file in your browser
```

## Output Files

After running visualizations, you'll find:

### Static Images (PNG)
- `visualizations/kg_statistics.png` - Statistics charts
- `visualizations/kg_overview.png` - Full graph overview
- `visualizations/network_*.png` - Entity-specific networks
- `visualizations/subgraph_*.png` - Subgraph visualizations

### Interactive Files (HTML)
- `visualizations/kg_interactive_full.html` - Full graph
- `visualizations/kg_interactive_snort.html` - Snort network
- `visualizations/kg_interactive_nmap.html` - Nmap network
- `visualizations/kg_interactive_multi.html` - Multiple entities

## Tips for Best Results

1. **For Large Graphs**: Use `max_nodes` parameter to limit nodes shown
2. **For Clarity**: Use `depth` parameter to control subgraph size
3. **For Exploration**: Use interactive HTML visualizations
4. **For Analysis**: Use statistics visualizations to understand distribution
5. **For Presentations**: Use static PNG files

## Troubleshooting

### Import Errors
```bash
pip install matplotlib networkx pyvis
```

### Graph Too Large
- Use subgraph visualization instead of full graph
- Reduce `max_nodes` parameter
- Increase `depth` parameter to see more connections

### Visualization Not Showing
- Check that graph was built successfully
- Verify entity names exist in graph
- Check file paths are correct

### Interactive Visualization Not Working
- Ensure pyvis is installed: `pip install pyvis`
- Open HTML file in a modern web browser
- Check browser console for JavaScript errors

## Advanced Customization

### Custom Node Colors
Modify the `color_map` dictionary in `visualize_kg.py`:
```python
color_map = {
    'tool': '#YOUR_COLOR',
    'attack': '#YOUR_COLOR',
    # ... add more
}
```

### Custom Layout
Change layout algorithm in `visualize_kg.py`:
```python
# Spring layout (default)
pos = nx.spring_layout(subgraph, k=2, iterations=50)

# Circular layout
pos = nx.circular_layout(subgraph)

# Hierarchical layout
pos = nx.nx_agraph.graphviz_layout(subgraph, prog='dot')
```

### Custom Edge Styling
Modify edge drawing parameters:
```python
nx.draw_networkx_edges(
    subgraph, pos,
    width=3,  # Thicker edges
    alpha=0.8,  # More opaque
    edge_color='red',  # Custom color
    style='dashed'  # Dashed style
)
```

## Next Steps

- Explore the interactive visualizations
- Analyze statistics to understand graph structure
- Create custom visualizations for specific use cases
- Export graph data for use in other tools (Gephi, Cytoscape, etc.)
