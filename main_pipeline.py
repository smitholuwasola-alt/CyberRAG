"""
Main Pipeline: Scrape CISSP Questions, Build KG, and Answer Questions
Complete workflow for the question-answering system
"""

import os
import sys
import json
from pathlib import Path
from kg_builder import KnowledgeGraphBuilder
from query_engine import QueryEngine
from scraper.cissp_scraper import CISSPScraper

class MainPipeline:
    def __init__(self, dataset_path: str = "dataset"):
        self.dataset_path = dataset_path
        self.kg_builder = None
        self.query_engine = None
        self.questions = []
    
    def step1_scrape_questions(self, max_pages: int = 50, force: bool = False):
        """Step 1: Scrape CISSP questions from website"""
        questions_file = "cissp_questions.json"
        
        if os.path.exists(questions_file) and not force:
            print(f"Loading existing questions from {questions_file}...")
            with open(questions_file, 'r', encoding='utf-8') as f:
                self.questions = json.load(f)
            print(f"Loaded {len(self.questions)} questions")
        else:
            print("Scraping CISSP questions from website...")
            scraper = CISSPScraper()
            self.questions = scraper.scrape_all_pages(max_pages=max_pages)
            
            if self.questions:
                scraper.save_to_json(self.questions, questions_file)
                print(f"Scraped {len(self.questions)} questions")
            else:
                print("Warning: No questions scraped. Using sample questions.")
                self.questions = self._get_sample_questions()
    
    def step2_build_knowledge_graph(self, force_rebuild: bool = False):
        """Step 2: Build knowledge graph from dataset"""
        kg_file = "knowledge_graph.pkl"
        
        if os.path.exists(kg_file) and not force_rebuild:
            print(f"Loading existing knowledge graph from {kg_file}...")
            self.kg_builder = KnowledgeGraphBuilder(self.dataset_path)
            self.kg_builder.load_graph(kg_file)
        else:
            print("Building knowledge graph from dataset...")
            self.kg_builder = KnowledgeGraphBuilder(self.dataset_path)
            self.kg_builder.build_graph()
            self.kg_builder.save_graph(kg_file)
            self.kg_builder.export_to_json("knowledge_graph.json")
        
        print(f"Knowledge graph ready: {self.kg_builder.graph.number_of_nodes()} nodes, "
              f"{self.kg_builder.graph.number_of_edges()} edges")
    
    def step3_initialize_query_engine(self):
        """Step 3: Initialize query engine"""
        if not self.kg_builder:
            raise ValueError("Knowledge graph must be built first!")
        
        print("Initializing query engine...")
        self.query_engine = QueryEngine(self.kg_builder)
        print("Query engine ready!")
    
    def step4_answer_questions(self, output_file: str = "answers.json", limit: int = None):
        """Step 4: Answer questions using knowledge graph"""
        if not self.query_engine:
            raise ValueError("Query engine must be initialized first!")
        
        if not self.questions:
            raise ValueError("No questions available!")
        
        print(f"Answering {len(self.questions) if not limit else limit} questions...")
        
        questions_to_answer = self.questions[:limit] if limit else self.questions
        results = self.query_engine.batch_answer(questions_to_answer)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Answers saved to {output_file}")
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: list):
        """Print summary of results"""
        total = len(results)
        with_answers = sum(1 for r in results if r.get('answer'))
        avg_confidence = sum(r.get('confidence', 0) for r in results) / total if total > 0 else 0
        
        print(f"\n=== Summary ===")
        print(f"Total questions: {total}")
        print(f"Questions with answers: {with_answers}")
        print(f"Average confidence: {avg_confidence:.2f}")
        print(f"Questions with predictions: {sum(1 for r in results if r.get('predicted_option'))}")
    
    def _get_sample_questions(self):
        """Get sample questions for testing"""
        return [
            {
                'question': 'What is Snort used for?',
                'options': ['A. Network scanning', 'B. Intrusion Detection', 'C. Firewall', 'D. Encryption'],
                'correct_answer': 'B'
            },
            {
                'question': 'Which tool can analyze network traffic?',
                'options': ['A. Nmap', 'B. Snort', 'C. Metasploit', 'D. Wireshark'],
                'correct_answer': 'B'
            },
            {
                'question': 'What does Nmap use for network discovery?',
                'options': ['A. TCP packets', 'B. UDP packets', 'C. IP packets', 'D. ICMP packets'],
                'correct_answer': 'C'
            },
            {
                'question': 'What is the primary function of an IDS?',
                'options': ['A. Block attacks', 'B. Detect intrusions', 'C. Encrypt data', 'D. Manage users'],
                'correct_answer': 'B'
            },
            {
                'question': 'Which protocol does WPA2 use?',
                'options': ['A. EAP', 'B. IPsec', 'C. SSL', 'D. SSH'],
                'correct_answer': 'A'
            }
        ]
    
    def run_full_pipeline(self, scrape: bool = True, max_pages: int = 50, 
                         rebuild_kg: bool = False, answer_limit: int = None):
        """Run the complete pipeline"""
        print("=" * 60)
        print("AISecKG CISSP Question Answering Pipeline")
        print("=" * 60)
        
        # Step 1: Scrape questions
        if scrape:
            self.step1_scrape_questions(max_pages=max_pages)
        else:
            # Try to load existing questions
            questions_file = "cissp_questions.json"
            if os.path.exists(questions_file):
                with open(questions_file, 'r', encoding='utf-8') as f:
                    self.questions = json.load(f)
            else:
                print("No existing questions found. Using sample questions.")
                self.questions = self._get_sample_questions()
        
        # Step 2: Build knowledge graph
        self.step2_build_knowledge_graph(force_rebuild=rebuild_kg)
        
        # Step 3: Initialize query engine
        self.step3_initialize_query_engine()
        
        # Step 4: Answer questions
        results = self.step4_answer_questions(limit=answer_limit)
        
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        
        return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CISSP Question Answering Pipeline')
    parser.add_argument('--scrape', action='store_true', help='Scrape questions from website')
    parser.add_argument('--no-scrape', dest='scrape', action='store_false', help='Skip scraping')
    parser.add_argument('--max-pages', type=int, default=50, help='Maximum pages to scrape')
    parser.add_argument('--rebuild-kg', action='store_true', help='Force rebuild knowledge graph')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of questions to answer')
    parser.set_defaults(scrape=False)
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = MainPipeline()
    pipeline.run_full_pipeline(
        scrape=args.scrape,
        max_pages=args.max_pages,
        rebuild_kg=args.rebuild_kg,
        answer_limit=args.limit
    )


if __name__ == "__main__":
    main()
