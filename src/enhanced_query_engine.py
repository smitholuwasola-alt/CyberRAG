"""
Enhanced Query Engine for CyberRAG
Extends the original QueryEngine with CyBOK textbook knowledge,
multi-hop reasoning, and improved answer generation.
"""

import re
import json
from typing import List, Dict, Tuple, Set
from collections import defaultdict, Counter
from pathlib import Path

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

from kg_builder import KnowledgeGraphBuilder

PROJECT_ROOT = Path(__file__).parent.parent

# ──────────────────────────────────────────────────────
# CyBOK Knowledge Area index for topic routing
# ──────────────────────────────────────────────────────
CYBOK_KA_INDEX = {
    "Risk Management and Governance": [
        "risk", "governance", "security policy", "business continuity",
        "incident response", "vulnerability management", "security metrics",
        "risk assessment", "compliance", "audit"
    ],
    "Law and Regulation": [
        "law", "regulation", "gdpr", "privacy law", "data protection",
        "computer crime", "intellectual property", "jurisdiction", "liability",
        "digital evidence"
    ],
    "Human Factors": [
        "human factor", "social engineering", "phishing", "security awareness",
        "usable security", "password", "user behavior", "security culture"
    ],
    "Privacy and Online Rights": [
        "privacy", "anonymity", "surveillance", "censorship", "tracking",
        "tor", "vpn", "pseudonymity", "data minimization"
    ],
    "Malware and Attack Technologies": [
        "malware", "virus", "worm", "trojan", "ransomware", "rootkit",
        "botnet", "exploit kit", "payload", "dropper", "rat"
    ],
    "Adversarial Behaviours": [
        "threat actor", "apt", "advanced persistent threat", "cyber crime",
        "kill chain", "mitre att&ck", "tactics", "techniques", "threat intelligence"
    ],
    "Security Operations and Incident Management": [
        "siem", "soc", "incident handling", "monitoring", "log analysis",
        "alerting", "triage", "containment", "detection", "response"
    ],
    "Forensics": [
        "forensic", "evidence", "chain of custody", "disk forensic",
        "memory forensic", "network forensic", "mobile forensic",
        "timeline", "acquisition", "preservation"
    ],
    "Cryptography": [
        "cryptography", "cipher", "aes", "rsa", "sha", "hash",
        "symmetric", "asymmetric", "block cipher", "stream cipher",
        "elliptic curve", "diffie-hellman", "key exchange"
    ],
    "Applied Cryptography": [
        "tls", "ssl", "https", "certificate", "pki",
        "key management", "secure messaging", "end-to-end encryption"
    ],
    "Operating Systems and Virtualisation Security": [
        "operating system", "kernel", "privilege escalation", "sandbox",
        "container", "hypervisor", "virtual machine", "selinux", "apparmor"
    ],
    "Distributed Systems Security": [
        "distributed system", "consensus", "blockchain", "cloud security",
        "microservice", "api security", "peer-to-peer"
    ],
    "Authentication, Authorisation and Accountability": [
        "authentication", "authorization", "accountability", "mfa",
        "multi-factor", "oauth", "saml", "rbac", "abac", "identity",
        "single sign-on", "kerberos", "ldap", "biometric"
    ],
    "Software Security": [
        "buffer overflow", "sql injection", "xss", "csrf", "code review",
        "fuzzing", "secure coding", "owasp", "vulnerability", "cwe",
        "static analysis", "dynamic analysis", "sast", "dast"
    ],
    "Web and Mobile Security": [
        "web security", "browser", "same-origin policy", "content security policy",
        "mobile security", "app security", "javascript", "dom"
    ],
    "Secure Software Lifecycle": [
        "sdl", "devsecops", "threat modeling", "security testing",
        "penetration testing", "security requirement", "secure design",
        "ci/cd", "supply chain"
    ],
    "Network Security": [
        "firewall", "ids", "ips", "vpn", "dns", "bgp", "ddos",
        "network segmentation", "zero trust", "packet filtering",
        "proxy", "nmap", "snort", "suricata", "wireshark"
    ],
    "Hardware Security": [
        "hardware security", "tpm", "hsm", "side-channel", "fault injection",
        "tamper", "secure boot", "fpga", "hardware trojan"
    ],
    "Cyber-Physical Systems Security": [
        "scada", "ics", "iot", "industrial control", "plc", "sensor",
        "actuator", "cyber-physical", "operational technology"
    ],
    "Physical Layer and Telecommunications Security": [
        "wireless", "bluetooth", "wifi", "cellular", "jamming",
        "eavesdropping", "rf security", "signal"
    ],
}


