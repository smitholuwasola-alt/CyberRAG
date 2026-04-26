"""
CyBOK Knowledge Extractor
Extracts entities, relations, and triples from the CyBOK v1.1.0 textbook
and merges them into the AISecKG knowledge graph.

Strategy:
1. Parse CyBOK text into chapters/sections
2. Extract cybersecurity entities (tools, concepts, attacks, standards, etc.)
3. Identify relationships between entities using pattern matching
4. Generate triples in AISecKG format (e1, r, e2)
5. Merge with existing KG data
"""

import re
import csv
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Set

PROJECT_ROOT = Path(__file__).parent.parent


# ─────────────────────────────────────────────
# CyBOK Knowledge Area definitions
# ─────────────────────────────────────────────
CYBOK_KNOWLEDGE_AREAS = {
    "Risk Management and Governance": {
        "category": "human_organisational_regulatory",
        "topics": ["risk assessment", "security governance", "security policy", "business continuity",
                   "incident response", "vulnerability management", "security metrics", "risk communication"]
    },
    "Law and Regulation": {
        "category": "human_organisational_regulatory",
        "topics": ["jurisdiction", "privacy law", "data protection", "GDPR", "computer crime law",
                   "intellectual property", "digital evidence", "liability"]
    },
    "Human Factors": {
        "category": "human_organisational_regulatory",
        "topics": ["security awareness", "social engineering", "usable security", "security culture",
                   "phishing", "password management", "security behavior"]
    },
    "Privacy and Online Rights": {
        "category": "human_organisational_regulatory",
        "topics": ["privacy", "anonymity", "data protection", "surveillance", "censorship",
                   "online rights", "tracking", "privacy-enhancing technologies"]
    },
    "Malware and Attack Technologies": {
        "category": "attacks_defences",
        "topics": ["malware", "virus", "worm", "trojan", "ransomware", "rootkit", "botnet",
                   "exploit kit", "attack framework", "payload", "dropper"]
    },
    "Adversarial Behaviours": {
        "category": "attacks_defences",
        "topics": ["threat actor", "APT", "cyber crime", "hacktivism", "cyber espionage",
                   "attack lifecycle", "kill chain", "MITRE ATT&CK", "tactics", "techniques"]
    },
    "Security Operations and Incident Management": {
        "category": "attacks_defences",
        "topics": ["SIEM", "SOC", "incident handling", "forensics", "threat intelligence",
                   "log analysis", "monitoring", "alerting", "triage", "containment"]
    },
    "Forensics": {
        "category": "attacks_defences",
        "topics": ["digital forensics", "evidence collection", "chain of custody", "disk forensics",
                   "memory forensics", "network forensics", "mobile forensics", "timeline analysis"]
    },
    "Cryptography": {
        "category": "systems_security",
        "topics": ["symmetric encryption", "asymmetric encryption", "hash function", "digital signature",
                   "key management", "PKI", "TLS", "AES", "RSA", "elliptic curve"]
    },
    "Applied Cryptography": {
        "category": "systems_security",
        "topics": ["TLS", "SSL", "HTTPS", "certificate", "key exchange", "secure messaging",
                   "end-to-end encryption", "protocol analysis"]
    },
    "Operating Systems and Virtualisation Security": {
        "category": "systems_security",
        "topics": ["access control", "privilege escalation", "sandboxing", "containerization",
                   "hypervisor", "virtual machine", "kernel security", "SELinux", "AppArmor"]
    },
    "Distributed Systems Security": {
        "category": "systems_security",
        "topics": ["distributed system", "consensus", "blockchain", "peer-to-peer", "cloud security",
                   "microservices", "service mesh", "API security"]
    },
    "Formal Methods for Security": {
        "category": "systems_security",
        "topics": ["formal verification", "model checking", "theorem proving", "security protocol verification",
                   "type systems", "static analysis"]
    },
    "Authentication, Authorisation and Accountability": {
        "category": "infrastructure_security",
        "topics": ["authentication", "authorization", "accountability", "multi-factor authentication",
                   "OAuth", "SAML", "RBAC", "ABAC", "identity management", "single sign-on"]
    },
    "Software Security": {
        "category": "infrastructure_security",
        "topics": ["buffer overflow", "SQL injection", "XSS", "CSRF", "code review", "static analysis",
                   "dynamic analysis", "fuzzing", "secure coding", "OWASP", "vulnerability"]
    },
    "Web and Mobile Security": {
        "category": "infrastructure_security",
        "topics": ["web security", "mobile security", "browser security", "same-origin policy",
                   "content security policy", "certificate pinning", "app sandboxing"]
    },
    "Secure Software Lifecycle": {
        "category": "infrastructure_security",
        "topics": ["SDL", "DevSecOps", "threat modeling", "security testing", "penetration testing",
                   "security requirements", "secure design", "SAST", "DAST"]
    },
    "Network Security": {
        "category": "infrastructure_security",
        "topics": ["firewall", "IDS", "IPS", "VPN", "DNS security", "BGP security", "DDoS",
                   "network segmentation", "zero trust", "packet filtering", "proxy"]
    },
    "Hardware Security": {
        "category": "infrastructure_security",
        "topics": ["hardware security module", "TPM", "side-channel attack", "fault injection",
                   "tamper resistance", "secure boot", "hardware trojan", "FPGA security"]
    },
    "Cyber-Physical Systems Security": {
        "category": "infrastructure_security",
        "topics": ["SCADA", "ICS", "IoT security", "industrial control", "PLC", "sensor security",
                   "actuator security", "cyber-physical system", "OT security"]
    },
    "Physical Layer and Telecommunications Security": {
        "category": "infrastructure_security",
        "topics": ["wireless security", "Bluetooth", "WiFi security", "cellular security",
                   "jamming", "eavesdropping", "signal analysis", "RF security"]
    }
}

