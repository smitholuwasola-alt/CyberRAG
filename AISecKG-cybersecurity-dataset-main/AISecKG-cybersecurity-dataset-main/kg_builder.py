"""
Knowledge Graph Builder
Builds a graph structure from the AISecKG dataset
"""

import pandas as pd
import networkx as nx
import json
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import pickle

class KnowledgeGraphBuilder:
    def __init__(self, dataset_path: str = "dataset"):
        self.dataset_path = dataset_path
        self.graph = nx.MultiDiGraph()  # MultiDiGraph to support multiple relations between same nodes
        self.entities = {}
        self.relations = set()
        self.triples = []
        
    def load_entities(self):
        """Load entity information from CSV"""
        try:
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
            print(f"Loaded {len(df)} entities")
        except Exception as e:
            print(f"Error loading entities: {e}")
    
    def load_relations(self):
        """Load relation types from CSV"""
        try:
            df = pd.read_csv(f"{self.dataset_path}/all_relation_info.csv")
            self.relations = set(df['relation'].tolist())
            print(f"Loaded {len(self.relations)} relation types")
        except Exception as e:
            print(f"Error loading relations: {e}")
    
    def load_triples(self):
        """Load triples and build graph"""
        try:
            df = pd.read_csv(f"{self.dataset_path}/all_triples.csv")
            
            for _, row in df.iterrows():
                e1 = str(row['e1']).strip()
                r = str(row['r']).strip()
                e2 = str(row['e2']).strip()
                
                if e1 and r and e2:
                    self.triples.append((e1, r, e2))
                    
                    # Add nodes to graph
                    if not self.graph.has_node(e1):
                        self.graph.add_node(e1, label=e1)
                    if not self.graph.has_node(e2):
                        self.graph.add_node(e2, label=e2)
                    
                    # Add edge with relation as attribute
                    self.graph.add_edge(e1, e2, relation=r, label=r)
            
            print(f"Loaded {len(self.triples)} triples")
            print(f"Graph has {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        except Exception as e:
            print(f"Error loading triples: {e}")
    
    def build_graph(self):
        """Build the complete knowledge graph"""
        print("Building knowledge graph...")
        self.load_entities()
        self.load_relations()
        self.load_triples()
        print("Knowledge graph built successfully!")
    
    def get_entity_info(self, entity_name: str) -> Dict:
        """Get information about an entity"""
        return self.entities.get(entity_name, {})
    
    def find_related_entities(self, entity_name: str, relation_type: str = None) -> List[Tuple]:
        """Find entities related to a given entity"""
        related = []
        
        if entity_name not in self.graph:
            return related
        
        # Find outgoing edges
        for neighbor in self.graph.successors(entity_name):
            for edge_data in self.graph[entity_name][neighbor].values():
                rel = edge_data.get('relation', '')
                if not relation_type or rel == relation_type:
                    related.append((neighbor, rel, 'outgoing'))
        
        # Find incoming edges
        for neighbor in self.graph.predecessors(entity_name):
            for edge_data in self.graph[neighbor][entity_name].values():
                rel = edge_data.get('relation', '')
                if not relation_type or rel == relation_type:
                    related.append((neighbor, rel, 'incoming'))
        
        return related
    
    def search_entities(self, query: str) -> List[str]:
        """Search for entities by name (case-insensitive partial match)"""
        query_lower = query.lower()
        matches = []
        
        for entity_name, entity_data in self.entities.items():
            if isinstance(entity_name, str) and query_lower in entity_name.lower():
                if isinstance(entity_data, dict) and 'name' in entity_data:
                    matches.append(entity_data['name'])
                else:
                    matches.append(entity_name)
        
        return list(set(matches))[:20]  # Return top 20 matches
    
    def get_path_between_entities(self, entity1: str, entity2: str, max_length: int = 3) -> List[List[str]]:
        """Find paths between two entities"""
        if entity1 not in self.graph or entity2 not in self.graph:
            return []
        
        try:
            paths = list(nx.all_simple_paths(self.graph, entity1, entity2, cutoff=max_length))
            return paths[:10]  # Return top 10 paths
        except:
            return []
    
    def get_subgraph(self, entity_names: List[str], depth: int = 2) -> nx.MultiDiGraph:
        """Get a subgraph around specific entities"""
        nodes_to_include = set(entity_names)
        
        # Add neighbors up to specified depth
        for entity in entity_names:
            if entity in self.graph:
                # Add nodes at different depths
                for d in range(1, depth + 1):
                    neighbors = list(self.graph.successors(entity)) + list(self.graph.predecessors(entity))
                    nodes_to_include.update(neighbors)
        
        return self.graph.subgraph(list(nodes_to_include))
    
    def save_graph(self, filename: str = "knowledge_graph.pkl"):
        """Save graph to pickle file"""
        with open(filename, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'entities': self.entities,
                'relations': list(self.relations),
                'triples': self.triples
            }, f)
        print(f"Graph saved to {filename}")
    
    def load_graph(self, filename: str = "knowledge_graph.pkl"):
        """Load graph from pickle file"""
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                self.graph = data['graph']
                self.entities = data['entities']
                self.relations = set(data['relations'])
                self.triples = data['triples']
            print(f"Graph loaded from {filename}")
        except Exception as e:
            print(f"Error loading graph: {e}")
    
    def export_to_json(self, filename: str = "knowledge_graph.json"):
        """Export graph to JSON format"""
        graph_data = {
            'nodes': [],
            'edges': [],
            'entities': self.entities,
            'relations': list(self.relations)
        }
        
        # Add nodes
        for node in self.graph.nodes():
            graph_data['nodes'].append({
                'id': node,
                'label': node
            })
        
        # Add edges
        for u, v, data in self.graph.edges(data=True):
            graph_data['edges'].append({
                'source': u,
                'target': v,
                'relation': data.get('relation', '')
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        print(f"Graph exported to {filename}")


def main():
    kg_builder = KnowledgeGraphBuilder(dataset_path="dataset")
    kg_builder.build_graph()
    kg_builder.save_graph("knowledge_graph.pkl")
    kg_builder.export_to_json("knowledge_graph.json")
    
    # Example queries
    print("\n=== Example Queries ===")
    print(f"\nSearch for 'Snort': {kg_builder.search_entities('Snort')}")
    print(f"\nEntities related to 'Snort': {kg_builder.find_related_entities('Snort')[:5]}")


if __name__ == "__main__":
    main()