class EnhancedQueryEngine:
    """
    Enhanced query engine that combines the original AISecKG knowledge graph
    with CyBOK textbook knowledge for comprehensive cybersecurity Q&A.
    """

    def __init__(self, kg_builder: KnowledgeGraphBuilder = None):
        if kg_builder is None:
            kg_builder = KnowledgeGraphBuilder()
            kg_builder.build_graph()
        self.kg = kg_builder

        self.use_nltk = False
        self.lemmatizer = None
        self.stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were',
                           'be', 'been', 'being', 'have', 'has', 'had',
                           'do', 'does', 'did', 'will', 'would', 'shall',
                           'should', 'may', 'might', 'can', 'could',
                           'and', 'but', 'or', 'nor', 'not', 'so', 'yet',
                           'at', 'by', 'for', 'from', 'in', 'of', 'on',
                           'to', 'with', 'about', 'into', 'through',
                           'this', 'that', 'these', 'those', 'it', 'its',
                           'what', 'which', 'who', 'whom', 'whose'}

        if HAS_NLTK:
            try:
                nltk.data.find('tokenizers/punkt_tab')
                nltk.data.find('corpora/stopwords')
                nltk.data.find('corpora/wordnet')
                self.lemmatizer = WordNetLemmatizer()
                self.stop_words = set(stopwords.words('english'))
                self.use_nltk = True
            except LookupError:
                pass  # Fallback to regex-based processing

        # Build reverse index for fast entity lookup
        self._build_entity_index()

    def _build_entity_index(self):
        """Build indexes for fast entity and triple lookup."""
        self.entity_by_name = {}
        self.entity_by_type = defaultdict(list)

        for ename, edata in self.kg.entities.items():
            if isinstance(edata, dict):
                self.entity_by_name[ename.lower()] = edata
                etype = edata.get('type', '')
                self.entity_by_type[etype].append(ename)

        # Build triple index by entity
        self.triples_by_entity = defaultdict(list)
        for e1, r, e2 in self.kg.triples:
            self.triples_by_entity[e1.lower()].append((e1, r, e2))
            self.triples_by_entity[e2.lower()].append((e1, r, e2))

        # Build triple index by relation
        self.triples_by_relation = defaultdict(list)
        for e1, r, e2 in self.kg.triples:
            self.triples_by_relation[r].append((e1, r, e2))

    def preprocess_text(self, text: str) -> List[str]:
        """Tokenize, lowercase, remove stopwords, lemmatize."""
        if self.use_nltk and self.lemmatizer:
            tokens = word_tokenize(text.lower())
            tokens = [self.lemmatizer.lemmatize(t) for t in tokens
                      if t.isalnum() and t not in self.stop_words]
        else:
            tokens = re.findall(r'\b\w+\b', text.lower())
            tokens = [t for t in tokens if t not in self.stop_words and len(t) > 1]
        return tokens

    def identify_cybok_kas(self, question: str) -> List[Tuple[str, float]]:
        """Identify which CyBOK Knowledge Areas are relevant to the question."""
        question_lower = question.lower()
        question_tokens = set(self.preprocess_text(question))
        ka_scores = []

        for ka_name, keywords in CYBOK_KA_INDEX.items():
            score = 0.0
            for kw in keywords:
                if kw in question_lower:
                    score += 5.0
                kw_tokens = set(kw.split())
                overlap = len(question_tokens & kw_tokens)
                score += overlap * 2.0
            if score > 0:
                ka_scores.append((ka_name, score))

        ka_scores.sort(key=lambda x: x[1], reverse=True)
        return ka_scores[:3]

    def find_relevant_entities(self, question: str) -> List[Tuple[str, float]]:
        """Find entities relevant to the question with relevance scores."""
        question_lower = question.lower()
        question_tokens = set(self.preprocess_text(question))
        entity_scores = []

        for ename, edata in self.kg.entities.items():
            if not isinstance(ename, str) or not isinstance(edata, dict):
                continue

            score = 0.0
            ename_lower = ename.lower()

            # Exact name match in question
            if len(ename_lower) > 2 and ename_lower in question_lower:
                score += 10.0
                # Bonus for longer matches (more specific)
                score += len(ename_lower) * 0.5

            # Token overlap
            entity_tokens = set(self.preprocess_text(ename))
            overlap = question_tokens & entity_tokens
            if overlap:
                score += len(overlap) * 3.0

            # Entity type or category mentioned in question
            etype = edata.get('type', '').lower()
            ecat = edata.get('category', '').lower()
            if etype and etype in question_lower:
                score += 2.0
            if ecat and ecat in question_lower:
                score += 2.0

            # Boost for entities with many connections (more informative)
            connection_count = len(self.triples_by_entity.get(ename_lower, []))
            if connection_count > 0 and score > 0:
                score += min(connection_count * 0.1, 3.0)

            if score > 0:
                entity_scores.append((ename, score))

        entity_scores.sort(key=lambda x: x[1], reverse=True)
        return entity_scores[:15]

    def multi_hop_query(self, entity_name: str, max_hops: int = 2) -> Dict:
        """Retrieve multi-hop neighborhood around an entity."""
        result = {
            'center': entity_name,
            'direct_relations': [],
            'two_hop_relations': [],
            'paths': []
        }

        ename_lower = entity_name.lower()

        # 1-hop: direct relations
        direct_triples = self.triples_by_entity.get(ename_lower, [])
        result['direct_relations'] = direct_triples[:20]

        # 2-hop: relations of direct neighbors
        if max_hops >= 2:
            neighbors = set()
            for e1, r, e2 in direct_triples[:10]:
                if e1.lower() != ename_lower:
                    neighbors.add(e1.lower())
                if e2.lower() != ename_lower:
                    neighbors.add(e2.lower())

            for neighbor in list(neighbors)[:5]:
                neighbor_triples = self.triples_by_entity.get(neighbor, [])
                for t in neighbor_triples[:5]:
                    if t not in result['direct_relations']:
                        result['two_hop_relations'].append(t)

        return result

    def extract_relation_intent(self, question: str) -> List[str]:
        """Determine what type of relationship the question asks about."""
        question_lower = question.lower()
        intents = []

        intent_patterns = {
            'uses': ['use', 'utiliz', 'employ', 'leverag', 'rely on', 'work with'],
            'can_detect': ['detect', 'identify', 'discover', 'find', 'prevent', 'protect', 'defend', 'mitigat'],
            'can_exploit': ['exploit', 'attack', 'target', 'breach', 'compromise', 'bypass'],
            'is_a': ['type of', 'kind of', 'form of', 'example of', 'classified as', 'category'],
            'is_part_of': ['part of', 'component', 'belong', 'included in', 'subset', 'element of'],
            'has_a': ['has', 'contain', 'include', 'feature', 'consist', 'composed of'],
            'can_analyze': ['analyz', 'examin', 'inspect', 'monitor', 'assess', 'evaluat'],
            'implements': ['implement', 'provide', 'enforce', 'enable', 'support'],
            'can_harm': ['harm', 'damag', 'destroy', 'disrupt', 'impact', 'affect'],
        }

        for relation, patterns in intent_patterns.items():
            for pat in patterns:
                if pat in question_lower:
                    intents.append(relation)
                    break

        return intents

    def generate_answer(self, question: str, options: List[str] = None) -> Dict:
        """Generate a comprehensive answer using the enhanced KG."""

        # Step 1: Identify relevant Knowledge Areas
        relevant_kas = self.identify_cybok_kas(question)

        # Step 2: Find relevant entities
        relevant_entities = self.find_relevant_entities(question)

        # Step 3: Determine relationship intent
        relation_intents = self.extract_relation_intent(question)

        # Step 4: Multi-hop query for top entities
        kg_context = []
        all_triples = []
        for ename, score in relevant_entities[:5]:
            hop_data = self.multi_hop_query(ename, max_hops=2)
            kg_context.append(hop_data)

            # Filter triples by relation intent if we have one
            for t in hop_data['direct_relations']:
                if not relation_intents or t[1] in relation_intents:
                    all_triples.append(t)
                else:
                    all_triples.append(t)

            for t in hop_data['two_hop_relations'][:5]:
                all_triples.append(t)

        # Deduplicate triples
        seen = set()
        unique_triples = []
        for t in all_triples:
            key = (t[0].lower(), t[1], t[2].lower())
            if key not in seen:
                seen.add(key)
                unique_triples.append(t)

        # Step 5: Build answer text
        answer_parts = []

        if relevant_kas:
            ka_names = [ka[0] for ka in relevant_kas[:2]]
            answer_parts.append(
                f"This question relates to the CyBOK Knowledge Area(s): {', '.join(ka_names)}."
            )

        if relevant_entities:
            top_entities = [e[0] for e in relevant_entities[:5]]
            answer_parts.append(
                f"Key entities: {', '.join(top_entities)}."
            )

        if unique_triples:
            answer_parts.append("\nRelevant knowledge from the graph:")
            # Group triples by relation type for readability
            by_relation = defaultdict(list)
            for e1, r, e2 in unique_triples[:15]:
                by_relation[r].append((e1, e2))

            for rel, pairs in by_relation.items():
                rel_display = rel.replace('_', ' ')
                for e1, e2 in pairs[:4]:
                    answer_parts.append(f"  - {e1} [{rel_display}] {e2}")

        answer_text = '\n'.join(answer_parts) if answer_parts else "No relevant information found in the knowledge graph."

        # Step 6: Match to multiple-choice options
        matched_option = None
        option_analysis = []
        if options:
            option_scores = []
            for i, option in enumerate(options):
                score = 0.0
                option_lower = option.lower()

                # Check if option text matches any relevant entity
                for ename, escore in relevant_entities[:10]:
                    if ename.lower() in option_lower:
                        score += escore

                # Check if option matches any triple endpoints
                for e1, r, e2 in unique_triples:
                    if e1.lower() in option_lower or e2.lower() in option_lower:
                        score += 2.0

                option_letter = chr(65 + i)
                option_scores.append((option_letter, option, score))
                option_analysis.append({
                    'letter': option_letter,
                    'text': option,
                    'score': score
                })

            option_scores.sort(key=lambda x: x[2], reverse=True)
            if option_scores[0][2] > 0:
                matched_option = option_scores[0][0]

        # Step 7: Calculate confidence
        confidence = 0.0
        if relevant_entities:
            top_score = relevant_entities[0][1]
            entity_count = min(len(relevant_entities), 5)
            confidence = min(0.3 + (entity_count * 0.1) + (top_score * 0.02), 1.0)
            if unique_triples:
                confidence = min(confidence + len(unique_triples) * 0.02, 1.0)

        return {
            'answer_text': answer_text,
            'confidence': confidence,
            'matched_option': matched_option,
            'supporting_evidence': [f"{e1} {r} {e2}" for e1, r, e2 in unique_triples[:10]],
            'relevant_kas': [ka[0] for ka in relevant_kas],
            'relevant_entities': [(e[0], round(e[1], 2)) for e in relevant_entities[:10]],
            'option_analysis': option_analysis if options else [],
            'relation_intents': relation_intents,
        }

    def answer_question(self, question_data: Dict) -> Dict:
        """Main entry point for answering a question."""
        question = question_data.get('question', '')
        options = question_data.get('options', [])

        result = self.generate_answer(question, options)

        return {
            'question': question,
            'answer': result['answer_text'],
            'predicted_option': result['matched_option'],
            'confidence': result['confidence'],
            'supporting_evidence': result['supporting_evidence'],
            'relevant_kas': result['relevant_kas'],
            'option_analysis': result.get('option_analysis', []),
            'options': options,
        }

    def batch_answer(self, questions: List[Dict]) -> List[Dict]:
        """Answer multiple questions."""
        return [self.answer_question(q) for q in questions]


