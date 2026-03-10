"""
Query Engine for Answering CISSP Questions using Knowledge Graph
Matches questions to knowledge graph entities and generates answers
"""

import re
import json
from typing import List, Dict, Tuple, Set
from collections import defaultdict, Counter
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import numpy as np
from kg_builder import KnowledgeGraphBuilder

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)


class QueryEngine:
    def __init__(self, kg_builder: KnowledgeGraphBuilder):
        self.kg = kg_builder
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Security domain keywords mapping
        self.domain_keywords = {
            'access_control': ['access', 'control', 'authorization', 'authentication', 'rbac', 'dac', 'mac'],
            'network': ['network', 'packet', 'traffic', 'protocol', 'tcp', 'udp', 'ip'],
            'attack': ['attack', 'exploit', 'vulnerability', 'threat', 'malware', 'intrusion'],
            'tool': ['tool', 'scanner', 'nmap', 'snort', 'ids', 'ips', 'firewall'],
            'encryption': ['encryption', 'decryption', 'cipher', 'key', 'ssl', 'tls'],
            'policy': ['policy', 'procedure', 'compliance', 'governance', 'risk']
        }
    
    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text: tokenize, lowercase, remove stopwords, lemmatize"""
        tokens = word_tokenize(text.lower())
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                 if token.isalnum() and token not in self.stop_words]
        return tokens
    
    def extract_key_terms(self, question: str) -> Set[str]:
        """Extract key terms from question"""
        tokens = self.preprocess_text(question)
        
        # Find entities in knowledge graph
        key_terms = set()
        question_lower = question.lower()
        
        # Search for entity names in question
        for entity_name in self.kg.entities.keys():
            if isinstance(entity_name, str):
                entity_lower = entity_name.lower()
                # Check if entity name appears in question
                if len(entity_lower) > 2 and entity_lower in question_lower:
                    key_terms.add(entity_name)
        
        # Add important tokens (nouns, capitalized words)
        words = word_tokenize(question)
        for word in words:
            if word[0].isupper() and len(word) > 2:
                key_terms.add(word)
        
        return key_terms
    
    def find_relevant_entities(self, question: str) -> List[Tuple[str, float]]:
        """Find entities relevant to the question with relevance scores"""
        key_terms = self.extract_key_terms(question)
        question_tokens = set(self.preprocess_text(question))
        
        entity_scores = []
        
        # Direct matches
        for entity_name, entity_data in self.kg.entities.items():
            if isinstance(entity_name, str):
                score = 0.0
                entity_lower = entity_name.lower()
                question_lower = question.lower()
                
                # Exact match
                if entity_name in key_terms:
                    score += 10.0
                
                # Partial match in question
                if entity_lower in question_lower:
                    score += 5.0
                
                # Token overlap
                entity_tokens = set(self.preprocess_text(entity_name))
                overlap = len(question_tokens & entity_tokens)
                if overlap > 0:
                    score += overlap * 2.0
                
                # Type-based matching
                if isinstance(entity_data, dict):
                    entity_type = entity_data.get('type', '').lower()
                    entity_category = entity_data.get('category', '').lower()
                    
                    # Check if question mentions entity type
                    if entity_type in question_lower or entity_category in question_lower:
                        score += 3.0
                
                if score > 0:
                    entity_scores.append((entity_name, score))
        
        # Sort by score
        entity_scores.sort(key=lambda x: x[1], reverse=True)
        return entity_scores[:10]  # Top 10 entities
    
    def extract_relation_keywords(self, question: str) -> List[str]:
        """Extract relation keywords from question"""
        question_lower = question.lower()
        relation_keywords = []
        
        # Map question patterns to relations
        relation_patterns = {
            'uses': ['uses', 'utilizes', 'employs', 'applies'],
            'has_a': ['has', 'contains', 'includes', 'consists'],
            'is_a': ['is', 'are', 'type of', 'kind of'],
            'can_analyze': ['analyzes', 'examines', 'inspects', 'monitors'],
            'can_detect': ['detects', 'identifies', 'finds', 'discovers'],
            'can_exploit': ['exploits', 'takes advantage'],
            'can_harm': ['harms', 'damages', 'affects', 'impacts'],
            'is_part_of': ['part of', 'component of', 'belongs to'],
            'implements': ['implements', 'executes', 'performs']
        }
        
        for relation, patterns in relation_patterns.items():
            for pattern in patterns:
                if pattern in question_lower:
                    relation_keywords.append(relation)
                    break
        
        return relation_keywords
    
    def query_knowledge_graph(self, question: str) -> Dict:
        """Query the knowledge graph to find relevant information"""
        # Find relevant entities
        relevant_entities = self.find_relevant_entities(question)
        relation_keywords = self.extract_relation_keywords(question)
        
        # Gather information from knowledge graph
        kg_info = {
            'entities': [],
            'relations': [],
            'paths': [],
            'subgraph_triples': []
        }
        
        # Get information about top entities
        top_entities = [e[0] for e in relevant_entities[:5]]
        
        for entity in top_entities:
            entity_info = self.kg.get_entity_info(entity)
            related = self.kg.find_related_entities(entity)
            
            kg_info['entities'].append({
                'name': entity,
                'info': entity_info,
                'related': related[:5]  # Top 5 relations
            })
            
            # Get triples involving this entity
            for e1, r, e2 in self.kg.triples:
                if entity.lower() in e1.lower() or entity.lower() in e2.lower():
                    kg_info['subgraph_triples'].append((e1, r, e2))
        
        # Find paths between entities if multiple found
        if len(top_entities) >= 2:
            for i in range(len(top_entities) - 1):
                paths = self.kg.get_path_between_entities(top_entities[i], top_entities[i+1], max_length=3)
                kg_info['paths'].extend(paths[:3])
        
        return kg_info
    
    def generate_answer(self, question: str, options: List[str] = None) -> Dict:
        """Generate answer based on knowledge graph"""
        kg_info = self.query_knowledge_graph(question)
        
        # Extract key information
        answer_text = ""
        confidence = 0.0
        supporting_evidence = []
        
        if kg_info['entities']:
            # Build answer from entity information
            entity_names = [e['name'] for e in kg_info['entities']]
            answer_text = f"Based on the knowledge graph, the question relates to: {', '.join(entity_names[:3])}.\n\n"
            
            # Add relevant triples
            if kg_info['subgraph_triples']:
                answer_text += "Relevant information:\n"
                for e1, r, e2 in kg_info['subgraph_triples'][:5]:
                    answer_text += f"- {e1} {r} {e2}\n"
                    supporting_evidence.append(f"{e1} {r} {e2}")
            
            # Calculate confidence based on number of matches
            confidence = min(len(kg_info['entities']) * 0.2, 1.0)
        
        # Match to options if provided
        matched_option = None
        if options:
            option_scores = []
            for i, option in enumerate(options):
                option_entities = self.find_relevant_entities(option)
                score = sum([e[1] for e in option_entities[:3]])
                option_scores.append((chr(65 + i), option, score))
            
            if option_scores:
                option_scores.sort(key=lambda x: x[2], reverse=True)
                matched_option = option_scores[0][0]  # Best matching option letter
        
        return {
            'answer_text': answer_text,
            'confidence': confidence,
            'matched_option': matched_option,
            'supporting_evidence': supporting_evidence,
            'kg_info': kg_info
        }
    
    def answer_question(self, question_data: Dict) -> Dict:
        """Answer a CISSP question"""
        question = question_data.get('question', '')
        options = question_data.get('options', [])
        
        result = self.generate_answer(question, options)
        
        return {
            'question': question,
            'answer': result['answer_text'],
            'predicted_option': result['matched_option'],
            'confidence': result['confidence'],
            'supporting_evidence': result['supporting_evidence'],
            'options': options
        }
    
    def batch_answer(self, questions: List[Dict]) -> List[Dict]:
        """Answer multiple questions"""
        results = []
        for q in questions:
            result = self.answer_question(q)
            results.append(result)
        return results


def main():
    # Build knowledge graph
    print("Building knowledge graph...")
    kg_builder = KnowledgeGraphBuilder(dataset_path="dataset")
    kg_builder.build_graph()
    
    # Initialize query engine
    print("Initializing query engine...")
    engine = QueryEngine(kg_builder)
    
    # Example questions
    test_questions = [
        {
            'question': 'What is Snort used for?',
            'options': ['A. Network scanning', 'B. Intrusion Detection', 'C. Firewall', 'D. Encryption']
        },
        {
            'question': 'Which tool can analyze network traffic?',
            'options': ['A. Nmap', 'B. Snort', 'C. Metasploit', 'D. Wireshark']
        },
        {
            'question': 'What does Nmap use for network discovery?',
            'options': ['A. TCP packets', 'B. UDP packets', 'C. IP packets', 'D. ICMP packets']
        }
    ]
    
    print("\n=== Answering Questions ===")
    for q in test_questions:
        result = engine.answer_question(q)
        print(f"\nQuestion: {result['question']}")
        print(f"Answer: {result['answer']}")
        print(f"Predicted Option: {result['predicted_option']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Evidence: {result['supporting_evidence'][:3]}")


if __name__ == "__main__":
    main()
