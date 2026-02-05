# Website Scraper

A Python utility for crawling websites, extracting content, and generating summaries based on configurable questions.

## Features

- **Dual-mode crawling**: Static HTML (fast) or JavaScript rendering (for SPAs)
- **Smart content extraction**: Uses readability algorithms to extract main content
- **Question-based summarization**: Define questions in YAML, get answers from scraped content
- **Pattern matching**: Automatically extracts emails, phones, addresses, prices
- **Polite crawling**: Configurable delays and respects site boundaries
- **Markdown output**: Clean, readable reports

## Installation

```bash
git clone <repo-url> && cd website-scraper

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For JavaScript rendering support
playwright install chromium
```

## Quick Start

```bash
# Basic usage - dump website content
./scrape https://example.com --dump-only

# With questions for Q&A summary
./scrape https://example.com --questions config/questions.example.yaml

# For JavaScript-heavy sites (SPAs)
./scrape https://spa-site.com --js --questions config/questions.example.yaml
```

## Usage

```
./scrape <url> [options]

Arguments:
  url                   The URL of the website to crawl

Options:
  -q, --questions PATH  Path to YAML file containing questions
  -o, --output PATH     Output directory (default: output/)
  --max-pages N         Maximum pages to crawl (default: 50)
  --max-depth N         Maximum link depth (default: 5)
  --delay SECONDS       Delay between requests (default: 1.0)
  --timeout SECONDS     Request timeout (default: 30)
  --js                  Enable JavaScript rendering
  --dump-only           Only dump content, skip Q&A
```

## Questions File Format

Create a YAML file with questions organized by category:

```yaml
organization:
  name: "What is the company name?"
  description: "What does this company do?"

contact:
  email: "What is the contact email?"
  phone: "What is the phone number?"

custom:
  - "What products do they offer?"
  - "Who are the founders?"
```

See `config/questions.example.yaml` for a complete example.

## Output

The scraper generates markdown files in the output directory:

- `*_summary.md` - Q&A summary with answers and sources
- `*_site_dump.md` - Complete content dump from all pages
- `index.md` - Index of all generated files

## Examples

```bash
# Crawl a company website
./scrape https://anthropic.com \
  --questions config/questions.example.yaml \
  --max-pages 30

# Crawl a React SPA with JS rendering
./scrape https://react-app.com \
  --js \
  --questions questions.yaml \
  --delay 2

# Quick content dump of small site
./scrape https://blog.example.com \
  --max-pages 10 \
  --dump-only
```

## Project Structure

```
website-scraper/
├── scrape             # CLI entry point (run this)
├── src/
│   ├── main.py        # Main application logic
│   ├── crawler.py     # Web crawling engine
│   ├── extractor.py   # Content extraction
│   ├── summarizer.py  # Question answering
│   └── output.py      # Markdown generation
├── config/
│   └── questions.example.yaml
├── output/            # Generated reports
└── requirements.txt
```

## Alternative: Manual Python Invocation

If you prefer not to use the `./scrape` wrapper, activate the virtual environment first:

```bash
source .venv/bin/activate
python -m src.main https://example.com --dump-only
```
