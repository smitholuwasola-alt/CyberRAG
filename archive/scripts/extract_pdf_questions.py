"""
Extract Questions from PDF Textbook
Scrapes questions from the EB-Ultimate-guide PDF and saves them in organized format
"""

import re
import json
import csv
from pathlib import Path
from typing import List, Dict
import sys

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("pdfplumber not available. Trying PyPDF2...")
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False
        print("Neither pdfplumber nor PyPDF2 available. Please install: pip install pdfplumber")


def extract_text_with_pdfplumber(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_text_with_pypdf2(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF2"""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using available library"""
    if PDFPLUMBER_AVAILABLE:
        return extract_text_with_pdfplumber(pdf_path)
    elif PYPDF2_AVAILABLE:
        return extract_text_with_pypdf2(pdf_path)
    else:
        raise ImportError("No PDF library available. Install pdfplumber: pip install pdfplumber")


def identify_questions(text: str) -> List[Dict]:
    """
    Identify and extract ALL possible questions from text
    Comprehensive extraction including:
    - Explicit questions ending with ?
    - Implicit questions (sentences starting with question words)
    - Questions in lists, bullet points, or embedded in text
    """
    questions = []
    question_number = 0
    question_starters = ['what', 'which', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'can', 'should', 'does', 'do', 'will', 'would', 'could', 'must', 'may', 'might', 'shall']
    
    # Method 1: Find ALL sentences ending with ? (be more lenient)
    question_pattern = r'([^.!?]*\?)'
    all_matches = list(re.finditer(question_pattern, text))
    
    for match in all_matches:
        segment = match.group(1).strip()
        
        # More lenient length check
        if len(segment) < 10 or len(segment) > 600:
            continue
        
        # Clean up whitespace
        segment = re.sub(r'\s+', ' ', segment).strip()
        
        # Remove common prefixes
        segment = re.sub(r'^\d+[\.\)]\s*', '', segment)
        segment = re.sub(r'^[Qq]uestion\s+\d+[\.\)]?\s*', '', segment, flags=re.IGNORECASE)
        segment = re.sub(r'^[Qq]\d+[\.\)]?\s*', '', segment)
        
        # Must end with ?
        if not segment.endswith('?'):
            continue
        
        # Skip URLs, emails, and very technical artifacts
        if 'http' in segment.lower() or '@' in segment or 'www.' in segment.lower():
            continue
        
        # Skip if it's just punctuation
        clean_seg = segment.replace('?', '').strip()
        if len(clean_seg) < 8:
            continue
        
        question_number += 1
        
        # Try to find options
        options = []
        match_end = match.end()
        following_text = text[match_end:match_end+1000]
        following_lines = following_text.split('\n')[:20]
        
        for line in following_lines:
            line = line.strip()
            if not line:
                continue
            option_match = re.match(r'^([A-E])[\.\)]\s*(.+)$', line)
            if option_match:
                option_letter = option_match.group(1)
                option_text = option_match.group(2).strip()
                if len(option_text) > 2 and len(option_text) < 200:
                    options.append(f"{option_letter}. {option_text}")
            elif options:
                break
        
        questions.append({
            'question_number': question_number,
            'question': segment,
            'options': options,
            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
        })
    
    # Method 2: Find implicit questions (sentences starting with question words, even without ?)
    # Split into sentences more carefully
    sentences = re.split(r'[.!?]\s+|\.\s+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        if len(sentence) < 15 or len(sentence) > 400:
            continue
        
        # Get first word
        words = sentence.split()
        if not words:
            continue
        
        first_word = words[0].lower().strip('.,!?;:()[]"\'')
        
        # Check if starts with question word
        if first_word in question_starters:
            # Check if already captured
            already_captured = any(
                sentence.lower() in q['question'].lower() or 
                q['question'].lower() in sentence.lower() 
                for q in questions
            )
            
            if not already_captured:
                # Clean the sentence
                sentence = re.sub(r'\s+', ' ', sentence).strip()
                
                # Skip URLs, emails
                if 'http' in sentence.lower() or '@' in sentence or 'www.' in sentence.lower():
                    continue
                
                # Skip if too technical (has many numbers/URLs)
                if len(re.findall(r'\d{4,}', sentence)) > 2:
                    continue
                
                # Add ? if not present
                if not sentence.endswith('?'):
                    sentence += "?"
                
                question_number += 1
                questions.append({
                    'question_number': question_number,
                    'question': sentence,
                    'options': [],
                    'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                })
    
    # Method 3: Find questions in bullet points or numbered lists
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        
        if len(line) < 15 or len(line) > 400:
            continue
        
        # Check for bullet point or numbered list
        bullet_match = re.match(r'^[•\-\*]\s+(.+)', line)
        numbered_match = re.match(r'^\d+[\.\)]\s+(.+)', line)
        
        if bullet_match:
            clean_line = bullet_match.group(1).strip()
        elif numbered_match:
            clean_line = numbered_match.group(1).strip()
        else:
            continue
        
        # Check if starts with question word
        first_word = clean_line.split()[0].lower().strip('.,!?;:()[]"\'') if clean_line.split() else ''
        
        if first_word in question_starters:
            # Check if already captured
            already_captured = any(
                clean_line.lower() in q['question'].lower() or 
                q['question'].lower() in clean_line.lower() 
                for q in questions
            )
            
            if not already_captured:
                clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                
                if 'http' in clean_line.lower() or '@' in clean_line:
                    continue
                
                if not clean_line.endswith('?'):
                    clean_line += "?"
                
                question_number += 1
                questions.append({
                    'question_number': question_number,
                    'question': clean_line,
                    'options': [],
                    'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                })
    
    return questions
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and headers/footers
        if not line or len(line) < 10:
            i += 1
            continue
        
        # Check if line is a question
        is_question = False
        question_text = None
        
        for pattern in question_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                question_text = match.group(1) if match.groups() else line
                # Ensure it ends with ?
                if not question_text.endswith('?'):
                    # Check if next line completes the question
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not re.match(option_pattern, next_line):
                            question_text = line + " " + next_line
                            i += 1
                            if not question_text.endswith('?'):
                                question_text += "?"
                else:
                    question_text = line
                
                # Validate it's actually a question (has question words or ends with ?)
                if question_text.endswith('?') and len(question_text) > 20:
                    is_question = True
                    break
        
        if is_question and question_text:
            # Save previous question if exists
            if current_question and len(current_question.strip()) > 20:
                question_number += 1
                questions.append({
                    'question_number': question_number,
                    'question': current_question.strip(),
                    'options': current_options.copy(),
                    'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
                })
            
            # Start new question
            current_question = question_text
            current_options = []
            in_question_block = True
        
        # Check if line is an option
        elif in_question_block:
            option_match = re.match(option_pattern, line)
            if option_match:
                option_letter = option_match.group(1)
                option_text = option_match.group(2).strip()
                current_options.append(f"{option_letter}. {option_text}")
            else:
                # If we hit text that's not an option and not a question, might be continuation
                if line and not line[0].isdigit() and len(line) > 5:
                    # Check if it's part of the question (no capital letter at start suggesting new sentence)
                    if current_question and not re.match(r'^[A-Z]', line):
                        current_question += " " + line
                    # Otherwise, we might be done with this question block
                    elif len(current_options) > 0:
                        in_question_block = False
        
        i += 1
    
    # Save last question
    if current_question and len(current_question.strip()) > 20:
        question_number += 1
        questions.append({
            'question_number': question_number,
            'question': current_question.strip(),
            'options': current_options.copy(),
            'source': 'EB-Ultimate-guide-IT-Risk-and-Compliance-EN.pdf'
        })
    
    return questions


def clean_questions(questions: List[Dict]) -> List[Dict]:
    """Clean and validate extracted questions"""
    cleaned = []
    seen_questions = set()
    
    for q in questions:
        question_text = q['question'].strip()
        
        # Remove common PDF artifacts
        question_text = re.sub(r'\bcom\s+\d+\b', '', question_text, flags=re.IGNORECASE)  # Remove "com 3"
        question_text = re.sub(r'\bCHAPTER\s+[A-Z]+\s+\d+[^\?]*', '', question_text, flags=re.IGNORECASE)  # Remove "CHAPTER ONE Exploring..."
        question_text = re.sub(r'\bCHAPTER\s+\d+[^\?]*', '', question_text, flags=re.IGNORECASE)  # Remove "CHAPTER 1..."
        question_text = re.sub(r'\btanium\.com\s+\d+\b', '', question_text, flags=re.IGNORECASE)  # Remove "tanium.com 3"
        question_text = re.sub(r'\bpage\s+\d+\b', '', question_text, flags=re.IGNORECASE)  # Remove "page 3"
        
        # Remove chapter titles that might be before the question
        # Look for patterns like "CHAPTER X Title Text What is..."
        # Try to find where the actual question starts
        question_starters = r'\b(What|Which|How|Why|When|Where|Who|Is|Are|Can|Should|Does|Do|Will|Would|Could)\b'
        question_match = re.search(question_starters, question_text, re.IGNORECASE)
        if question_match:
            # Extract from the question starter to the end
            start_pos = question_match.start()
            question_text = question_text[start_pos:].strip()
        
        # Also remove any remaining chapter/header text at the start
        question_text = re.sub(r'^(?:CHAPTER|Chapter|Exploring|Understanding)\s+[A-Z][^?]*?\s+', '', question_text, flags=re.IGNORECASE)
        
        # If question contains multiple question-like phrases, take the last one (usually the actual question)
        # Pattern: "Some text Why/What/How Question?"
        question_matches = list(re.finditer(r'\b(Why|What|Which|How|When|Where|Who|Is|Are|Can|Should|Does|Do|Will|Would|Could)\s+[^?]+\?', question_text, re.IGNORECASE))
        if len(question_matches) > 1:
            # Extract the last question
            last_q_match = question_matches[-1]
            question_text = question_text[last_q_match.start():].strip()
        elif 'Why Tanium?' in question_text:
            # Special case for "Why Tanium?"
            question_text = 'Why Tanium?'
        
        # Remove URLs
        question_text = re.sub(r'https?://[^\s]+', '', question_text)
        
        # Clean up extra whitespace
        question_text = re.sub(r'\s+', ' ', question_text).strip()
        
        # Skip duplicates
        question_key = question_text[:100].lower()
        if question_key in seen_questions:
            continue
        seen_questions.add(question_key)
        
        # Skip if too short or doesn't look like a question
        if len(question_text) < 15:
            continue
        
        # Ensure it ends with ?
        if not question_text.endswith('?'):
            question_text += "?"
        
        # Skip if it's clearly not a question (contains too many technical artifacts)
        if re.search(r'\d{4,}', question_text):  # Skip if has long numbers (likely dates/IDs)
            continue
        
        # Skip statements that look like questions but aren't (e.g., "When building... organizations can adopt several?")
        # Real questions usually have question structure, not just "When [action], [subject] [verb]?"
        # Check if it's a statement pattern: "When [verb-ing], [subject] [verb] [object]?"
        statement_patterns = [
            r'^When\s+\w+ing\s+[^?]+,?\s+\w+\s+\w+\s+[^?]+\?$',  # "When building..., organizations can adopt?"
            r'^When\s+exploring\s+[^?]+,?\s+make\s+sure',  # "When exploring..., make sure..."
            r'^When\s+[^?]+\s+can\s+[^?]+\?$',  # "When X, can Y?"
        ]
        if any(re.match(pattern, question_text, re.IGNORECASE) for pattern in statement_patterns):
            continue
        
        # Clean options
        cleaned_options = []
        for opt in q['options']:
            opt = re.sub(r'\s+', ' ', opt).strip()
            if len(opt) > 3:  # Valid option should have at least "A. text"
                cleaned_options.append(opt)
        
        cleaned.append({
            'question_number': q['question_number'],
            'question': question_text,
            'options': cleaned_options,
            'source': q['source']
        })
    
    return cleaned


def save_questions(questions: List[Dict], output_dir: Path):
    """Save questions to CSV and JSON files"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    json_file = output_dir / "eb_ultimate_guide_questions.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {len(questions)} questions to {json_file}")
    
    # Save as CSV
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
    print("PDF Question Extractor - EB Ultimate Guide")
    print("="*70)
    
    # Find PDF file
    pdf_files = list(PROJECT_ROOT.rglob("EB-Ultimate-guide*.pdf"))
    
    if not pdf_files:
        print("Error: PDF file not found!")
        print("Looking for: EB-Ultimate-guide*.pdf")
        return
    
    pdf_path = pdf_files[0]
    print(f"\nFound PDF: {pdf_path.name}")
    print(f"Full path: {pdf_path}")
    
    # Extract text
    print("\nExtracting text from PDF...")
    try:
        text = extract_text_from_pdf(str(pdf_path))
        print(f"[OK] Extracted {len(text)} characters of text")
    except Exception as e:
        print(f"[ERROR] Error extracting text: {e}")
        return
    
    # Extract questions
    print("\nIdentifying questions...")
    questions = identify_questions(text)
    print(f"[OK] Found {len(questions)} potential questions")
    
    # Clean questions
    print("\nCleaning questions...")
    cleaned_questions = clean_questions(questions)
    print(f"[OK] {len(cleaned_questions)} valid questions after cleaning")
    
    # Save questions
    output_dir = PROJECT_ROOT / "data" / "qa"
    print(f"\nSaving questions to {output_dir}...")
    save_questions(cleaned_questions, output_dir)
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    print(f"Total questions extracted: {len(cleaned_questions)}")
    print(f"Questions with options: {sum(1 for q in cleaned_questions if len(q['options']) > 0)}")
    print(f"Questions without options: {sum(1 for q in cleaned_questions if len(q['options']) == 0)}")
    
    # Show sample questions
    print("\n" + "="*70)
    print("SAMPLE QUESTIONS (first 5):")
    print("="*70)
    for i, q in enumerate(cleaned_questions[:5], 1):
        try:
            question_text = q['question'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n{i}. {question_text}")
            if q['options']:
                for opt in q['options']:
                    opt_text = opt.encode('ascii', 'ignore').decode('ascii')
                    print(f"   {opt_text}")
            else:
                print("   (No options found)")
        except:
            print(f"\n{i}. [Question {i} - encoding issue]")
    
    print("\n" + "="*70)
    print("Extraction complete!")
    print("="*70)


if __name__ == "__main__":
    main()
