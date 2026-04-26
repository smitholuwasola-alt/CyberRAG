"""
Strict Triple Quality Filter - Pass 2
Removes remaining noise from short acronyms and unanchored triples.
"""

import csv
import re
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent
KG_PATH = PROJECT_ROOT / "data" / "knowledge_graph"

# Known high-quality entity names (curated)
CURATED_ENTITIES = {
    # Tools
    'nmap', 'wireshark', 'snort', 'suricata', 'metasploit', 'burp suite', 'nessus',
    'openvas', 'nikto', 'john the ripper', 'hashcat', 'aircrack-ng', 'tcpdump',
    'netcat', 'volatility', 'autopsy', 'encase', 'ftk', 'splunk', 'elk stack',
    'ossec', 'zeek', 'pfsense', 'iptables', 'modsecurity', 'yara', 'ghidra',
    'ida pro', 'cuckoo sandbox', 'gnupg', 'openssl', 'tor', 'owasp zap',
    # Attacks
    'buffer overflow', 'sql injection', 'cross-site scripting', 'xss', 'csrf',
    'phishing', 'spear phishing', 'denial of service', 'ddos', 'man-in-the-middle',
    'privilege escalation', 'brute force', 'dictionary attack', 'rainbow table',
    'replay attack', 'side-channel attack', 'timing attack', 'spoofing',
    'arp spoofing', 'dns spoofing', 'ip spoofing', 'session hijacking',
    'rootkit', 'ransomware', 'trojan', 'worm', 'virus', 'botnet', 'keylogger',
    'spyware', 'backdoor', 'zero-day', 'exploit', 'social engineering',
    'supply chain attack', 'advanced persistent threat', 'apt', 'insider threat',
    'code injection', 'command injection', 'path traversal', 'race condition',
    'return-oriented programming', 'cache poisoning', 'bgp hijacking',
    'fault injection', 'clickjacking', 'watering hole',
    # Concepts
    'confidentiality', 'integrity', 'availability', 'authentication',
    'authorization', 'accountability', 'non-repudiation', 'access control',
    'encryption', 'decryption', 'hashing', 'digital signature', 'certificate',
    'pki', 'tls', 'ssl', 'https', 'ipsec', 'vpn', 'firewall', 'ids', 'ips',
    'siem', 'soc', 'threat modeling', 'risk assessment', 'penetration testing',
    'vulnerability scanning', 'incident response', 'digital forensics',
    'malware analysis', 'reverse engineering', 'secure coding', 'code review',
    'defense in depth', 'least privilege', 'separation of duties', 'zero trust',
    'fail-safe defaults', 'complete mediation', 'open design',
    'economy of mechanism', 'rbac', 'abac', 'mac', 'dac',
    'multi-factor authentication', 'single sign-on', 'oauth', 'saml',
    'sandboxing', 'containerization', 'virtualization', 'network segmentation',
    'data loss prevention', 'intrusion detection', 'intrusion prevention',
    'security awareness', 'security policy', 'security governance',
    'business continuity', 'disaster recovery', 'privacy', 'anonymity',
    'key management', 'symmetric encryption', 'asymmetric encryption',
    'hash function', 'blockchain', 'secure boot', 'tpm', 'hsm', 'scada',
    'iot', 'cloud security', 'devsecops', 'memory forensics',
    'network forensics', 'disk forensics', 'web security', 'mobile security',
    # Standards
    'nist', 'iso 27001', 'iso 27002', 'gdpr', 'owasp top 10', 'mitre att&ck',
    'cve', 'cvss', 'cis controls', 'nist csf', 'pci dss', 'hipaa',
    'common criteria', 'fips', 'cyber kill chain', 'stride', 'dread',
    'octave', 'fair',
    # Algorithms
    'aes', 'rsa', 'sha-256', 'sha-1', 'md5', 'des', '3des', 'blowfish',
    'diffie-hellman', 'elliptic curve', 'hmac', 'kerberos', 'radius', 'ldap',
    # CyBOK Knowledge Areas
    'risk management and governance', 'law and regulation', 'human factors',
    'privacy and online rights', 'malware and attack technologies',
    'adversarial behaviours', 'security operations and incident management',
    'forensics', 'cryptography', 'applied cryptography',
    'operating systems and virtualisation security',
    'distributed systems security', 'formal methods for security',
    'authentication, authorisation and accountability', 'software security',
    'web and mobile security', 'secure software lifecycle', 'network security',
    'hardware security', 'cyber-physical systems security',
    'physical layer and telecommunications security',
    # Additional important CyBOK concepts
    'network traffic', 'network attacks', 'packet', 'protocol',
    'tcp', 'udp', 'http', 'dns', 'bgp', 'icmp',
    'public key', 'private key', 'session', 'cookie',
    'password', 'token', 'biometrics',
    'log analysis', 'monitoring', 'alerting', 'triage', 'containment',
    'evidence', 'chain of custody', 'timeline analysis',
    'threat intelligence', 'vulnerability', 'risk', 'threat',
    'cia triad', 'attack lifecycle', 'adversarial behavior',
    'security evaluation', 'lateral movement', 'eavesdropping',
    'human factors', 'wireless security', 'cellular security',
    'software security', 'hardware security',
    'network behavior', 'traffic', 'data flow',
}