def main():
    """Demo the enhanced query engine."""
    print("Building knowledge graph...")
    kg = KnowledgeGraphBuilder()
    kg.build_graph()

    print("Initializing enhanced query engine...")
    engine = EnhancedQueryEngine(kg)

    print(f"\nKG Stats: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
    print(f"Entity types: {dict(Counter(e.get('type','?') for e in kg.entities.values() if isinstance(e, dict)))}")

    # Test questions spanning multiple CyBOK Knowledge Areas
    test_questions = [
        {
            'question': 'What is the purpose of Snort in network security?',
            'options': ['A. Port scanning', 'B. Intrusion Detection',
                        'C. Password cracking', 'D. Data encryption']
        },
        {
            'question': 'Which attack exploits vulnerabilities in web applications through malicious SQL queries?',
            'options': ['A. XSS', 'B. CSRF', 'C. SQL injection', 'D. Buffer overflow']
        },
        {
            'question': 'What does TLS provide for web communications?',
            'options': ['A. Load balancing', 'B. Encryption and authentication',
                        'C. Caching', 'D. URL routing']
        },
        {
            'question': 'What is the CIA triad in cybersecurity?',
            'options': []
        },
        {
            'question': 'How does defense in depth protect systems?',
            'options': []
        },
        {
            'question': 'What tools are used for digital forensics?',
            'options': []
        },
        {
            'question': 'What is the difference between symmetric and asymmetric encryption?',
            'options': []
        },
        {
            'question': 'How does RBAC implement access control?',
            'options': ['A. By encrypting data', 'B. By assigning permissions based on roles',
                        'C. By monitoring network traffic', 'D. By scanning for vulnerabilities']
        },
        {
            'question': 'Which tool can analyze network traffic in real time?',
            'options': ['A. Nmap', 'B. Wireshark', 'C. John the Ripper', 'D. Hashcat']
        },
        {
            'question': 'What is the relationship between GDPR and data privacy?',
            'options': []
        },
    ]

    print("\n" + "=" * 70)
    print("CYBERRAG ENHANCED Q&A DEMO")
    print("=" * 70)

    for q in test_questions:
        result = engine.answer_question(q)
        print(f"\n{'─' * 70}")
        print(f"Q: {result['question']}")
        if result['options']:
            for opt in result['options']:
                print(f"   {opt}")
        print(f"\nCyBOK Knowledge Areas: {', '.join(result['relevant_kas']) if result['relevant_kas'] else 'General'}")
        print(f"\n{result['answer']}")
        if result['predicted_option']:
            print(f"\nPredicted Answer: {result['predicted_option']}")
        print(f"Confidence: {result['confidence']:.2f}")
        if result['supporting_evidence']:
            print(f"Evidence: {result['supporting_evidence'][:3]}")


if __name__ == "__main__":
    main()
