"""
Triple Quality Filter
Cleans noisy triples from the CyBOK extraction and rebuilds a high-quality KG.
"""

import csv
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
KG_PATH = PROJECT_ROOT / "data" / "knowledge_graph"


def load_entities():
    """Load entity names for validation."""
    entities = {}
    with open(KG_PATH / "all_entity_info.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities[row['entityName'].strip().lower()] = row
    return entities


def is_valid_entity_name(name: str) -> bool:
    """Check if an entity name is well-formed."""
    name = name.strip()
    # Too short or too long
    if len(name) < 2 or len(name) > 60:
        return False
    # Contains newlines (captured sentence fragments)
    if '\n' in name or '\r' in name:
        return False
    # Starts with lowercase common words (likely sentence fragments)
    fragment_starts = ['the ', 'a ', 'an ', 'this ', 'that ', 'these ', 'those ',
                       'such ', 'some ', 'any ', 'at ', 'in ', 'on ', 'for ',
                       'of ', 'to ', 'by ', 'with ', 'from ', 'and ', 'or ',
                       'but ', 'if ', 'when ', 'while ', 'as ', 'it ', 'its ',
                       'they ', 'we ', 'he ', 'she ']
    name_lower = name.lower()
    for start in fragment_starts:
        if name_lower.startswith(start):
            return False
    # Contains special characters (not a clean entity)
    if re.search(r'[{}()\[\]<>@#$%^&*+=|\\~`]', name):
        return False
    # More than 5 words (likely a sentence fragment)
    if len(name.split()) > 5:
        return False
    # All uppercase single char
    if len(name) == 1:
        return False
    return True


def is_valid_triple(e1: str, rel: str, e2: str, valid_relations: set) -> bool:
    """Check if a triple is well-formed and meaningful."""
    e1 = e1.strip()
    e2 = e2.strip()
    rel = rel.strip()

    # Both entities must be valid names
    if not is_valid_entity_name(e1) or not is_valid_entity_name(e2):
        return False

    # No self-loops
    if e1.lower() == e2.lower():
        return False

    # Relation must be valid
    if rel not in valid_relations:
        return False

    return True


def compute_entity_importance(triples, entities):
    """Score entities by how connected they are."""
    mention_count = Counter()
    for e1, r, e2 in triples:
        mention_count[e1.lower()] += 1
        mention_count[e2.lower()] += 1
    return mention_count


def filter_and_deduplicate():
    """Main filtering pipeline."""
    print("=" * 60)
    print("Triple Quality Filter")
    print("=" * 60)

    # Load current data
    entities = load_entities()
    print(f"Loaded {len(entities)} entities")

    valid_relations = set()
    with open(KG_PATH / "all_relation_info.csv", 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            valid_relations.add(row[0].strip())
    print(f"Valid relations: {valid_relations}")

    # Load all triples
    all_triples = []
    with open(KG_PATH / "all_triples.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_triples.append((row['e1'].strip(), row['r'].strip(), row['e2'].strip()))
    print(f"Total triples before filtering: {len(all_triples)}")

    # Step 1: Basic quality filter
    clean_triples = []
    removed_reasons = Counter()
    for e1, r, e2 in all_triples:
        if not is_valid_entity_name(e1):
            removed_reasons['bad_e1_name'] += 1
            continue
        if not is_valid_entity_name(e2):
            removed_reasons['bad_e2_name'] += 1
            continue
        if e1.lower() == e2.lower():
            removed_reasons['self_loop'] += 1
            continue
        if r not in valid_relations:
            removed_reasons['bad_relation'] += 1
            continue
        clean_triples.append((e1, r, e2))

    print(f"\nAfter basic quality filter: {len(clean_triples)}")
    print(f"Removed: {dict(removed_reasons)}")

    # Step 2: Deduplicate (case-insensitive)
    seen = set()
    deduped_triples = []
    for e1, r, e2 in clean_triples:
        key = (e1.lower(), r.lower(), e2.lower())
        if key not in seen:
            seen.add(key)
            deduped_triples.append((e1, r, e2))

    print(f"After deduplication: {len(deduped_triples)}")

    # Step 3: Normalize entity names (prefer canonical forms from entity list)
    canonical_map = {}
    for ename_lower, edata in entities.items():
        canonical_map[ename_lower] = edata['entityName']

    normalized_triples = []
    for e1, r, e2 in deduped_triples:
        e1_norm = canonical_map.get(e1.lower(), e1)
        e2_norm = canonical_map.get(e2.lower(), e2)
        normalized_triples.append((e1_norm, r, e2_norm))

    # Deduplicate again after normalization
    seen = set()
    final_triples = []
    for e1, r, e2 in normalized_triples:
        key = (e1.lower(), r.lower(), e2.lower())
        if key not in seen:
            seen.add(key)
            final_triples.append((e1, r, e2))

    print(f"After normalization + dedup: {len(final_triples)}")

    # Step 4: Remove triples where entities are not in the entity list
    # (only for entities with very generic/short names that could be false positives)
    # Keep triples where at least one entity is a known entity
    known_entity_names = set(entities.keys())
    verified_triples = []
    for e1, r, e2 in final_triples:
        e1_known = e1.lower() in known_entity_names
        e2_known = e2.lower() in known_entity_names
        # Keep if at least one entity is known, or both are reasonably named
        if e1_known or e2_known:
            verified_triples.append((e1, r, e2))
        elif len(e1) > 3 and len(e2) > 3:
            verified_triples.append((e1, r, e2))

    print(f"After entity verification: {len(verified_triples)}")

    # Step 5: Clean up entity list (remove entities with bad names)
    clean_entities = {}
    referenced_entities = set()
    for e1, r, e2 in verified_triples:
        referenced_entities.add(e1.lower())
        referenced_entities.add(e2.lower())

    removed_entities = 0
    for ename_lower, edata in entities.items():
        if is_valid_entity_name(edata['entityName']):
            clean_entities[ename_lower] = edata
        else:
            removed_entities += 1

    print(f"Removed {removed_entities} malformed entity names")

    # Add any entities referenced in triples but missing from entity list
    max_id = max(int(e['entityID']) for e in clean_entities.values())
    for e1, r, e2 in verified_triples:
        for ename in [e1, e2]:
            if ename.lower() not in clean_entities:
                max_id += 1
                clean_entities[ename.lower()] = {
                    'entityID': max_id,
                    'entityName': ename,
                    'entityType': 'concept',
                    'entityCategory': 'cybok_concept',
                    'entityDescription': f'Extracted from CyBOK knowledge base'
                }

    # Write cleaned files
    print("\nWriting cleaned files...")

    # Write entities
    with open(KG_PATH / "all_entity_info.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['entityID', 'entityName', 'entityType', 'entityCategory', 'entityDescription'])
        for ename in sorted(clean_entities.keys()):
            e = clean_entities[ename]
            writer.writerow([e['entityID'], e['entityName'], e['entityType'],
                             e['entityCategory'], e.get('entityDescription', '')])

    # Write triples
    with open(KG_PATH / "all_triples.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['e1', 'r', 'e2'])
        for e1, r, e2 in verified_triples:
            writer.writerow([e1, r, e2])

    # Relations stay the same
    print(f"\nFinal counts:")
    print(f"  Entities: {len(clean_entities)}")
    print(f"  Triples:  {len(verified_triples)}")

    # Print relation distribution
    rel_dist = Counter(t[1] for t in verified_triples)
    print(f"\n  Relation distribution:")
    for r, c in rel_dist.most_common():
        print(f"    {r}: {c}")

    # Sample some triples to verify quality
    print(f"\n=== Sample Cleaned Triples ===")
    import random
    random.seed(42)
    samples = random.sample(verified_triples, min(25, len(verified_triples)))
    for e1, r, e2 in samples:
        print(f"  {e1} --[{r}]--> {e2}")

    return len(clean_entities), len(verified_triples)


if __name__ == "__main__":
    filter_and_deduplicate()

    # Rebuild KG
    print("\n\nRebuilding knowledge graph from cleaned data...")
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from kg_builder import KnowledgeGraphBuilder

    kg = KnowledgeGraphBuilder()
    kg.build_graph()
    kg.save_graph()
    kg.export_to_json()
    print("Knowledge graph rebuilt successfully!")
