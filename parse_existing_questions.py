"""
Parse existing scraped questions and extract proper question-option pairs
This script processes the raw scraped data to extract complete questions with options
"""

import csv
import json
import re
from typing import List, Dict

def parse_questions_from_csv(filename: str = "cissp_questions.csv") -> List[Dict]:
    """Parse questions from CSV and extract proper question-option pairs"""
    
    questions = []
    current_question = None
    current_options = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    i = 0
    while i < len(rows):
        row = rows[i]
        question_text = row.get('question', '').strip()
        
        # Skip empty or header rows
        if not question_text or len(question_text) < 10:
            i += 1
            continue
        
        # Check if this is a question (ends with ? and is substantial)
        if question_text.endswith('?') and len(question_text) > 20:
            # Save previous question if exists
            if current_question and len(current_options) >= 2:
                questions.append({
                    'question': current_question,
                    'options': current_options[:4],
                    'correct_answer': '',
                    'topic': ''
                })
            
            # Start new question
            current_question = question_text
            current_options = []
            
            # Look ahead for options in next rows
            j = i + 1
            while j < min(i + 15, len(rows)):
                next_row = rows[j]
                next_text = next_row.get('question', '').strip()
                
                # Check if this is an option (starts with A., B., C., or D.)
                option_match = re.match(r'^([A-D])\.\s*(.+)$', next_text)
                if option_match:
                    letter = option_match.group(1)
                    option_text = option_match.group(2).strip()
                    if len(option_text) > 5:
                        current_options.append(f"{letter}. {option_text}")
                elif next_text.endswith('?') and len(next_text) > 20:
                    # Hit next question, stop
                    break
                elif 'Correct Answer' in next_text:
                    # Extract correct answer
                    match = re.search(r'Correct Answer:\s*([A-D])', next_text, re.I)
                    if match:
                        # Update the last saved question's correct answer
                        if questions:
                            questions[-1]['correct_answer'] = match.group(1).upper()
                
                j += 1
            
            i = j
        else:
            i += 1
    
    # Save last question
    if current_question and len(current_options) >= 2:
        questions.append({
            'question': current_question,
            'options': current_options[:4],
            'correct_answer': '',
            'topic': ''
        })
    
    return questions


def parse_from_text_file(filename: str = "cissp_questions.csv") -> List[Dict]:
    """Alternative parsing method - read as text and extract patterns"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = []
    
    # Split by lines
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip CSV header and empty lines
        if not line or line.startswith('question,options') or len(line) < 10:
            i += 1
            continue
        
        # Check if line contains a question (ends with ?)
        if line.endswith('?') and len(line) > 30:
            # Extract question (remove CSV formatting)
            question_text = line.split(',')[0].strip()
            if question_text.startswith('"') and question_text.endswith('"'):
                question_text = question_text[1:-1]
            
            # Look for options in following lines
            options = []
            j = i + 1
            
            while j < min(i + 20, len(lines)):
                next_line = lines[j].strip()
                
                # Skip empty lines
                if not next_line:
                    j += 1
                    continue
                
                # Check if this line is an option
                # Options might be in format: "A. Option text" or just "A. Option text" in CSV
                parts = next_line.split(',')
                if len(parts) > 0:
                    potential_option = parts[0].strip()
                    if potential_option.startswith('"'):
                        potential_option = potential_option[1:]
                    
                    option_match = re.match(r'^([A-D])\.\s*(.+)$', potential_option)
                    if option_match:
                        letter = option_match.group(1)
                        option_text = option_match.group(2).strip()
                        if option_text.endswith('"'):
                            option_text = option_text[:-1]
                        if len(option_text) > 5:
                            options.append(f"{letter}. {option_text}")
                
                # Check for correct answer
                if 'Correct Answer' in next_line:
                    match = re.search(r'Correct Answer:\s*([A-D])', next_line, re.I)
                    if match and questions:
                        questions[-1]['correct_answer'] = match.group(1).upper()
                
                # Stop if we hit another question
                if next_line.endswith('?') and len(next_line) > 30:
                    break
                
                j += 1
            
            if question_text and len(options) >= 2:
                questions.append({
                    'question': question_text,
                    'options': options[:4],
                    'correct_answer': '',
                    'topic': ''
                })
        
        i += 1
    
    return questions


def main():
    print("Parsing existing scraped questions...")
    print("="*60)
    
    # Try both methods
    print("\nMethod 1: CSV parsing...")
    questions1 = parse_questions_from_csv("cissp_questions.csv")
    print(f"Found {len(questions1)} questions")
    
    print("\nMethod 2: Text pattern parsing...")
    questions2 = parse_from_text_file("cissp_questions.csv")
    print(f"Found {len(questions2)} questions")
    
    # Use the method that found more questions
    if len(questions2) > len(questions1):
        questions = questions2
        print(f"\nUsing Method 2 (found more questions)")
    else:
        questions = questions1
        print(f"\nUsing Method 1")
    
    # Remove duplicates
    seen = set()
    unique_questions = []
    for q in questions:
        key = q['question'][:80].lower()
        if key not in seen:
            seen.add(key)
            unique_questions.append(q)
    
    print(f"\nUnique questions: {len(unique_questions)}")
    print(f"Questions with 4 options: {sum(1 for q in unique_questions if len(q.get('options', [])) == 4)}")
    print(f"Questions with 2+ options: {sum(1 for q in unique_questions if len(q.get('options', [])) >= 2)}")
    
    # Save results
    if unique_questions:
        # Save to JSON
        with open("cissp_questions_parsed.json", 'w', encoding='utf-8') as f:
            json.dump(unique_questions, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to cissp_questions_parsed.json")
        
        # Save to CSV
        with open("cissp_questions_parsed.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['question', 'options', 'correct_answer', 'topic'])
            writer.writeheader()
            for q in unique_questions:
                row = q.copy()
                row['options'] = ' | '.join(q['options'])
                writer.writerow(row)
        print(f"Saved to cissp_questions_parsed.csv")
        
        # Show samples
        print("\n" + "="*60)
        print("Sample Questions:")
        print("="*60)
        for i, q in enumerate(unique_questions[:5], 1):
            print(f"\n{i}. {q['question']}")
            for opt in q['options']:
                print(f"   {opt}")
            if q.get('correct_answer'):
                print(f"   Correct Answer: {q['correct_answer']}")
    else:
        print("\nNo valid questions found. The CSV structure may need manual inspection.")


if __name__ == "__main__":
    main()
