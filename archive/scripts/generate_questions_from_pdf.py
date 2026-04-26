"""
Generate Questions from PDF Content
Creates questions based on the information in the PDF document
"""

import re
import json
import csv
from pathlib import Path
from typing import List, Dict

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False
        print("No PDF library available. Install pdfplumber: pip install pdfplumber")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF"""
    if PDFPLUMBER_AVAILABLE:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    elif PYPDF2_AVAILABLE:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    else:
        raise ImportError("No PDF library available")


def generate_questions_from_text(text: str) -> List[Dict]:
    """
    Generate questions based on the content of the text
    Analyzes key concepts, definitions, processes, and information to create questions
    """
    questions = []
    question_number = 0
    
    # Split text into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Key patterns to identify important information
    definition_patterns = [
        r'(\w+(?:\s+\w+)*)\s+is\s+(?:a|an|the)\s+([^.!?]+)',
        r'(\w+(?:\s+\w+)*)\s+refers\s+to\s+([^.!?]+)',
        r'(\w+(?:\s+\w+)*)\s+means\s+([^.!?]+)',
        r'(\w+(?:\s+\w+)*)\s+involves\s+([^.!?]+)',
    ]
    
    # Process patterns
    process_patterns = [
        r'steps?\s+(?:to|for|in)\s+([^.!?]+)',
        r'process\s+(?:of|for)\s+([^.!?]+)',
        r'components?\s+(?:of|in)\s+([^.!?]+)',
        r'features?\s+(?:of|in)\s+([^.!?]+)',
    ]
    
    # List patterns
    list_patterns = [
        r'•\s+([^•\n]+)',
        r'-\s+([^\n]+)',
        r'\d+[\.\)]\s+([^\n]+)',
    ]
    
    seen_questions = set()
    
    for para in paragraphs:
        para = para.strip()
        if len(para) < 50:  # Skip very short paragraphs
            continue
        
        # Clean paragraph
        para = re.sub(r'\s+', ' ', para)
        
        # Generate definition questions
        for pattern in definition_patterns:
            matches = re.finditer(pattern, para, re.IGNORECASE)
            for match in matches:
                subject = match.group(1).strip()
                definition = match.group(2).strip()
                
                # Skip if too short or too long
                if len(subject) < 3 or len(subject) > 50 or len(definition) < 10:
                    continue
                
                # Skip common words and invalid subjects
                invalid_words = ['it', 'this', 'that', 'these', 'those', 'they', 'we', 'you', 'one', 'which', 'what', 'how', 'why', 'when', 'where', 'who']
                if subject.lower().split()[0] in invalid_words:
                    continue
                
                # Skip if subject is just an adjective or adverb
                if len(subject.split()) == 1 and subject.lower() in ['equally', 'important', 'critical', 'essential', 'necessary', 'effective']:
                    continue
                
                # Skip if subject contains question words
                if any(word in subject.lower() for word in ['what', 'which', 'how', 'why', 'when', 'where', 'who']):
                    continue
                
                # Generate question
                question = f"What is {subject}?"
                key = question.lower()
                
                if key not in seen_questions:
                    seen_questions.add(key)
                    question_number += 1
                    questions.append({
                        'question_number': question_number,
                        'question': question,
                        'options': [],
                        'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                    })
        
        # Generate "What are the..." questions for lists
        if '•' in para or re.search(r'\d+[\.\)]\s+', para):
            # Check for list indicators
            if any(word in para.lower() for word in ['components', 'steps', 'features', 'benefits', 'risks', 'types', 'examples', 'categories']):
                list_word = None
                for word in ['components', 'steps', 'features', 'benefits', 'risks', 'types', 'examples', 'categories']:
                    if word in para.lower():
                        list_word = word
                        break
                
                if list_word:
                    # Try to find the subject
                    subject_match = re.search(rf'(?:the|of|for)\s+([^.!?]+?)\s+{list_word}', para, re.IGNORECASE)
                    if subject_match:
                        subject = subject_match.group(1).strip()
                        if len(subject) > 3 and len(subject) < 50:
                            question = f"What are the {list_word} of {subject}?"
                            key = question.lower()
                            
                            if key not in seen_questions:
                                seen_questions.add(key)
                                question_number += 1
                                questions.append({
                                    'question_number': question_number,
                                    'question': question,
                                    'options': [],
                                    'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                                })
        
        # Generate "How does..." questions for processes
        if any(word in para.lower() for word in ['process', 'work', 'function', 'operate', 'manage']):
            process_match = re.search(r'(\w+(?:\s+\w+)*)\s+(?:process|works?|functions?|operates?|manages?)', para, re.IGNORECASE)
            if process_match:
                subject = process_match.group(1).strip()
                if len(subject) > 3 and len(subject) < 50:
                    question = f"How does {subject} work?"
                    key = question.lower()
                    
                    if key not in seen_questions:
                        seen_questions.add(key)
                        question_number += 1
                        questions.append({
                            'question_number': question_number,
                            'question': question,
                            'options': [],
                            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                        })
        
        # Generate "Why..." questions for benefits/importance
        if any(word in para.lower() for word in ['important', 'critical', 'essential', 'benefit', 'advantage', 'necessary']):
            importance_match = re.search(r'(\w+(?:\s+\w+)*)\s+(?:is|are)\s+(?:important|critical|essential)', para, re.IGNORECASE)
            if importance_match:
                subject = importance_match.group(1).strip()
                if len(subject) > 3 and len(subject) < 50:
                    question = f"Why is {subject} important?"
                    key = question.lower()
                    
                    if key not in seen_questions:
                        seen_questions.add(key)
                        question_number += 1
                        questions.append({
                            'question_number': question_number,
                            'question': question,
                            'options': [],
                            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                        })
        
        # Generate "What are..." questions for categories/types
        if any(word in para.lower() for word in ['types', 'kinds', 'categories', 'forms', 'varieties']):
            types_match = re.search(r'(?:types|kinds|categories|forms|varieties)\s+of\s+([^.!?]+)', para, re.IGNORECASE)
            if types_match:
                subject = types_match.group(1).strip()
                if len(subject) > 3 and len(subject) < 50:
                    question = f"What are the types of {subject}?"
                    key = question.lower()
                    
                    if key not in seen_questions:
                        seen_questions.add(key)
                        question_number += 1
                        questions.append({
                            'question_number': question_number,
                            'question': question,
                            'options': [],
                            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                        })
    
    # Generate questions from key terms and concepts
    key_terms = [
        'risk management', 'compliance management', 'GRC', 'enterprise risk management',
        'cybersecurity', 'vulnerability', 'threat', 'compliance framework', 'regulatory compliance',
        'data privacy', 'GDPR', 'HIPAA', 'NIST', 'ISO 27001', 'endpoint security',
        'patch management', 'cyber insurance', 'risk assessment', 'compliance audit',
        'supply chain risk', 'shadow IT', 'zero trust', 'CISA KEV', 'SBOM'
    ]
    
    for term in key_terms:
        if term.lower() in text.lower():
            # Generate different types of questions
            question_types = [
                f"What is {term}?",
                f"How does {term} work?",
                f"Why is {term} important?",
                f"What are the benefits of {term}?",
            ]
            
            for question in question_types:
                key = question.lower()
                if key not in seen_questions:
                    seen_questions.add(key)
                    question_number += 1
                    questions.append({
                        'question_number': question_number,
                        'question': question,
                        'options': [],
                        'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                    })
    
    return questions


def clean_questions(questions: List[Dict]) -> List[Dict]:
    """Clean and deduplicate questions"""
    cleaned = []
    seen = set()
    
    invalid_patterns = [
        r'What is one of which\?',
        r'What is Equally important\?',
        r'What is The modern approach\?',
        r'What is many organizations',
        r'What is while IT',
        r'What is The only',
        r'What is \w+ \w+ \w+\?',  # Too many repeated words
    ]
    
    for q in questions:
        question_text = q['question'].strip()
        
        # Normalize for duplicate detection (remove extra spaces, lowercase)
        normalized = re.sub(r'\s+', ' ', question_text.lower().strip())
        
        # Skip duplicates
        if normalized in seen:
            continue
        seen.add(normalized)
        
        # Skip invalid patterns
        if any(re.search(pattern, question_text, re.IGNORECASE) for pattern in invalid_patterns):
            continue
        
        # Skip questions with invalid subjects
        if re.match(r'What is (one|which|what|how|why|when|where|who|the|a|an)\s+', question_text, re.IGNORECASE):
            continue
        
        # Fix questions with redundant text
        if 'What are the components of' in question_text:
            # Remove redundant text after the question mark pattern
            question_text = re.sub(r'(\w+\s+\w+\s+comprises\s+\w+)\?', '?', question_text, flags=re.IGNORECASE)
        
        # Fix "Why is Why..." patterns
        question_text = re.sub(r'Why is Why\s+', 'Why is ', question_text, flags=re.IGNORECASE)
        
        # Remove duplicate words in questions
        words = question_text.split()
        if len(words) > 2:
            # Check for consecutive duplicate words
            cleaned_words = []
            for i, word in enumerate(words):
                if i == 0 or word.lower() != words[i-1].lower():
                    cleaned_words.append(word)
            question_text = ' '.join(cleaned_words)
        
        # Skip if subject is too short or just an adjective
        match = re.match(r'What is (.+?)\?', question_text, re.IGNORECASE)
        if match:
            subject = match.group(1).strip()
            if len(subject.split()) == 1 and subject.lower() in ['equally', 'important', 'critical', 'essential']:
                continue
            if len(subject) < 4:
                continue
        
        # Clean up trailing spaces before ?
        question_text = re.sub(r'\s+\?', '?', question_text)
        
        # Ensure ends with ?
        if not question_text.endswith('?'):
            question_text += "?"
        
        # Skip if too short or too long
        if len(question_text) < 12 or len(question_text) > 150:
            continue
        
        # Skip if contains obvious errors
        if 'Microsoft Sentinel Microsoft Sentinel' in question_text:
            continue
        if question_text.count('?') > 1:
            continue
        
        cleaned.append({
            'question_number': len(cleaned) + 1,
            'question': question_text,
            'options': [],
            'source': q['source']
        })
    
    return cleaned


def save_questions(questions: List[Dict], output_dir: Path):
    """Save questions to files"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / "eb_ultimate_guide_questions.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {len(questions)} questions to {json_file}")
    
    csv_file = output_dir / "eb_ultimate_guide_questions.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if questions:
            fieldnames = ['question_number', 'question', 'options', 'source']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for q in questions:
                row = q.copy()
                row['options'] = ' | '.join(q['options'])
                writer.writerow(row)
    print(f"[OK] Saved {len(questions)} questions to {csv_file}")


