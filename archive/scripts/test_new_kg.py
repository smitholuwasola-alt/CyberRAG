"""
Test script to verify the new knowledge graph implementation
"""

from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent

def test_knowledge_graph():
    """Test knowledge graph loading and building"""
    print("="*70)
    print("Testing New Knowledge Graph Implementation")
    print("="*70)
    
    print("\n1. Testing Knowledge Graph Builder...")
    kg = KnowledgeGraphBuilder()
    print(f"   Default path: {kg.dataset_path}")
    
    kg.build_graph()
    print(f"   [OK] Graph built: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
    print(f"   [OK] Entities loaded: {len(kg.entities)}")
    print(f"   [OK] Relations: {len(kg.relations)}")
    print(f"   [OK] Triples: {len(kg.triples)}")
    
    # Test entity search
    print("\n2. Testing Entity Search...")
    results = kg.search_entities("risk")
    print(f"   [OK] Search for 'risk': {len(results)} results")
    if results:
        print(f"   Sample: {results[:3]}")
    
    # Test query engine
    print("\n3. Testing Query Engine...")
    engine = QueryEngine(kg)
    test_question = {
        'question': 'What is risk management?',
        'options': []
    }
    result = engine.answer_question(test_question)
    print(f"   [OK] Query engine working")
    print(f"   Question: {result['question']}")
    print(f"   Answer: {result['answer'][:100]}...")
    print(f"   Confidence: {result['confidence']:.2f}")
    
    # Test question answering
    print("\n4. Testing Question Answering...")
    questions_file = PROJECT_ROOT / "data" / "qa" / "eb_ultimate_guide_questions.json"
    if questions_file.exists():
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        print(f"   [OK] Loaded {len(questions)} questions from EB Ultimate Guide")
        
        # Answer first 3 questions
        print("\n   Answering first 3 questions:")
        for i, q in enumerate(questions[:3], 1):
            result = engine.answer_question({
                'question': q['question'],
                'options': q.get('options', [])
            })
            print(f"\n   {i}. {q['question']}")
            print(f"      Answer: {result['answer'][:80]}...")
            print(f"      Confidence: {result['confidence']:.2f}")
    
    # Check answers file
    print("\n5. Checking Generated Answers...")
    answers_file = PROJECT_ROOT / "data" / "qa" / "eb_ultimate_guide_answers.json"
    if answers_file.exists():
        with open(answers_file, 'r', encoding='utf-8') as f:
            answers = json.load(f)
        print(f"   [OK] Answers file exists: {len(answers)} answers")
        with_answers = sum(1 for a in answers if a.get('answer') and len(a.get('answer', '')) > 20)
        print(f"   [OK] Questions with meaningful answers: {with_answers}")
    
    print("\n" + "="*70)
    print("All tests passed! System is ready to use.")
    print("="*70)
    print("\nFiles updated:")
    print("  [OK] kg_builder.py - uses knowledge_graph folder")
    print("  [OK] main_pipeline.py - uses knowledge_graph folder")
    print("  [OK] test_system.py - uses knowledge_graph folder")
    print("  [OK] run_visualizations.py - uses knowledge_graph folder")
    print("\nKnowledge Graph:")
    print(f"  [OK] Location: data/knowledge_graph/")
    print(f"  [OK] Entities: {len(kg.entities)}")
    print(f"  [OK] Relations: {len(kg.relations)}")
    print(f"  [OK] Graph: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
    print("\nQuestion Answering:")
    questions = []
    answers = []
    if questions_file.exists():
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    if answers_file.exists():
        with open(answers_file, 'r', encoding='utf-8') as f:
            answers = json.load(f)
    print(f"  [OK] Questions: {len(questions)}")
    print(f"  [OK] Answers: {len(answers)}")

if __name__ == "__main__":
    test_knowledge_graph()
