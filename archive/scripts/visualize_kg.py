"""
Knowledge Graph Visualization
Creates visual representations of the AISecKG knowledge graph
"""

import matplotlib.pyplot as plt
import networkx as nx
from kg_builder import KnowledgeGraphBuilder
import numpy as np
from collections import Counter
import os
from typing import List
from pathlib import Path

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

class KGVisualizer:
    def __init__(self, kg_builder: KnowledgeGraphBuilder):
        self.kg = kg_builder
        self.graph = kg_builder.graph
        
    def visualize_subgraph(self, entity_names: List[str], depth: int = 1, 
                          figsize=(16, 12), save_path=None):
        """Visualize a subgraph around specific entities"""
        # Get subgraph
        subgraph = self.kg.get_subgraph(entity_names, depth=depth)
        
        if subgraph.number_of_nodes() == 0:
            print(f"No subgraph found for entities: {entity_names}")
            return
        
        # Create figure
        plt.figure(figsize=figsize)
        
        # Use spring layout for better visualization
        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
        
        # Color nodes by entity type if available
        node_colors = []
        for node in subgraph.nodes():
            entity_info = self.kg.get_entity_info(node)
            if isinstance(entity_info, dict):
                entity_type = entity_info.get('type', 'unknown')
                # Color mapping
                color_map = {
                    'tool': '#FF6B6B',      # Red
                    'attack': '#4ECDC4',     # Teal
                    'feature': '#95E1D3',    # Light teal
                    'data': '#F38181',       # Pink
                    'technique': '#AA96DA',  # Purple
                    'system': '#FCBAD3',     # Light pink
                    'app': '#A8DADC',        # Light blue
                    'function': '#FFD93D',   # Yellow
                    'vulnerability': '#FF6B9D', # Dark pink
                }
                node_colors.append(color_map.get(entity_type, '#CCCCCC'))
            else:
                node_colors.append('#CCCCCC')
        
        # Draw nodes
        nx.draw_networkx_nodes(subgraph, pos, 
                              node_color=node_colors,
                              node_size=2000,
                              alpha=0.9)
        
        # Draw edges with different colors for different relations
        edge_colors = []
        for u, v, data in subgraph.edges(data=True):
            relation = data.get('relation', '')
            relation_colors = {
                'uses': '#3498db',
                'has_a': '#2ecc71',
                'can_analyze': '#e74c3c',
                'can_detect': '#f39c12',
                'is_part_of': '#9b59b6',
                'can_exploit': '#e67e22',
                'implements': '#1abc9c',
                'can_harm': '#c0392b',
            }
            edge_colors.append(relation_colors.get(relation, '#95a5a6'))
        
        nx.draw_networkx_edges(subgraph, pos,
                              edge_color=edge_colors,
                              width=2,
                              alpha=0.6,
                              arrows=True,
                              arrowsize=20,
                              arrowstyle='->')
        
        # Draw labels
        labels = {node: node[:20] + '...' if len(node) > 20 else node 
                 for node in subgraph.nodes()}
        nx.draw_networkx_labels(subgraph, pos, labels, 
                               font_size=8, font_weight='bold')
        
        # Add title
        title = f"Knowledge Graph Subgraph: {', '.join(entity_names[:3])}"
        if len(entity_names) > 3:
            title += f" (+{len(entity_names)-3} more)"
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Add legend for node types
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#FF6B6B', label='Tool'),
            Patch(facecolor='#4ECDC4', label='Attack'),
            Patch(facecolor='#95E1D3', label='Feature'),
            Patch(facecolor='#F38181', label='Data'),
            Patch(facecolor='#AA96DA', label='Technique'),
            Patch(facecolor='#CCCCCC', label='Other'),
        ]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
        
        plt.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to {save_path}")
        else:
            plt.show()
    
    def visualize_statistics(self, save_path=None):
        """Create statistical visualizations of the knowledge graph"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Entity types distribution
        entity_types = []
        for entity_name, entity_data in self.kg.entities.items():
            if isinstance(entity_data, dict) and 'type' in entity_data:
                entity_types.append(entity_data['type'])
        
        type_counts = Counter(entity_types)
        axes[0, 0].barh(list(type_counts.keys()), list(type_counts.values()))
        axes[0, 0].set_title('Entity Types Distribution', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Count')
        axes[0, 0].grid(axis='x', alpha=0.3)
        
        # 2. Relation types distribution
        relation_counts = Counter([r for _, r, _ in self.kg.triples])
        axes[0, 1].barh(list(relation_counts.keys()), list(relation_counts.values()))
        axes[0, 1].set_title('Relation Types Distribution', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Count')
        axes[0, 1].grid(axis='x', alpha=0.3)
        
        # 3. Degree distribution
        degrees = [self.graph.degree(node) for node in self.graph.nodes()]
        axes[1, 0].hist(degrees, bins=30, edgecolor='black', alpha=0.7)
        axes[1, 0].set_title('Node Degree Distribution', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Degree (Number of Connections)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].grid(alpha=0.3)
        
        # 4. Top connected entities
        node_degrees = [(node, self.graph.degree(node)) 
                       for node in self.graph.nodes()]
        node_degrees.sort(key=lambda x: x[1], reverse=True)
        top_nodes = node_degrees[:15]
        
        top_names = [name[:15] + '...' if len(name) > 15 else name 
                    for name, _ in top_nodes]
        top_degrees = [deg for _, deg in top_nodes]
        
        axes[1, 1].barh(top_names, top_degrees)
        axes[1, 1].set_title('Top 15 Most Connected Entities', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Number of Connections')
        axes[1, 1].grid(axis='x', alpha=0.3)
        
        plt.suptitle('AISecKG Knowledge Graph Statistics', 
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Statistics saved to {save_path}")
        else:
            plt.show()
    
    def visualize_full_graph_overview(self, max_nodes=100, save_path=None):
        """Visualize an overview of the full graph (sampled if too large)"""
        if self.graph.number_of_nodes() > max_nodes:
            # Sample nodes with highest degree
            node_degrees = [(node, self.graph.degree(node)) 
                           for node in self.graph.nodes()]
            node_degrees.sort(key=lambda x: x[1], reverse=True)
            top_nodes = [node for node, _ in node_degrees[:max_nodes]]
            subgraph = self.graph.subgraph(top_nodes)
        else:
            subgraph = self.graph
        
        plt.figure(figsize=(20, 16))
        
        # Use force-directed layout
        pos = nx.spring_layout(subgraph, k=1, iterations=50, seed=42)
        
        # Draw edges first (so nodes appear on top)
        nx.draw_networkx_edges(subgraph, pos,
                              alpha=0.2,
                              width=0.5,
                              edge_color='gray',
                              arrows=True,
                              arrowsize=10)
        
        # Draw nodes
        node_sizes = [self.graph.degree(node) * 50 + 100 
                     for node in subgraph.nodes()]
        nx.draw_networkx_nodes(subgraph, pos,
                              node_size=node_sizes,
                              node_color='lightblue',
                              alpha=0.7)
        
        # Only label high-degree nodes to avoid clutter
        high_degree_nodes = [node for node in subgraph.nodes() 
                           if self.graph.degree(node) > 5]
        labels = {node: node[:15] for node in high_degree_nodes}
        nx.draw_networkx_labels(subgraph, pos, labels, 
                               font_size=8, font_weight='bold')
        
        title = f"Knowledge Graph Overview ({subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges)"
        if self.graph.number_of_nodes() > max_nodes:
            title += f" (showing top {max_nodes} nodes)"
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Overview saved to {save_path}")
        else:
            plt.show()
    
    def visualize_entity_network(self, entity_name: str, depth: int = 2, 
                                 save_path=None):
        """Visualize network around a specific entity"""
        if entity_name not in self.graph:
            print(f"Entity '{entity_name}' not found in graph")
            return
        
        subgraph = self.kg.get_subgraph([entity_name], depth=depth)
        
        plt.figure(figsize=(14, 10))
        
        # Use hierarchical layout with entity at center
        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
        
        # Highlight the main entity
        main_node_color = '#FF6B6B'
        other_node_colors = '#95E1D3'
        
        node_colors = [main_node_color if node == entity_name else other_node_colors 
                      for node in subgraph.nodes()]
        node_sizes = [3000 if node == entity_name else 1500 
                     for node in subgraph.nodes()]
        
        # Draw edges
        nx.draw_networkx_edges(subgraph, pos,
                              alpha=0.5,
                              width=2,
                              edge_color='gray',
                              arrows=True,
                              arrowsize=15)
        
        # Draw nodes
        nx.draw_networkx_nodes(subgraph, pos,
                              node_color=node_colors,
                              node_size=node_sizes,
                              alpha=0.9)
        
        # Draw labels
        labels = {node: node[:25] + '...' if len(node) > 25 else node 
                 for node in subgraph.nodes()}
        nx.draw_networkx_labels(subgraph, pos, labels, 
                               font_size=9, font_weight='bold')
        
        # Add edge labels for relations
        edge_labels = {}
        for u, v, data in subgraph.edges(data=True):
            relation = data.get('relation', '')
            if relation:
                edge_labels[(u, v)] = relation
        
        nx.draw_networkx_edge_labels(subgraph, pos, edge_labels, 
                                    font_size=7, alpha=0.7)
        
        plt.title(f"Network around '{entity_name}' (depth={depth})", 
                 fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Network visualization saved to {save_path}")
        else:
            plt.show()


def main():
    """Main function to create visualizations"""
    print("Building knowledge graph...")
    kg_builder = KnowledgeGraphBuilder()
    
    # Try to load existing graph, otherwise build it
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
    
    # Create visualizer
    visualizer = KGVisualizer(kg_builder)
    
    # Create output directory
    viz_dir = PROJECT_ROOT / "output" / "visualizations"
    os.makedirs(viz_dir, exist_ok=True)
    
    print("\nGenerating visualizations...")
    
    # 1. Statistics
    print("1. Creating statistics visualization...")
    visualizer.visualize_statistics(str(viz_dir / "kg_statistics.png"))
    
    # 2. Full graph overview
    print("2. Creating full graph overview...")
    visualizer.visualize_full_graph_overview(
        max_nodes=100, 
        save_path=str(viz_dir / "kg_overview.png")
    )
    
    # 3. Entity-specific networks
    print("3. Creating entity-specific networks...")
    important_entities = ["Snort", "Nmap", "Metasploit", "IDS", "Firewall"]
    
    for entity in important_entities:
        if entity in kg_builder.graph:
            print(f"   - Visualizing network for '{entity}'...")
            visualizer.visualize_entity_network(
                entity, 
                depth=2,
                save_path=str(viz_dir / f"network_{entity.lower()}.png")
            )
    
    # 4. Subgraph visualization
    print("4. Creating subgraph visualization...")
    visualizer.visualize_subgraph(
        ["Snort", "Nmap", "IDS"],
        depth=2,
        save_path=str(viz_dir / "subgraph_snort_nmap_ids.png")
    )
    
    print("\n" + "="*60)
    print("All visualizations created successfully!")
    print(f"Check the '{viz_dir}' directory for output files.")
    print("="*60)


if __name__ == "__main__":
    main()