# ─────────────────────────────────────────────
# Cybersecurity entity dictionaries
# ─────────────────────────────────────────────

TOOL_ENTITIES = {
    # Network tools
    "Nmap": ("tool", "application"), "Wireshark": ("tool", "application"),
    "Snort": ("tool", "application"), "Suricata": ("tool", "application"),
    "Metasploit": ("tool", "application"), "Burp Suite": ("tool", "application"),
    "Nessus": ("tool", "application"), "OpenVAS": ("tool", "application"),
    "Nikto": ("tool", "application"), "John the Ripper": ("tool", "application"),
    "Hashcat": ("tool", "application"), "Aircrack-ng": ("tool", "application"),
    "tcpdump": ("tool", "application"), "netcat": ("tool", "application"),
    "Volatility": ("tool", "application"), "Autopsy": ("tool", "application"),
    "EnCase": ("tool", "application"), "FTK": ("tool", "application"),
    "Splunk": ("tool", "application"), "ELK Stack": ("tool", "application"),
    "OSSEC": ("tool", "application"), "Zeek": ("tool", "application"),
    "pfSense": ("tool", "application"), "iptables": ("tool", "application"),
    "ModSecurity": ("tool", "application"), "YARA": ("tool", "application"),
    "Ghidra": ("tool", "application"), "IDA Pro": ("tool", "application"),
    "Cuckoo Sandbox": ("tool", "application"), "GnuPG": ("tool", "application"),
    "OpenSSL": ("tool", "application"), "Tor": ("tool", "application"),
    "OWASP ZAP": ("tool", "application"),
}

ATTACK_ENTITIES = {
    # Attack types
    "buffer overflow": ("attack", "technique"), "SQL injection": ("attack", "technique"),
    "cross-site scripting": ("attack", "technique"), "XSS": ("attack", "technique"),
    "CSRF": ("attack", "technique"), "cross-site request forgery": ("attack", "technique"),
    "phishing": ("attack", "technique"), "spear phishing": ("attack", "technique"),
    "denial of service": ("attack", "technique"), "DDoS": ("attack", "technique"),
    "man-in-the-middle": ("attack", "technique"), "MITM": ("attack", "technique"),
    "privilege escalation": ("attack", "technique"),
    "brute force": ("attack", "technique"), "dictionary attack": ("attack", "technique"),
    "rainbow table": ("attack", "technique"), "replay attack": ("attack", "technique"),
    "side-channel attack": ("attack", "technique"), "timing attack": ("attack", "technique"),
    "spoofing": ("attack", "technique"), "ARP spoofing": ("attack", "technique"),
    "DNS spoofing": ("attack", "technique"), "IP spoofing": ("attack", "technique"),
    "session hijacking": ("attack", "technique"), "clickjacking": ("attack", "technique"),
    "rootkit": ("attack", "malware"), "ransomware": ("attack", "malware"),
    "trojan": ("attack", "malware"), "worm": ("attack", "malware"),
    "virus": ("attack", "malware"), "botnet": ("attack", "malware"),
    "keylogger": ("attack", "malware"), "spyware": ("attack", "malware"),
    "adware": ("attack", "malware"), "backdoor": ("attack", "malware"),
    "zero-day": ("attack", "vulnerability"), "exploit": ("attack", "technique"),
    "social engineering": ("attack", "technique"), "watering hole": ("attack", "technique"),
    "drive-by download": ("attack", "technique"), "supply chain attack": ("attack", "technique"),
    "advanced persistent threat": ("attack", "technique"), "APT": ("attack", "technique"),
    "insider threat": ("attack", "technique"), "code injection": ("attack", "technique"),
    "command injection": ("attack", "technique"), "path traversal": ("attack", "technique"),
    "race condition": ("attack", "technique"), "integer overflow": ("attack", "technique"),
    "format string": ("attack", "technique"), "use-after-free": ("attack", "technique"),
    "heap overflow": ("attack", "technique"), "stack overflow": ("attack", "technique"),
    "return-oriented programming": ("attack", "technique"),
    "cache poisoning": ("attack", "technique"),
    "BGP hijacking": ("attack", "technique"),
    "fault injection": ("attack", "technique"),
}

