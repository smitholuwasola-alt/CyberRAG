"""
Answer EB Ultimate Guide Questions using Knowledge Graph
Uses the new knowledge graph to answer questions from the EB Ultimate Guide PDF
"""

import json
import csv
from pathlib import Path
from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

def load_eb_questions() -> list:
    """Load questions from EB Ultimate Guide"""
    json_file = PROJECT_ROOT / "data" / "qa" / "eb_ultimate_guide_questions.json"
    
    if not json_file.exists():
        print(f"Error: Questions file not found at {json_file}")
        return []
    
    with open(json_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    return questions

def answer_questions_with_kg(questions: list, limit: int = None) -> list:
    """Answer questions using knowledge graph"""
    
    print("="*70)
    print("Loading Knowledge Graph from knowledge_graph folder...")
    print("="*70)
    
    # Load or build knowledge graph (now uses knowledge_graph folder by default)
    kg_builder = KnowledgeGraphBuilder()
    kg_file = PROJECT_ROOT / "data" / "knowledge_graph.pkl"
    
    if kg_file.exists():
        print("Loading existing knowledge graph...")
        kg_builder.load_graph(str(kg_file))
    else:
        print("Building knowledge graph from knowledge_graph folder...")
        kg_builder.build_graph()
        kg_builder.save_graph(str(kg_file))
        kg_builder.export_to_json(str(PROJECT_ROOT / "data" / "knowledge_graph.json"))
    
    print(f"Knowledge graph loaded: {kg_builder.graph.number_of_nodes()} nodes, "
          f"{kg_builder.graph.number_of_edges()} edges")
    
    # Initialize query engine
    print("\nInitializing query engine...")
    query_engine = QueryEngine(kg_builder)
    print("Query engine ready!")
    
    # Answer questions
    print("\n" + "="*70)
    print("Answering EB Ultimate Guide Questions using Knowledge Graph")
    print("="*70)
    
    questions_to_answer = questions[:limit] if limit else questions
    print(f"Processing {len(questions_to_answer)} questions...\n")
    
    results = []
    for i, question_data in enumerate(questions_to_answer, 1):
        if i % 10 == 0:
            print(f"Processed {i}/{len(questions_to_answer)} questions...")
        
        try:
            # Format question for query engine
            q_dict = {
                'question': question_data.get('question', ''),
                'options': question_data.get('options', [])
            }
            
            result = query_engine.answer_question(q_dict)
            results.append(result)
        except Exception as e:
            print(f"Error answering question {i}: {e}")
            results.append({
                'question': question_data.get('question', ''),
                'answer': f"Error: {str(e)}",
                'predicted_option': None,
                'confidence': 0.0,
                'supporting_evidence': [],
                'options': question_data.get('options', [])
            })
    
    return results

def save_results(results: list):
    """Save answer results to files"""
    output_dir = PROJECT_ROOT / "data" / "qa"
    
    # Save JSON
    json_file = output_dir / "eb_ultimate_guide_answers.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Saved answers to {json_file}")
    
    # Save CSV
    csv_file = output_dir / "eb_ultimate_guide_answers.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ['question', 'answer', 'predicted_option', 'confidence', 'supporting_evidence', 'options']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {
                    'question': r.get('question', ''),
                    'answer': r.get('answer', ''),
                    'predicted_option': r.get('predicted_option', ''),
                    'confidence': r.get('confidence', 0.0),
                    'supporting_evidence': ' | '.join(r.get('supporting_evidence', [])),
                    'options': ' | '.join(r.get('options', []))
                }
                writer.writerow(row)
    print(f"[OK] Saved answers to {csv_file}")

def print_summary(results: list):
    """Print summary of results"""
    total = len(results)
    with_answers = sum(1 for r in results if r.get('answer') and r.get('answer') != '')
    avg_confidence = sum(r.get('confidence', 0) for r in results) / total if total > 0 else 0
    
    print("\n" + "="*70)
    print("ANSWERING SUMMARY")
    print("="*70)
    print(f"Total questions: {total}")
    print(f"Questions with answers: {with_answers}")
    print(f"Average confidence: {avg_confidence:.2f}")
    print(f"Questions with predictions: {sum(1 for r in results if r.get('predicted_option'))}")

def show_sample_results(results: list, num_samples: int = 5):
    """Show sample results"""
    # Sort by confidence
    sorted_results = sorted(results, key=lambda x: x.get('confidence', 0), reverse=True)
    
    print("\n" + "="*70)
    print(f"SAMPLE RESULTS (top {num_samples} by confidence):")
    print("="*70)
    
    for i, result in enumerate(sorted_results[:num_samples], 1):
        print(f"\n{i}. Question: {result.get('question', '')[:80]}...")
        print(f"   Answer: {result.get('answer', '')[:150]}...")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        if result.get('supporting_evidence'):
            print(f"   Evidence: {result.get('supporting_evidence')[0][:80]}...")

def main():
    print("="*70)
    print("EB Ultimate Guide Question Answering using Knowledge Graph")
    print("="*70)
    
    # Load questions
    print("\nLoading questions from EB Ultimate Guide...")
    questions = load_eb_questions()
    
    if not questions:
        print("No questions found!")
        return
    
    print(f"Loaded {len(questions)} questions")
    
    # Ask for limit
    try:
        limit_input = input(f"\nHow many questions to answer? (default: all {len(questions)}, or enter number): ").strip()
        limit = int(limit_input) if limit_input else None
    except:
        limit = None
    
    if limit:
        print(f"Answering first {limit} questions...")
    else:
        print("Answering all questions...")
    
    # Answer questions
    results = answer_questions_with_kg(questions, limit=limit)
    
    # Save results
    save_results(results)
    
    # Print summary
    print_summary(results)
    
    # Show samples
    show_sample_results(results, num_samples=5)
    
    print("\n" + "="*70)
    print("Process complete!")
    print("="*70)
    print(f"\nResults saved to:")
    print(f"  - {PROJECT_ROOT / 'data' / 'qa' / 'eb_ultimate_guide_answers.json'}")
    print(f"  - {PROJECT_ROOT / 'data' / 'qa' / 'eb_ultimate_guide_answers.csv'}")

if __name__ == "__main__":
    main()
