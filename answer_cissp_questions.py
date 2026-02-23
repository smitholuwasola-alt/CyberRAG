"""
Answer CISSP Questions using Knowledge Graph Query Engine
Uses the built knowledge graph to answer scraped CISSP questions
"""

import json
import csv
import os
from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine

def load_questions_from_csv(filename: str = "cissp_questions.csv") -> list:
    """Load questions from CSV file"""
    questions = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question_text = row.get('question', '').strip()
            
            # Skip empty or invalid questions
            if not question_text or len(question_text) < 20:
                continue
            
            # Skip header-like rows
            if question_text.startswith('Topic') or question_text.startswith('Question #') and '?' not in question_text:
                continue
            
            # Only process actual questions (end with ?)
            if question_text.endswith('?'):
                # Parse options if they exist (stored as string in CSV)
                options_str = row.get('options', '')
                options = []
                if options_str and options_str != '[]':
                    # Try to parse options
                    if '|' in options_str:
                        options = [opt.strip() for opt in options_str.split('|') if opt.strip()]
                    elif options_str.startswith('['):
                        try:
                            import ast
                            options = ast.literal_eval(options_str)
                        except:
                            options = []
                
                questions.append({
                    'question': question_text,
                    'options': options if options else [],
                    'correct_answer': row.get('correct_answer', '').strip(),
                    'topic': row.get('topic', '').strip()
                })
    
    return questions

def load_questions_from_json(filename: str = "cissp_questions.json") -> list:
    """Load questions from JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    # Filter valid questions
    valid_questions = []
    for q in questions:
        question_text = q.get('question', '').strip()
        if question_text and len(question_text) > 20 and question_text.endswith('?'):
            # Skip header rows
            if not question_text.startswith('Topic') and not (question_text.startswith('Question #') and len(question_text) < 30):
                valid_questions.append(q)
    
    return valid_questions

def answer_questions_with_kg(questions: list, limit: int = None) -> list:
    """Answer questions using knowledge graph"""
    
    print("="*70)
    print("Loading Knowledge Graph...")
    print("="*70)
    
    # Load or build knowledge graph
    kg_builder = KnowledgeGraphBuilder(dataset_path="dataset")
    
    if os.path.exists("knowledge_graph.pkl"):
        print("Loading existing knowledge graph...")
        kg_builder.load_graph("knowledge_graph.pkl")
    else:
        print("Building knowledge graph from dataset...")
        kg_builder.build_graph()
        kg_builder.save_graph("knowledge_graph.pkl")
    
    print(f"Knowledge graph loaded: {kg_builder.graph.number_of_nodes()} nodes, "
          f"{kg_builder.graph.number_of_edges()} edges")
    
    # Initialize query engine
    print("\nInitializing query engine...")
    query_engine = QueryEngine(kg_builder)
    print("Query engine ready!")
    
    # Answer questions
    print("\n" + "="*70)
    print("Answering Questions using Knowledge Graph")
    print("="*70)
    
    questions_to_answer = questions[:limit] if limit else questions
    print(f"Processing {len(questions_to_answer)} questions...\n")
    
    results = []
    for i, question_data in enumerate(questions_to_answer, 1):
        if i % 10 == 0:
            print(f"Processed {i}/{len(questions_to_answer)} questions...")
        
        try:
            result = query_engine.answer_question(question_data)
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

def save_results(results: list, json_file: str = "cissp_answers.json", 
                 csv_file: str = "cissp_answers.csv"):
    """Save answer results to files"""
    
    # Save JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved answers to {json_file}")
    
    # Save CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            # Flatten results for CSV
            csv_data = []
            for r in results:
                csv_data.append({
                    'question': r.get('question', ''),
                    'answer': r.get('answer', ''),
                    'predicted_option': r.get('predicted_option', ''),
                    'confidence': r.get('confidence', 0.0),
                    'supporting_evidence': ' | '.join(r.get('supporting_evidence', [])),
                    'options': ' | '.join(r.get('options', []))
                })
            
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
    print(f"Saved answers to {csv_file}")

def print_summary(results: list):
    """Print summary statistics"""
    total = len(results)
    with_answers = sum(1 for r in results if r.get('answer') and 'Error' not in str(r.get('answer', '')))
    with_predictions = sum(1 for r in results if r.get('predicted_option'))
    avg_confidence = sum(r.get('confidence', 0) for r in results) / total if total > 0 else 0
    
    print("\n" + "="*70)
    print("ANSWERING SUMMARY")
    print("="*70)
    print(f"Total questions processed: {total}")
    print(f"Questions with answers: {with_answers} ({with_answers/total*100:.1f}%)")
    print(f"Questions with predictions: {with_predictions} ({with_predictions/total*100:.1f}%)")
    print(f"Average confidence: {avg_confidence:.2f}")
    
    # Confidence distribution
    high_conf = sum(1 for r in results if r.get('confidence', 0) > 0.7)
    medium_conf = sum(1 for r in results if 0.3 < r.get('confidence', 0) <= 0.7)
    low_conf = sum(1 for r in results if r.get('confidence', 0) <= 0.3)
    
    print(f"\nConfidence Distribution:")
    print(f"  High (>0.7): {high_conf} ({high_conf/total*100:.1f}%)")
    print(f"  Medium (0.3-0.7): {medium_conf} ({medium_conf/total*100:.1f}%)")
    print(f"  Low (<=0.3): {low_conf} ({low_conf/total*100:.1f}%)")
    print("="*70)

def show_sample_results(results: list, num_samples: int = 5):
    """Show sample question-answer pairs"""
    print("\n" + "="*70)
    print("SAMPLE RESULTS")
    print("="*70)
    
    # Show best confidence results
    sorted_results = sorted(results, key=lambda x: x.get('confidence', 0), reverse=True)
    
    for i, result in enumerate(sorted_results[:num_samples], 1):
        print(f"\n{i}. Question: {result.get('question', '')[:100]}...")
        print(f"   Answer: {result.get('answer', '')[:200]}...")
        print(f"   Predicted Option: {result.get('predicted_option', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        if result.get('supporting_evidence'):
            print(f"   Evidence: {result.get('supporting_evidence')[0][:80]}...")

def main():
    print("="*70)
    print("CISSP Question Answering using Knowledge Graph")
    print("="*70)
    
    # Load questions
    print("\nLoading questions...")
    
    # Try JSON first, then CSV
    questions = []
    if os.path.exists("cissp_questions.json"):
        print("Loading from cissp_questions.json...")
        questions = load_questions_from_json("cissp_questions.json")
    elif os.path.exists("cissp_questions.csv"):
        print("Loading from cissp_questions.csv...")
        questions = load_questions_from_csv("cissp_questions.csv")
    else:
        print("Error: No question files found!")
        print("Please ensure cissp_questions.json or cissp_questions.csv exists")
        return
    
    print(f"Loaded {len(questions)} valid questions")
    
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
    print(f"  - cissp_answers.json")
    print(f"  - cissp_answers.csv")

if __name__ == "__main__":
    main()
