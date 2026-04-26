"""
Test script to verify the system works
"""

import os
import sys
from pathlib import Path

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

def test_kg_builder():
    """Test knowledge graph builder"""
    print("Testing Knowledge Graph Builder...")
    try:
        from kg_builder import KnowledgeGraphBuilder
        
        kg = KnowledgeGraphBuilder()
        kg.build_graph()
        
        print(f"✓ Graph built: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
        
        # Test search
        results = kg.search_entities("Snort")
        print(f"✓ Search for 'Snort': {results[:3]}")
        
        # Test relations
        if "Snort" in kg.graph:
            related = kg.find_related_entities("Snort")
            print(f"✓ Relations for 'Snort': {len(related)} found")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_engine():
    """Test query engine"""
    print("\nTesting Query Engine...")
    try:
        from kg_builder import KnowledgeGraphBuilder
        from query_engine import QueryEngine
        
        # Build or load KG
        kg = KnowledgeGraphBuilder()
        kg_file = PROJECT_ROOT / "data" / "knowledge_graph.pkl"
        if kg_file.exists():
            kg.load_graph(str(kg_file))
        else:
            kg.build_graph()
        
        engine = QueryEngine(kg)
        
        # Test question
        question = {
            'question': 'What is Snort used for?',
            'options': ['A. Network scanning', 'B. Intrusion Detection', 'C. Firewall', 'D. Encryption']
        }
        
        result = engine.answer_question(question)
        print(f"✓ Question answered: {result['question'][:50]}...")
        print(f"✓ Confidence: {result['confidence']:.2f}")
        print(f"✓ Predicted option: {result.get('predicted_option', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("AISecKG System Test")
    print("=" * 60)
    
    # Check if knowledge graph exists
    dataset_dir = PROJECT_ROOT / "data" / "knowledge_graph"
    if not dataset_dir.exists():
        print("✗ Knowledge graph directory not found!")
        print(f"Expected at: {dataset_dir}")
        return
    
    # Run tests
    test1 = test_kg_builder()
    test2 = test_query_engine()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)

if __name__ == "__main__":
    main()