# Noisy short acronyms that match too broadly in CyBOK text
NOISY_ACRONYMS = {
    'can', 'pan', 'lan', 'wan', 'nat', 'rat', 'esp', 'isa', 'sdl',
    'acc', 'ike', 'dsa', 'nis', 'owe', 'ppp', 'cti', 'sent',
    'flag', 'set', 'run', 'get', 'put', 'del', 'new', 'old',
    'key', 'log', 'bit', 'tag', 'end', 'raw', 'use',
}


def run_strict_filter():
    print("=" * 60)
    print("Strict Triple Quality Filter (Pass 2)")
    print("=" * 60)

    # Load triples
    triples = []
    with open(KG_PATH / "all_triples.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            triples.append((row['e1'].strip(), row['r'].strip(), row['e2'].strip()))
    print(f"Input triples: {len(triples)}")

    # Load entities
    entities = {}
    with open(KG_PATH / "all_entity_info.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities[row['entityName'].strip().lower()] = row

    # Filter
    filtered = []
    removed = Counter()

    for e1, r, e2 in triples:
        e1_lower = e1.lower().strip()
        e2_lower = e2.lower().strip()

        # Remove triples with noisy short acronyms
        if e1_lower in NOISY_ACRONYMS or e2_lower in NOISY_ACRONYMS:
            removed['noisy_acronym'] += 1
            continue

        # Remove very short entities (1-2 chars) unless they're known
        if (len(e1_lower) <= 2 and e1_lower not in CURATED_ENTITIES) or \
           (len(e2_lower) <= 2 and e2_lower not in CURATED_ENTITIES):
            removed['too_short'] += 1
            continue

        # Remove triples with sentence fragments (contain certain patterns)
        if any(x in e1_lower for x in ['such as', 'leads to', 'based on', 'point it']) or \
           any(x in e2_lower for x in ['such as', 'leads to', 'based on', 'point it']):
            removed['sentence_fragment'] += 1
            continue

        # Remove triples where both entities are unknown AND neither is curated
        e1_curated = e1_lower in CURATED_ENTITIES
        e2_curated = e2_lower in CURATED_ENTITIES
        e1_known = e1_lower in entities
        e2_known = e2_lower in entities

        # At least one entity must be either curated or a known entity with length > 3
        if not e1_curated and not e2_curated:
            if not (e1_known and len(e1_lower) > 4) and not (e2_known and len(e2_lower) > 4):
                removed['unanchored'] += 1
                continue

        # Entities that are just "Based X" patterns
        if re.match(r'^based\s', e1_lower) or re.match(r'^based\s', e2_lower):
            removed['based_pattern'] += 1
            continue

        filtered.append((e1, r, e2))

    print(f"After strict filter: {len(filtered)}")
    print(f"Removed: {dict(removed)}")

    # Deduplicate
    seen = set()
    deduped = []
    for e1, r, e2 in filtered:
        key = (e1.lower(), r.lower(), e2.lower())
        if key not in seen:
            seen.add(key)
            deduped.append((e1, r, e2))
    print(f"After final dedup: {len(deduped)}")

    # Write cleaned triples
    with open(KG_PATH / "all_triples.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['e1', 'r', 'e2'])
        for e1, r, e2 in deduped:
            writer.writerow([e1, r, e2])

    # Clean entity list to remove entities no longer referenced
    referenced = set()
    for e1, r, e2 in deduped:
        referenced.add(e1.lower())
        referenced.add(e2.lower())

    clean_entities = {k: v for k, v in entities.items()
                      if k in referenced or k in CURATED_ENTITIES}

    # Also add any referenced entities not yet in the list
    max_id = max(int(v['entityID']) for v in clean_entities.values()) if clean_entities else 0
    for e1, r, e2 in deduped:
        for ename in [e1, e2]:
            if ename.lower() not in clean_entities:
                max_id += 1
                clean_entities[ename.lower()] = {
                    'entityID': max_id,
                    'entityName': ename,
                    'entityType': 'concept',
                    'entityCategory': 'cybok_concept',
                    'entityDescription': ''
                }

    with open(KG_PATH / "all_entity_info.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['entityID', 'entityName', 'entityType', 'entityCategory', 'entityDescription'])
        for ename in sorted(clean_entities.keys()):
            e = clean_entities[ename]
            writer.writerow([e['entityID'], e['entityName'], e['entityType'],
                             e['entityCategory'], e.get('entityDescription', '')])

    print(f"\nFinal entity count: {len(clean_entities)}")

    # Relation distribution
    rel_dist = Counter(t[1] for t in deduped)
    print(f"\nRelation distribution:")
    for r, c in rel_dist.most_common():
        print(f"  {r}: {c}")

    # Print quality samples
    print(f"\n=== Quality Check Samples ===")
    import random
    random.seed(42)
    samples = random.sample(deduped, min(30, len(deduped)))
    for e1, r, e2 in sorted(samples, key=lambda x: x[1]):
        print(f"  {e1} --[{r}]--> {e2}")

    return len(clean_entities), len(deduped)


if __name__ == "__main__":
    run_strict_filter()

    # Rebuild KG
    print("\n\nRebuilding knowledge graph...")
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from kg_builder import KnowledgeGraphBuilder

    kg = KnowledgeGraphBuilder()
    kg.build_graph()
    kg.save_graph()
    kg.export_to_json()
    print("Done!")
