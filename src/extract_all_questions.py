"""
Comprehensive Question Extractor - Finds ALL possible questions from PDF
This version is more aggressive in finding questions, including implicit ones
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


def extract_all_questions(text: str) -> List[Dict]:
    """
    Extract ALL possible questions using multiple methods
    """
    questions = []
    question_number = 0
    seen_questions = set()
    
    question_starters = [
        'what', 'which', 'how', 'why', 'when', 'where', 'who', 
        'is', 'are', 'can', 'should', 'does', 'do', 'will', 
        'would', 'could', 'must', 'may', 'might', 'shall'
    ]
    
    # Method 1: All sentences ending with ?
    question_matches = list(re.finditer(r'([^.!?]*\?)', text))
    
    for match in question_matches:
        segment = match.group(1).strip()
        
        if len(segment) < 8 or len(segment) > 600:
            continue
        
        segment = re.sub(r'\s+', ' ', segment).strip()
        segment = re.sub(r'^\d+[\.\)]\s*', '', segment)
        segment = re.sub(r'^[Qq]uestion\s+\d+[\.\)]?\s*', '', segment, flags=re.IGNORECASE)
        segment = re.sub(r'^[Qq]\d+[\.\)]?\s*', '', segment)
        
        if not segment.endswith('?'):
            continue
        
        # Skip URLs, emails
        if 'http' in segment.lower() or '@' in segment or 'www.' in segment.lower():
            continue
        
        clean_seg = segment.replace('?', '').strip()
        if len(clean_seg) < 8:
            continue
        
        # Create unique key
        key = clean_seg[:80].lower()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        
        question_number += 1
        questions.append({
            'question_number': question_number,
            'question': segment,
            'options': [],
            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
        })
    
    # Method 2: Sentences starting with question words (even without ?)
    # Split text into sentences more intelligently
    sentences = re.split(r'[.!?]\s+|\.\s+|:\s+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        if len(sentence) < 12 or len(sentence) > 350:
            continue
        
        words = sentence.split()
        if not words:
            continue
        
        first_word = words[0].lower().strip('.,!?;:()[]"\'')
        
        if first_word in question_starters:
            # Check if already captured
            key = sentence[:80].lower()
            if key in seen_questions:
                continue
            
            # Skip URLs, emails
            if 'http' in sentence.lower() or '@' in sentence or 'www.' in sentence.lower():
                continue
            
            # Skip if too many numbers (likely not a question)
            if len(re.findall(r'\d{4,}', sentence)) > 1:
                continue
            
            # Skip statement patterns
            if re.match(r'^When\s+\w+ing\s+[^?]+,?\s+\w+\s+\w+', sentence, re.IGNORECASE):
                continue
            
            sentence = re.sub(r'\s+', ' ', sentence).strip()
            
            if not sentence.endswith('?'):
                sentence += "?"
            
            seen_questions.add(key)
            question_number += 1
            questions.append({
                'question_number': question_number,
                'question': sentence,
                'options': [],
                'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
            })
    
    # Method 3: Questions in lists/bullet points
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        
        if len(line) < 12 or len(line) > 400:
            continue
        
        # Check for bullet or numbered list
        bullet_match = re.match(r'^[•\-\*]\s+(.+)', line)
        numbered_match = re.match(r'^\d+[\.\)]\s+(.+)', line)
        
        if bullet_match:
            clean_line = bullet_match.group(1).strip()
        elif numbered_match:
            clean_line = numbered_match.group(1).strip()
        else:
            continue
        
        first_word = clean_line.split()[0].lower().strip('.,!?;:()[]"\'') if clean_line.split() else ''
        
        if first_word in question_starters:
            key = clean_line[:80].lower()
            if key in seen_questions:
                continue
            
            if 'http' in clean_line.lower() or '@' in clean_line:
                continue
            
            clean_line = re.sub(r'\s+', ' ', clean_line).strip()
            
            if not clean_line.endswith('?'):
                clean_line += "?"
            
            seen_questions.add(key)
            question_number += 1
            questions.append({
                'question_number': question_number,
                'question': clean_line,
                'options': [],
                'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
            })
    
    return questions


def clean_questions(questions: List[Dict]) -> List[Dict]:
    """Clean and validate questions"""
    cleaned = []
    seen = set()
    
    for q in questions:
        question_text = q['question'].strip()
        
        # Remove PDF artifacts
        question_text = re.sub(r'\bcom\s+\d+\b', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'\bCHAPTER\s+[A-Z]+\s+\d+[^\?]*', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'\bCHAPTER\s+\d+[^\?]*', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'\btanium\.com\s+\d+\b', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'\bpage\s+\d+\b', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'https?://[^\s]+', '', question_text)
        question_text = re.sub(r'\s+', ' ', question_text).strip()
        
        # Remove chapter titles
        question_starters = r'\b(What|Which|How|Why|When|Where|Who|Is|Are|Can|Should|Does|Do|Will|Would|Could)\b'
        question_match = re.search(question_starters, question_text, re.IGNORECASE)
        if question_match:
            start_pos = question_match.start()
            question_text = question_text[start_pos:].strip()
        
        question_text = re.sub(r'^(?:CHAPTER|Chapter|Exploring|Understanding)\s+[A-Z][^?]*?\s+', '', question_text, flags=re.IGNORECASE)
        
        # Handle multiple questions in one
        question_matches = list(re.finditer(r'\b(Why|What|Which|How|When|Where|Who|Is|Are|Can|Should|Does|Do|Will|Would|Could)\s+[^?]+\?', question_text, re.IGNORECASE))
        if len(question_matches) > 1:
            last_q_match = question_matches[-1]
            question_text = question_text[last_q_match.start():].strip()
        elif 'Why Tanium?' in question_text:
            question_text = 'Why Tanium?'
        
        # Skip duplicates
        key = question_text[:100].lower()
        if key in seen or len(question_text) < 10:
            continue
        seen.add(key)
        
        # Ensure ends with ?
        if not question_text.endswith('?'):
            question_text += "?"
        
        # Skip statement patterns
        if re.match(r'^When\s+\w+ing\s+[^?]+,?\s+\w+\s+\w+\s+[^?]+\?$', question_text, re.IGNORECASE):
            continue
        if re.match(r'^When\s+exploring\s+[^?]+,?\s+make\s+sure', question_text, re.IGNORECASE):
            continue
        
        cleaned.append({
            'question_number': q['question_number'],
            'question': question_text,
            'options': q['options'],
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
    print("COMPREHENSIVE PDF Question Extractor - EB Ultimate Guide")
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
    
    # Extract ALL questions
    print("\nIdentifying ALL possible questions...")
    questions = extract_all_questions(text)
    print(f"[OK] Found {len(questions)} potential questions")
    
    # Clean questions
    print("\nCleaning questions...")
    cleaned_questions = clean_questions(questions)
    print(f"[OK] {len(cleaned_questions)} valid questions after cleaning")
    
    # Save
    output_dir = PROJECT_ROOT / "data" / "qa"
    print(f"\nSaving questions to {output_dir}...")
    save_questions(cleaned_questions, output_dir)
    
    # Summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    print(f"Total questions extracted: {len(cleaned_questions)}")
    print(f"Questions with options: {sum(1 for q in cleaned_questions if len(q['options']) > 0)}")
    print(f"Questions without options: {sum(1 for q in cleaned_questions if len(q['options']) == 0)}")
    
    # Show all questions
    print("\n" + "="*70)
    print("ALL EXTRACTED QUESTIONS:")
    print("="*70)
    for i, q in enumerate(cleaned_questions, 1):
        try:
            question_text = q['question'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n{i}. {question_text}")
            if q['options']:
                for opt in q['options']:
                    opt_text = opt.encode('ascii', 'ignore').decode('ascii')
                    print(f"   {opt_text}")
        except:
            print(f"\n{i}. [Question {i}]")
    
    print("\n" + "="*70)
    print("Extraction complete!")
    print("="*70)


if __name__ == "__main__":
    main()