CONCEPT_ENTITIES = {
    # Security concepts
    "confidentiality": ("concept", "security_property"), "integrity": ("concept", "security_property"),
    "availability": ("concept", "security_property"), "authentication": ("concept", "security_mechanism"),
    "authorization": ("concept", "security_mechanism"), "accountability": ("concept", "security_mechanism"),
    "non-repudiation": ("concept", "security_property"), "access control": ("concept", "security_mechanism"),
    "encryption": ("concept", "security_mechanism"), "decryption": ("concept", "security_mechanism"),
    "hashing": ("concept", "security_mechanism"), "digital signature": ("concept", "security_mechanism"),
    "certificate": ("concept", "security_mechanism"), "PKI": ("concept", "infrastructure"),
    "TLS": ("concept", "protocol"), "SSL": ("concept", "protocol"),
    "HTTPS": ("concept", "protocol"), "IPsec": ("concept", "protocol"),
    "VPN": ("concept", "infrastructure"), "firewall": ("concept", "security_mechanism"),
    "IDS": ("concept", "security_mechanism"), "IPS": ("concept", "security_mechanism"),
    "SIEM": ("concept", "security_mechanism"), "SOC": ("concept", "infrastructure"),
    "threat modeling": ("concept", "methodology"), "risk assessment": ("concept", "methodology"),
    "penetration testing": ("concept", "methodology"), "vulnerability scanning": ("concept", "methodology"),
    "incident response": ("concept", "methodology"), "digital forensics": ("concept", "methodology"),
    "malware analysis": ("concept", "methodology"), "reverse engineering": ("concept", "methodology"),
    "secure coding": ("concept", "methodology"), "code review": ("concept", "methodology"),
    "defense in depth": ("concept", "principle"), "least privilege": ("concept", "principle"),
    "separation of duties": ("concept", "principle"), "zero trust": ("concept", "principle"),
    "fail-safe defaults": ("concept", "principle"), "complete mediation": ("concept", "principle"),
    "open design": ("concept", "principle"), "economy of mechanism": ("concept", "principle"),
    "RBAC": ("concept", "security_mechanism"), "ABAC": ("concept", "security_mechanism"),
    "MAC": ("concept", "security_mechanism"), "DAC": ("concept", "security_mechanism"),
    "multi-factor authentication": ("concept", "security_mechanism"),
    "single sign-on": ("concept", "security_mechanism"),
    "OAuth": ("concept", "protocol"), "SAML": ("concept", "protocol"),
    "sandboxing": ("concept", "security_mechanism"), "containerization": ("concept", "security_mechanism"),
    "virtualization": ("concept", "infrastructure"),
    "network segmentation": ("concept", "security_mechanism"),
    "data loss prevention": ("concept", "security_mechanism"),
    "intrusion detection": ("concept", "security_mechanism"),
    "intrusion prevention": ("concept", "security_mechanism"),
    "security awareness": ("concept", "methodology"),
    "security policy": ("concept", "governance"), "security governance": ("concept", "governance"),
    "business continuity": ("concept", "governance"), "disaster recovery": ("concept", "governance"),
    "privacy": ("concept", "security_property"), "anonymity": ("concept", "security_property"),
    "pseudonymity": ("concept", "security_property"),
    "key management": ("concept", "security_mechanism"),
    "symmetric encryption": ("concept", "security_mechanism"),
    "asymmetric encryption": ("concept", "security_mechanism"),
    "hash function": ("concept", "security_mechanism"),
    "blockchain": ("concept", "infrastructure"),
    "secure boot": ("concept", "security_mechanism"),
    "TPM": ("concept", "security_mechanism"),
    "HSM": ("concept", "security_mechanism"),
    "SCADA": ("concept", "infrastructure"),
    "IoT": ("concept", "infrastructure"),
    "cloud security": ("concept", "security_mechanism"),
    "DevSecOps": ("concept", "methodology"),
}

STANDARD_ENTITIES = {
    # Standards and frameworks
    "NIST": ("standard", "framework"), "ISO 27001": ("standard", "framework"),
    "ISO 27002": ("standard", "framework"), "GDPR": ("standard", "regulation"),
    "OWASP Top 10": ("standard", "framework"), "MITRE ATT&CK": ("standard", "framework"),
    "CVE": ("standard", "framework"), "CVSS": ("standard", "framework"),
    "CIS Controls": ("standard", "framework"), "NIST CSF": ("standard", "framework"),
    "PCI DSS": ("standard", "regulation"), "HIPAA": ("standard", "regulation"),
    "SOX": ("standard", "regulation"), "Common Criteria": ("standard", "framework"),
    "FIPS": ("standard", "framework"),
    "Cyber Kill Chain": ("standard", "framework"),
    "STRIDE": ("standard", "framework"), "DREAD": ("standard", "framework"),
    "OCTAVE": ("standard", "framework"), "FAIR": ("standard", "framework"),
}

ALGORITHM_ENTITIES = {
    "AES": ("algorithm", "cryptographic"), "RSA": ("algorithm", "cryptographic"),
    "SHA-256": ("algorithm", "cryptographic"), "SHA-1": ("algorithm", "cryptographic"),
    "MD5": ("algorithm", "cryptographic"), "DES": ("algorithm", "cryptographic"),
    "3DES": ("algorithm", "cryptographic"), "Blowfish": ("algorithm", "cryptographic"),
    "Diffie-Hellman": ("algorithm", "cryptographic"),
    "elliptic curve": ("algorithm", "cryptographic"),
    "HMAC": ("algorithm", "cryptographic"),
    "Kerberos": ("algorithm", "protocol"),
    "RADIUS": ("algorithm", "protocol"),
    "LDAP": ("algorithm", "protocol"),
}


