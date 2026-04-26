"""
Create Interactive HTML Visualization of Knowledge Graph
Uses pyvis for interactive network visualization
"""

import networkx as nx
from kg_builder import KnowledgeGraphBuilder
import os
from pathlib import Path

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    print("pyvis not available. Install with: pip install pyvis")

def create_interactive_visualization(kg_builder: KnowledgeGraphBuilder, 
                                    entity_names=None, 
                                    depth=2,
                                    output_file=None):
    if output_file is None:
        output_file = str(PROJECT_ROOT / "output" / "visualizations" / "kg_interactive.html")
    elif not Path(output_file).is_absolute():
        output_file = str(PROJECT_ROOT / output_file)
    """Create an interactive HTML visualization"""
    
    if not PYVIS_AVAILABLE:
        print("pyvis is required for interactive visualization")
        print("Install with: pip install pyvis")
        return
    
    # Get subgraph or use full graph
    if entity_names:
        graph = kg_builder.get_subgraph(entity_names, depth=depth)
        title = f"Knowledge Graph: {', '.join(entity_names)}"
    else:
        # Use top connected nodes if graph is too large
        if kg_builder.graph.number_of_nodes() > 200:
            node_degrees = [(node, kg_builder.graph.degree(node)) 
                           for node in kg_builder.graph.nodes()]
            node_degrees.sort(key=lambda x: x[1], reverse=True)
            top_nodes = [node for node, _ in node_degrees[:200]]
            graph = kg_builder.graph.subgraph(top_nodes)
            title = "Knowledge Graph Overview (Top 200 Nodes)"
        else:
            graph = kg_builder.graph
            title = "Complete Knowledge Graph"
    
    # Create pyvis network
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
    net.set_options("""
    {
      "nodes": {
        "font": {
          "size": 14,
          "face": "Arial"
        },
        "scaling": {
          "min": 10,
          "max": 50
        }
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 1.2
          }
        },
        "smooth": {
          "type": "continuous"
        }
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.1,
          "springLength": 200,
          "springConstant": 0.04
        },
        "minVelocity": 0.75
      }
    }
    """)
    
    # Add nodes with colors based on entity type
    color_map = {
        'tool': '#FF6B6B',
        'attack': '#4ECDC4',
        'feature': '#95E1D3',
        'data': '#F38181',
        'technique': '#AA96DA',
        'system': '#FCBAD3',
        'app': '#A8DADC',
        'function': '#FFD93D',
        'vulnerability': '#FF6B9D',
    }
    
    # Calculate node sizes based on degree
    max_degree = max([graph.degree(node) for node in graph.nodes()]) if graph.nodes() else 1
    
    for node in graph.nodes():
        entity_info = kg_builder.get_entity_info(node)
        entity_type = 'unknown'
        if isinstance(entity_info, dict):
            entity_type = entity_info.get('type', 'unknown')
        
        color = color_map.get(entity_type, '#CCCCCC')
        degree = graph.degree(node)
        size = 20 + (degree / max_degree) * 30
        
        # Create title with entity information
        title_text = f"<b>{node}</b><br>"
        if isinstance(entity_info, dict):
            title_text += f"Type: {entity_info.get('type', 'N/A')}<br>"
            title_text += f"Category: {entity_info.get('category', 'N/A')}<br>"
        title_text += f"Connections: {degree}"
        
        net.add_node(node, 
                    label=node[:30] + '...' if len(node) > 30 else node,
                    color=color,
                    size=size,
                    title=title_text)
    
    # Add edges with relation labels
    for u, v, data in graph.edges(data=True):
        relation = data.get('relation', '')
        net.add_edge(u, v, 
                    title=relation,
                    label=relation[:10] if relation else '',
                    color='#888888')
    
    # Set title
    net.set_options(f'var options = {{"title": "{title}"}}')
    
    # Save
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    net.save_graph(output_file)
    print(f"Interactive visualization saved to {output_file}")
    print(f"Open it in a web browser to explore the graph interactively!")


def main():
    """Create interactive visualizations"""
    print("Building knowledge graph...")
    kg_builder = KnowledgeGraphBuilder()
    
    # Try to load existing graph
    kg_file = PROJECT_ROOT / "data" / "knowledge_graph.pkl"
    if kg_file.exists():
        print("Loading existing knowledge graph...")
        kg_builder.load_graph(str(kg_file))
    else:
        print("Building knowledge graph from dataset...")
        kg_builder.build_graph()
        kg_builder.save_graph(str(kg_file))
    
    print(f"Graph loaded: {kg_builder.graph.number_of_nodes()} nodes, "
          f"{kg_builder.graph.number_of_edges()} edges")
    
    viz_dir = PROJECT_ROOT / "output" / "visualizations"
    os.makedirs(viz_dir, exist_ok=True)
    
    if PYVIS_AVAILABLE:
        print("\nCreating interactive visualizations...")
        
        # 1. Full graph overview
        print("1. Creating full graph overview...")
        create_interactive_visualization(
            kg_builder,
            entity_names=None,
            output_file=str(viz_dir / "kg_interactive_full.html")
        )
        
        # 2. Snort network
        print("2. Creating Snort network...")
        if "Snort" in kg_builder.graph:
            create_interactive_visualization(
                kg_builder,
                entity_names=["Snort"],
                depth=2,
                output_file=str(viz_dir / "kg_interactive_snort.html")
            )
        
        # 3. Nmap network
        print("3. Creating Nmap network...")
        if "Nmap" in kg_builder.graph:
            create_interactive_visualization(
                kg_builder,
                entity_names=["Nmap"],
                depth=2,
                output_file=str(viz_dir / "kg_interactive_nmap.html")
            )
        
        # 4. Multiple entities
        print("4. Creating multi-entity network...")
        create_interactive_visualization(
            kg_builder,
            entity_names=["Snort", "Nmap", "IDS", "Firewall"],
            depth=2,
            output_file=str(viz_dir / "kg_interactive_multi.html")
        )
        
        print("\n" + "="*60)
        print("Interactive visualizations created!")
        print("Open the HTML files in a web browser to explore.")
        print("="*60)
    else:
        print("\nTo create interactive visualizations, install pyvis:")
        print("pip install pyvis")


if __name__ == "__main__":
    main()
