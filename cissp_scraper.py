"""
CISSP Exam Questions Scraper
Scrapes questions from ExamTopics CISSP exam page
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import List, Dict
import csv

class CISSPScraper:
    def __init__(self, base_url: str = "https://www.examtopics.com/exams/isc/cissp/view/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.questions = []
    
    def scrape_question_page(self, page_num: int = 1) -> List[Dict]:
        """Scrape questions from a specific page"""
        url = f"{self.base_url}?page={page_num}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            questions = []
            
            # Find all question containers
            question_containers = soup.find_all('div', class_=re.compile('question|card', re.I))
            
            for container in question_containers:
                question_data = self._extract_question(container)
                if question_data:
                    questions.append(question_data)
            
            # Alternative: Look for question text patterns
            if not questions:
                questions = self._extract_questions_alternative(soup)
            
            return questions
            
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
            return []
    
    def _extract_question(self, container) -> Dict:
        """Extract question data from a container"""
        try:
            question_text = ""
            options = []
            correct_answer = ""
            topic = ""
            
            # Extract question text
            q_text_elem = container.find(['p', 'div', 'h3'], class_=re.compile('question|text', re.I))
            if not q_text_elem:
                q_text_elem = container.find(string=re.compile(r'Question\s*#', re.I))
            
            if q_text_elem:
                if hasattr(q_text_elem, 'get_text'):
                    question_text = q_text_elem.get_text(strip=True)
                else:
                    question_text = str(q_text_elem).strip()
            
            # Extract options (A, B, C, D)
            option_elems = container.find_all(['li', 'div', 'p'], string=re.compile(r'^[A-D]\.', re.M))
            for opt in option_elems:
                opt_text = opt.get_text(strip=True) if hasattr(opt, 'get_text') else str(opt).strip()
                options.append(opt_text)
            
            # Extract correct answer
            correct_elem = container.find(string=re.compile(r'Correct Answer|Answer:', re.I))
            if correct_elem:
                correct_answer = str(correct_elem).strip()
            
            if question_text:
                return {
                    'question': question_text,
                    'options': options,
                    'correct_answer': correct_answer,
                    'topic': topic
                }
        except Exception as e:
            print(f"Error extracting question: {e}")
        
        return None
    
    def _extract_questions_alternative(self, soup) -> List[Dict]:
        """Alternative extraction method using text patterns"""
        questions = []
        text = soup.get_text()
        
        # Find question patterns
        question_pattern = r'Question\s*#\d+[^\?]*\?'
        matches = re.finditer(question_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            question_text = match.group(0)
            # Try to find options after the question
            start_pos = match.end()
            next_question = re.search(r'Question\s*#', text[start_pos:start_pos+2000], re.I)
            end_pos = start_pos + (next_question.start() if next_question else 2000)
            
            options_text = text[start_pos:end_pos]
            options = re.findall(r'[A-D]\.\s*[^\n]+', options_text)
            
            questions.append({
                'question': question_text.strip(),
                'options': [opt.strip() for opt in options],
                'correct_answer': '',
                'topic': ''
            })
        
        return questions
    
    def scrape_all_pages(self, max_pages: int = 50) -> List[Dict]:
        """Scrape all available pages"""
        all_questions = []
        
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            questions = self.scrape_question_page(page)
            
            if not questions:
                print(f"No questions found on page {page}, stopping...")
                break
            
            all_questions.extend(questions)
            print(f"Found {len(questions)} questions on page {page}")
            
            # Be respectful with rate limiting
            time.sleep(2)
        
        return all_questions
    
    def save_to_json(self, questions: List[Dict], filename: str = "cissp_questions.json"):
        """Save questions to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(questions)} questions to {filename}")
    
    def save_to_csv(self, questions: List[Dict], filename: str = "cissp_questions.csv"):
        """Save questions to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if questions:
                writer = csv.DictWriter(f, fieldnames=questions[0].keys())
                writer.writeheader()
                writer.writerows(questions)
        print(f"Saved {len(questions)} questions to {filename}")


def main():
    scraper = CISSPScraper()
    
    # Scrape questions
    print("Starting CISSP questions scraping...")
    questions = scraper.scrape_all_pages(max_pages=50)
    
    if questions:
        # Save to both JSON and CSV
        scraper.save_to_json(questions, "cissp_questions.json")
        scraper.save_to_csv(questions, "cissp_questions.csv")
        print(f"\nTotal questions scraped: {len(questions)}")
    else:
        print("No questions were scraped. The website structure may have changed.")


if __name__ == "__main__":
    main()