# ─────────────────────────────────────────────
# Relationship extraction patterns
# ─────────────────────────────────────────────

RELATION_PATTERNS = [
    # (regex_pattern, relation_type)
    # "X is used to Y" / "X is used for Y"
    (r"(\b\w[\w\s\-]{1,40}?\b)\s+(?:is\s+)?used\s+(?:to|for)\s+(\b\w[\w\s\-]{1,40}?\b)", "uses"),
    # "X detects Y" / "X can detect Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:can\s+)?detect(?:s|ed|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "can_detect"),
    # "X exploits Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:can\s+)?exploit(?:s|ed|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "can_exploit"),
    # "X protects against Y" / "X prevents Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:protect(?:s|ed|ing)?\s+against|prevent(?:s|ed|ing)?)\s+(\b\w[\w\s\-]{1,30}?\b)", "can_detect"),
    # "X is a type of Y" / "X is a form of Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+is\s+(?:a\s+)?(?:type|form|kind|class|category)\s+of\s+(\b\w[\w\s\-]{1,30}?\b)", "is_a"),
    # "X implements Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+implement(?:s|ed|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "implements"),
    # "X is part of Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+is\s+(?:a\s+)?(?:part|component|element)\s+of\s+(\b\w[\w\s\-]{1,30}?\b)", "is_part_of"),
    # "X analyzes Y" / "X analyses Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:can\s+)?analy[sz]e(?:s|d|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "can_analyze"),
    # "X harms Y" / "X damages Y" / "X compromises Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:can\s+)?(?:harm|damage|compromise)(?:s|d|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "can_harm"),
    # "X exposes Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:can\s+)?expose(?:s|d|ing)?\s+(\b\w[\w\s\-]{1,30}?\b)", "can_expose"),
    # "X uses Y" / "X utilizes Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:uses|utilizes|employs|leverages)\s+(\b\w[\w\s\-]{1,30}?\b)", "uses"),
    # "X has Y" / "X contains Y" / "X includes Y"
    (r"(\b\w[\w\s\-]{1,30}?\b)\s+(?:has|contains|includes|provides)\s+(\b\w[\w\s\-]{1,30}?\b)", "has_a"),
]


