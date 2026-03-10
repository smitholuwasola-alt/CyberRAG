# CISSP Question Scraper - Working Version

## Status: ✅ Working

This scraper successfully scraped **1,650 questions** from ExamTopics CISSP exam pages.

## Files

- **`cissp_scraper.py`** - Main working scraper (this is the one that worked)
- **Output files:**
  - `cissp_questions.json` - JSON format (1,650 questions)
  - `cissp_questions.csv` - CSV format (1,650 questions)

## Usage

```bash
python scraper/cissp_scraper.py
```

This will:
1. Scrape questions from ExamTopics CISSP pages
2. Extract question text
3. Save to both JSON and CSV formats
4. Handle rate limiting (2 second delay between pages)

## Configuration

Default settings:
- **Base URL**: `https://www.examtopics.com/exams/isc/cissp/view/`
- **Max Pages**: 50 (configurable in `scrape_all_pages()`)
- **Rate Limiting**: 2 seconds between pages

## Output Format

Each question entry contains:
```json
{
  "question": "Question text here?",
  "options": [],
  "correct_answer": "",
  "topic": ""
}
```

## Notes

- The scraper successfully captured question text from all pages
- Questions are stored in both JSON and CSV for flexibility
- The scraper handles pagination automatically
- Rate limiting is built-in to be respectful to the website

## Alternative Scrapers

Other scraper versions were created but this is the **working version**:
- `cissp_scraper.py` - ✅ **This is the working one**
- `cissp_scraper_improved.py` - Alternative approach
- `cissp_scraper_robust.py` - Robust text pattern matching
- `cissp_scraper_selenium.py` - Selenium-based (for JS-heavy sites)

## Next Steps

The scraped questions can now be used with:
1. Knowledge graph query engine
2. Question answering system
3. Training/testing datasets