def main():
    print("="*70)
    print("Question Generator from PDF Content - EB Ultimate Guide")
    print("="*70)
    
    # Find PDF
    pdf_files = list(PROJECT_ROOT.rglob("EB-Ultimate-guide*.pdf"))
    
    if not pdf_files:
        print("Error: PDF file not found!")
        return
    
    pdf_path = pdf_files[0]
    print(f"\nFound PDF: {pdf_path.name}")
    
    # Extract text
    print("\nExtracting text from PDF...")
    try:
        text = extract_text_from_pdf(str(pdf_path))
        print(f"[OK] Extracted {len(text)} characters of text")
    except Exception as e:
        print(f"[ERROR] Error extracting text: {e}")
        return
    
    # Generate questions
    print("\nGenerating questions from content...")
    questions = generate_questions_from_text(text)
    print(f"[OK] Generated {len(questions)} potential questions")
    
    # Clean questions
    print("\nCleaning and deduplicating questions...")
    cleaned_questions = clean_questions(questions)
    print(f"[OK] {len(cleaned_questions)} unique questions after cleaning")
    
    # Save
    output_dir = PROJECT_ROOT / "data" / "qa"
    print(f"\nSaving questions to {output_dir}...")
    save_questions(cleaned_questions, output_dir)
    
    # Summary
    print("\n" + "="*70)
    print("GENERATION SUMMARY")
    print("="*70)
    print(f"Total questions generated: {len(cleaned_questions)}")
    
    # Show sample questions
    print("\n" + "="*70)
    print("SAMPLE QUESTIONS (first 20):")
    print("="*70)
    for i, q in enumerate(cleaned_questions[:20], 1):
        try:
            question_text = q['question'].encode('ascii', 'ignore').decode('ascii')
            print(f"{i}. {question_text}")
        except:
            print(f"{i}. [Question {i}]")
    
    if len(cleaned_questions) > 20:
        print(f"\n... and {len(cleaned_questions) - 20} more questions")
    
    print("\n" + "="*70)
    print("Question generation complete!")
    print("="*70)


if __name__ == "__main__":
    main()