class CyBOKExtractor:
    """Extracts knowledge from the CyBOK textbook into AISecKG-compatible format."""

    def __init__(self, cybok_text_path: str):
        self.text_path = cybok_text_path
        self.raw_text = ""
        self.chapters = {}
        self.entities = {}       # name -> {id, name, type, category, description}
        self.triples = []        # [(e1, relation, e2)]
        self.entity_counter = 2000  # Start after existing IDs

        # Build combined entity dictionary for recognition
        self.known_entities = {}
        self.known_entities.update(TOOL_ENTITIES)
        self.known_entities.update(ATTACK_ENTITIES)
        self.known_entities.update(CONCEPT_ENTITIES)
        self.known_entities.update(STANDARD_ENTITIES)
        self.known_entities.update(ALGORITHM_ENTITIES)

    def load_text(self):
        """Load the full extracted text."""
        with open(self.text_path, 'r', encoding='utf-8', errors='replace') as f:
            self.raw_text = f.read()
        print(f"Loaded {len(self.raw_text)} characters of CyBOK text")

    def parse_chapters(self):
        """Split text into chapters based on CyBOK Knowledge Areas."""
        # CyBOK chapters are numbered and titled
        chapter_pattern = re.compile(
            r'\n(\d{1,2})\s+([\w\s,&:]+?)\n',
            re.MULTILINE
        )

        matches = list(chapter_pattern.finditer(self.raw_text))
        print(f"Found {len(matches)} potential chapter headers")

        # Use the known KA names to identify real chapters
        ka_keywords = set()
        for ka_name in CYBOK_KNOWLEDGE_AREAS.keys():
            for word in ka_name.lower().split():
                if len(word) > 3:
                    ka_keywords.add(word)

        # Split text into chunks based on page markers
        # For simplicity, process the entire text as one document
        # but tag sections by which KA they belong to
        self.chapters["full_text"] = self.raw_text
        print("Text loaded for processing")

    def extract_entities_from_text(self):
        """Extract entities that appear in the CyBOK text."""
        text_lower = self.raw_text.lower()
        found_count = 0

        # Search for known entities in the text
        for entity_name, (etype, ecat) in self.known_entities.items():
            # Check if entity appears in text (case-insensitive)
            search_term = entity_name.lower()
            if search_term in text_lower:
                # Count occurrences to gauge importance
                count = text_lower.count(search_term)
                if count >= 2:  # Must appear at least twice
                    self._add_entity(entity_name, etype, ecat,
                                     f"CyBOK: {entity_name} (mentioned {count} times)")
                    found_count += 1

        print(f"Found {found_count} known entities in CyBOK text")

        # Extract additional entities from CyBOK using patterns
        self._extract_additional_entities()

    def _add_entity(self, name: str, etype: str, category: str, description: str = ""):
        """Add entity to the collection if not already present."""
        if name not in self.entities:
            self.entity_counter += 1
            self.entities[name] = {
                'id': self.entity_counter,
                'name': name,
                'type': etype,
                'category': category,
                'description': description,
                'source': 'CyBOK'
            }

    def _extract_additional_entities(self):
        """Extract entities not in our predefined dictionaries."""
        # Extract capitalized multi-word terms that appear frequently
        # These are likely cybersecurity concepts
        pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
        term_counts = defaultdict(int)

        for match in pattern.finditer(self.raw_text):
            term = match.group(1)
            if 3 <= len(term.split()) <= 4:
                term_counts[term] += 1

        # Filter for terms that appear at least 5 times (significant concepts)
        security_keywords = {'security', 'attack', 'threat', 'vulnerability', 'risk',
                             'encryption', 'authentication', 'access', 'control', 'network',
                             'malware', 'protocol', 'privacy', 'forensic', 'intrusion',
                             'exploit', 'defense', 'defence', 'cipher', 'key', 'certificate',
                             'hash', 'firewall', 'policy', 'audit', 'compliance', 'patch',
                             'phishing', 'injection', 'overflow', 'crypto', 'digital'}

        new_entities = 0
        for term, count in term_counts.items():
            if count >= 5:
                term_lower = term.lower()
                # Check if any word in the term is security-related
                words = set(term_lower.split())
                if words & security_keywords:
                    if term not in self.entities:
                        self._add_entity(term, "concept", "cybok_concept",
                                         f"CyBOK concept (mentioned {count} times)")
                        new_entities += 1

        # Also extract acronyms defined in text (e.g., "Advanced Persistent Threat (APT)")
        acronym_pattern = re.compile(r'(\b[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)\s*\(([A-Z]{2,6})\)')
        for match in acronym_pattern.finditer(self.raw_text):
            full_name = match.group(1)
            acronym = match.group(2)
            full_lower = full_name.lower()
            if any(kw in full_lower for kw in security_keywords):
                if full_name not in self.entities:
                    self._add_entity(full_name, "concept", "cybok_concept",
                                     f"CyBOK: {full_name} ({acronym})")
                    new_entities += 1
                if acronym not in self.entities and len(acronym) >= 2:
                    self._add_entity(acronym, "concept", "cybok_concept",
                                     f"CyBOK: {acronym} = {full_name}")
                    new_entities += 1

        print(f"Extracted {new_entities} additional entities from CyBOK patterns")

    def extract_triples_from_text(self):
        """Extract relationship triples from the text."""
        entity_names = set(self.entities.keys())
        entity_names_lower = {n.lower(): n for n in entity_names}

        # Method 1: Pattern-based extraction on sentences containing known entities
        sentences = re.split(r'[.!?]\s+', self.raw_text)
        pattern_triples = 0

        for sentence in sentences:
            if len(sentence) > 300 or len(sentence) < 10:
                continue

            sent_lower = sentence.lower()

            # Find which entities appear in this sentence
            entities_in_sentence = []
            for ename_lower, ename_orig in entity_names_lower.items():
                if len(ename_lower) > 2 and ename_lower in sent_lower:
                    entities_in_sentence.append(ename_orig)

            if len(entities_in_sentence) < 1:
                continue

            # Try relation patterns
            for pattern_str, relation in RELATION_PATTERNS:
                try:
                    matches = re.finditer(pattern_str, sentence, re.IGNORECASE)
                    for match in matches:
                        subj = match.group(1).strip()
                        obj = match.group(2).strip()

                        # Check if subject or object matches a known entity
                        subj_match = self._match_entity(subj, entity_names_lower)
                        obj_match = self._match_entity(obj, entity_names_lower)

                        if subj_match and obj_match and subj_match != obj_match:
                            triple = (subj_match, relation, obj_match)
                            if triple not in self.triples:
                                self.triples.append(triple)
                                pattern_triples += 1
                except re.error:
                    continue

        print(f"Extracted {pattern_triples} triples via pattern matching")

        # Method 2: Co-occurrence based triples from CyBOK structure
        # If two entities appear in the same paragraph, infer a relationship
        cooccurrence_triples = self._extract_cooccurrence_triples(entity_names_lower)
        print(f"Extracted {cooccurrence_triples} triples via co-occurrence")

        # Method 3: KA-based triples (entities belonging to knowledge areas)
        ka_triples = self._extract_ka_triples()
        print(f"Extracted {ka_triples} triples from Knowledge Area structure")

    def _match_entity(self, text: str, entity_names_lower: dict) -> str:
        """Try to match text to a known entity."""
        text_lower = text.lower().strip()
        # Exact match
        if text_lower in entity_names_lower:
            return entity_names_lower[text_lower]
        # Substring match
        for ename_lower, ename_orig in entity_names_lower.items():
            if len(ename_lower) > 3 and ename_lower in text_lower:
                return ename_orig
            if len(text_lower) > 3 and text_lower in ename_lower:
                return ename_orig
        return None

    def _extract_cooccurrence_triples(self, entity_names_lower: dict) -> int:
        """Extract triples from entities co-occurring in paragraphs."""
        paragraphs = self.raw_text.split('\n\n')
        count = 0

        for para in paragraphs:
            if len(para) < 50 or len(para) > 2000:
                continue

            para_lower = para.lower()

            # Find entities in this paragraph
            entities_found = []
            for ename_lower, ename_orig in entity_names_lower.items():
                if len(ename_lower) > 2 and ename_lower in para_lower:
                    entities_found.append(ename_orig)

            if len(entities_found) < 2:
                continue

            # Deduplicate
            entities_found = list(set(entities_found))

            # For pairs of entities, determine relationship from context
            for i in range(len(entities_found)):
                for j in range(i + 1, min(len(entities_found), i + 4)):
                    e1, e2 = entities_found[i], entities_found[j]
                    if e1 == e2:
                        continue

                    relation = self._infer_relation(e1, e2, para_lower)
                    if relation:
                        triple = (e1, relation, e2)
                        if triple not in self.triples:
                            self.triples.append(triple)
                            count += 1

        return count

    def _infer_relation(self, e1: str, e2: str, context: str) -> str:
        """Infer the relationship between two entities based on their types and context."""
        e1_info = self.entities.get(e1, {})
        e2_info = self.entities.get(e2, {})
        e1_type = e1_info.get('type', '')
        e2_type = e2_info.get('type', '')

        # Tool -> Attack: can_detect
        if e1_type == 'tool' and e2_type == 'attack':
            return 'can_detect'
        if e2_type == 'tool' and e1_type == 'attack':
            return None  # Skip, will be captured in reverse

        # Attack -> concept (security property): can_harm
        if e1_type == 'attack' and e2_info.get('category') == 'security_property':
            return 'can_harm'

        # Tool -> concept: uses
        if e1_type == 'tool' and e2_type == 'concept':
            return 'uses'

        # Algorithm -> concept: implements
        if e1_type == 'algorithm' and e2_type == 'concept':
            return 'implements'

        # Concept -> concept: check context for keywords
        if 'protect' in context or 'defend' in context or 'mitigat' in context:
            return 'can_detect'
        if 'attack' in context or 'exploit' in context or 'compromise' in context:
            return 'can_exploit'
        if 'part of' in context or 'component' in context:
            return 'is_part_of'
        if 'type of' in context or 'form of' in context or 'kind of' in context:
            return 'is_a'
        if 'use' in context or 'employ' in context or 'implement' in context:
            return 'uses'

        # Default: has_a for related concepts
        return 'has_a'

    def _extract_ka_triples(self) -> int:
        """Generate triples mapping entities to CyBOK Knowledge Areas."""
        count = 0
        text_lower = self.raw_text.lower()

        for ka_name, ka_info in CYBOK_KNOWLEDGE_AREAS.items():
            # Add the KA itself as an entity
            self._add_entity(ka_name, "knowledge_area", ka_info["category"],
                             f"CyBOK Knowledge Area: {ka_name}")

            for topic in ka_info["topics"]:
                topic_lower = topic.lower()
                # Check if topic appears in text
                if topic_lower in text_lower:
                    # Find entities related to this topic
                    for ename, einfo in self.entities.items():
                        if ename == ka_name:
                            continue
                        ename_lower = ename.lower()
                        if topic_lower in ename_lower or ename_lower in topic_lower:
                            triple = (ename, "is_part_of", ka_name)
                            if triple not in self.triples:
                                self.triples.append(triple)
                                count += 1

            # Also create triples between KA and its category
            category_name = ka_info["category"].replace("_", " ").title()
            self._add_entity(category_name, "category", "cybok_category",
                             f"CyBOK Category: {category_name}")
            triple = (ka_name, "is_part_of", category_name)
            if triple not in self.triples:
                self.triples.append(triple)
                count += 1

        return count

    def generate_cybok_specific_triples(self):
        """Generate high-value triples based on CyBOK domain knowledge."""
        specific_triples = [
            # Saltzer & Schroeder Principles
            ("least privilege", "is_a", "security policy"),
            ("separation of duties", "is_a", "security policy"),
            ("defense in depth", "is_a", "security policy"),
            ("fail-safe defaults", "is_a", "security policy"),
            ("complete mediation", "is_a", "security policy"),
            ("open design", "is_a", "security policy"),
            ("economy of mechanism", "is_a", "security policy"),
            ("zero trust", "is_a", "security policy"),

            # CIA Triad
            ("confidentiality", "is_part_of", "CIA triad"),
            ("integrity", "is_part_of", "CIA triad"),
            ("availability", "is_part_of", "CIA triad"),

            # Crypto relationships
            ("AES", "implements", "symmetric encryption"),
            ("RSA", "implements", "asymmetric encryption"),
            ("SHA-256", "implements", "hash function"),
            ("SHA-1", "implements", "hash function"),
            ("MD5", "implements", "hash function"),
            ("Diffie-Hellman", "implements", "key management"),
            ("TLS", "uses", "encryption"),
            ("TLS", "uses", "certificate"),
            ("TLS", "uses", "digital signature"),
            ("HTTPS", "uses", "TLS"),
            ("IPsec", "uses", "encryption"),
            ("VPN", "uses", "IPsec"),
            ("VPN", "uses", "encryption"),
            ("PKI", "uses", "certificate"),
            ("PKI", "uses", "digital signature"),

            # Tool relationships
            ("Wireshark", "can_analyze", "network traffic"),
            ("Nmap", "can_analyze", "network"),
            ("Metasploit", "can_exploit", "vulnerability"),
            ("Nessus", "can_detect", "vulnerability"),
            ("OpenVAS", "can_detect", "vulnerability"),
            ("Snort", "can_detect", "intrusion detection"),
            ("Suricata", "can_detect", "intrusion detection"),
            ("Burp Suite", "can_analyze", "web security"),
            ("Volatility", "can_analyze", "memory forensics"),
            ("Autopsy", "can_analyze", "digital forensics"),
            ("YARA", "can_detect", "malware"),
            ("Ghidra", "can_analyze", "reverse engineering"),
            ("Splunk", "can_analyze", "log analysis"),
            ("OWASP ZAP", "can_detect", "web security"),
            ("John the Ripper", "can_exploit", "password"),
            ("Hashcat", "can_exploit", "password"),
            ("Aircrack-ng", "can_exploit", "wireless security"),
            ("Tor", "implements", "anonymity"),
            ("GnuPG", "implements", "encryption"),
            ("OpenSSL", "implements", "TLS"),

            # Attack -> target relationships
            ("SQL injection", "can_exploit", "web security"),
            ("XSS", "can_exploit", "web security"),
            ("CSRF", "can_exploit", "web security"),
            ("buffer overflow", "can_exploit", "software security"),
            ("phishing", "can_harm", "authentication"),
            ("DDoS", "can_harm", "availability"),
            ("man-in-the-middle", "can_harm", "confidentiality"),
            ("ransomware", "can_harm", "availability"),
            ("rootkit", "can_harm", "integrity"),
            ("social engineering", "can_exploit", "human factors"),
            ("privilege escalation", "can_harm", "access control"),
            ("brute force", "can_exploit", "authentication"),
            ("replay attack", "can_exploit", "authentication"),
            ("side-channel attack", "can_exploit", "encryption"),
            ("spoofing", "can_harm", "authentication"),
            ("ARP spoofing", "can_exploit", "network"),
            ("DNS spoofing", "can_exploit", "network"),
            ("insider threat", "can_harm", "confidentiality"),
            ("supply chain attack", "can_harm", "integrity"),
            ("zero-day", "can_exploit", "vulnerability"),
            ("advanced persistent threat", "uses", "social engineering"),
            ("advanced persistent threat", "uses", "zero-day"),
            ("botnet", "can_harm", "availability"),
            ("keylogger", "can_harm", "confidentiality"),

            # Defense mechanisms
            ("firewall", "can_detect", "network attacks"),
            ("IDS", "can_detect", "intrusion detection"),
            ("IPS", "can_detect", "intrusion prevention"),
            ("SIEM", "can_analyze", "log analysis"),
            ("SOC", "uses", "SIEM"),
            ("access control", "can_detect", "privilege escalation"),
            ("encryption", "can_detect", "eavesdropping"),
            ("multi-factor authentication", "can_detect", "phishing"),
            ("sandboxing", "can_detect", "malware"),
            ("network segmentation", "can_detect", "lateral movement"),

            # Standards/frameworks
            ("NIST", "has_a", "NIST CSF"),
            ("OWASP Top 10", "can_detect", "web security"),
            ("MITRE ATT&CK", "can_analyze", "adversarial behavior"),
            ("CVE", "can_analyze", "vulnerability"),
            ("CVSS", "can_analyze", "vulnerability"),
            ("ISO 27001", "implements", "security governance"),
            ("GDPR", "implements", "privacy"),
            ("PCI DSS", "implements", "security policy"),
            ("Common Criteria", "can_analyze", "security evaluation"),
            ("Cyber Kill Chain", "can_analyze", "attack lifecycle"),

            # Forensics
            ("digital forensics", "can_analyze", "evidence"),
            ("memory forensics", "is_part_of", "digital forensics"),
            ("network forensics", "is_part_of", "digital forensics"),
            ("disk forensics", "is_part_of", "digital forensics"),
            ("incident response", "uses", "digital forensics"),

            # Methodology relationships
            ("threat modeling", "uses", "STRIDE"),
            ("penetration testing", "uses", "Metasploit"),
            ("penetration testing", "uses", "Nmap"),
            ("penetration testing", "uses", "Burp Suite"),
            ("vulnerability scanning", "uses", "Nessus"),
            ("vulnerability scanning", "uses", "OpenVAS"),
            ("malware analysis", "uses", "YARA"),
            ("malware analysis", "uses", "Cuckoo Sandbox"),
            ("reverse engineering", "uses", "Ghidra"),
            ("code review", "is_part_of", "secure coding"),
            ("DevSecOps", "uses", "secure coding"),

            # Access control models
            ("RBAC", "is_a", "access control"),
            ("ABAC", "is_a", "access control"),
            ("MAC", "is_a", "access control"),
            ("DAC", "is_a", "access control"),

            # Authentication
            ("OAuth", "implements", "authorization"),
            ("SAML", "implements", "authentication"),
            ("Kerberos", "implements", "authentication"),
            ("single sign-on", "uses", "SAML"),
        ]

        # Add entity for any mentioned in triples but not yet registered
        for e1, r, e2 in specific_triples:
            if e1 not in self.entities:
                self._add_entity(e1, "concept", "cybok_concept", f"CyBOK: {e1}")
            if e2 not in self.entities:
                self._add_entity(e2, "concept", "cybok_concept", f"CyBOK: {e2}")
            if (e1, r, e2) not in self.triples:
                self.triples.append((e1, r, e2))

        print(f"Added {len(specific_triples)} curated CyBOK-specific triples")

    def merge_with_existing_kg(self):
        """Merge extracted CyBOK data with existing AISecKG data."""
        kg_path = PROJECT_ROOT / "data" / "knowledge_graph"

        # Load existing entities
        existing_entities = {}
        existing_entity_names = set()
        max_id = 0
        with open(kg_path / "all_entity_info.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                eid = int(row['entityID'])
                existing_entities[eid] = row
                existing_entity_names.add(row['entityName'].lower())
                max_id = max(max_id, eid)

        # Load existing triples
        existing_triples = set()
        with open(kg_path / "all_triples.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_triples.add((row['e1'].strip(), row['r'].strip(), row['e2'].strip()))

        # Load existing relations
        existing_relations = set()
        with open(kg_path / "all_relation_info.csv", 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                existing_relations.add(row[0].strip())

        print(f"\nExisting KG: {len(existing_entities)} entities, {len(existing_triples)} triples, {len(existing_relations)} relations")

        # Merge new entities
        new_entity_count = 0
        new_id = max_id + 1
        merged_entities = dict(existing_entities)

        for ename, einfo in self.entities.items():
            if ename.lower() not in existing_entity_names:
                merged_entities[new_id] = {
                    'entityID': new_id,
                    'entityName': ename,
                    'entityType': einfo['type'],
                    'entityCategory': einfo['category'],
                    'entityDescription': einfo.get('description', '')
                }
                existing_entity_names.add(ename.lower())
                new_id += 1
                new_entity_count += 1

        # Merge new triples
        new_triple_count = 0
        merged_triples = list(existing_triples)
        for triple in self.triples:
            if triple not in existing_triples:
                merged_triples.append(triple)
                existing_triples.add(triple)
                new_triple_count += 1

        # Merge relations
        for triple in self.triples:
            existing_relations.add(triple[1])

        # Write merged entity file
        output_path = kg_path
        with open(output_path / "all_entity_info.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entityID', 'entityName', 'entityType', 'entityCategory', 'entityDescription'])
            for eid in sorted(merged_entities.keys()):
                e = merged_entities[eid]
                writer.writerow([
                    e.get('entityID', eid),
                    e.get('entityName', ''),
                    e.get('entityType', ''),
                    e.get('entityCategory', ''),
                    e.get('entityDescription', '')
                ])

        # Write merged triples file
        with open(output_path / "all_triples.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['e1', 'r', 'e2'])
            for e1, r, e2 in merged_triples:
                writer.writerow([e1, r, e2])

        # Write merged relations file
        with open(output_path / "all_relation_info.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['relation'])
            for rel in sorted(existing_relations):
                writer.writerow([rel])

        print(f"\nMerge results:")
        print(f"  New entities added: {new_entity_count}")
        print(f"  New triples added:  {new_triple_count}")
        print(f"  Total entities:     {len(merged_entities)}")
        print(f"  Total triples:      {len(merged_triples)}")
        print(f"  Total relations:    {len(existing_relations)}")

        return {
            'new_entities': new_entity_count,
            'new_triples': new_triple_count,
            'total_entities': len(merged_entities),
            'total_triples': len(merged_triples),
            'total_relations': len(existing_relations)
        }

    def run(self):
        """Run the full extraction pipeline."""
        print("=" * 60)
        print("CyBOK Knowledge Extraction Pipeline")
        print("=" * 60)

        print("\n[1/5] Loading CyBOK text...")
        self.load_text()

        print("\n[2/5] Parsing chapter structure...")
        self.parse_chapters()

        print("\n[3/5] Extracting entities...")
        self.extract_entities_from_text()

        print("\n[4/5] Extracting relationship triples...")
        self.extract_triples_from_text()

        print("\n[4b/5] Adding curated CyBOK-specific triples...")
        self.generate_cybok_specific_triples()

        print("\n[5/5] Merging with existing AISecKG knowledge graph...")
        stats = self.merge_with_existing_kg()

        print("\n" + "=" * 60)
        print("Extraction complete!")
        print("=" * 60)

        return stats


def main():
    import argparse

    default_txt = PROJECT_ROOT / "data" / "cybok" / "cybok_full_text.txt"
    p = argparse.ArgumentParser(description="Extract CyBOK triples and merge into data/knowledge_graph CSVs.")
    p.add_argument(
        "cybok_text",
        nargs="?",
        default=str(default_txt),
        help=f"Path to CyBOK plain text (default: {default_txt})",
    )
    p.add_argument("--no-rebuild", action="store_true", help="Skip NetworkX pickle/JSON rebuild after merge")
    args = p.parse_args()

    extractor = CyBOKExtractor(args.cybok_text)
    stats = extractor.run()

    if not args.no_rebuild:
        print("\n\nRebuilding knowledge graph...")
        from kg_builder import KnowledgeGraphBuilder

        kg = KnowledgeGraphBuilder()
        kg.build_graph()
        kg.save_graph()
        kg.export_to_json()
        print("Knowledge graph rebuilt and saved!")

    return stats


if __name__ == "__main__":
    main()
