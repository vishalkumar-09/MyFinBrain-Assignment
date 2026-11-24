# Startup Funding Intelligence Platform (US & India)

An automated platform that monitors, collects, verifies, and organizes startup investment announcements across the United States and India in Private Markets, Alternative Investments, Wealth Management, and adjacent financial technology sectors.

---

## 1. Quick Start and Setup Guide

This platform is designed to run with a single command. Follow these simple steps to run the platform and view the generated Excel report.

### Requirements
- Python 3.10 or higher
- An internet connection (to fetch recent news and articles)

### Step 1: Open Your Terminal
Navigate to the project folder:
```bash
cd ~/Desktop/MyFinBrainAssignment
```

### Step 2: Install Required Packages (First Time Only)
If you are setting this up on a new computer, install the required packages:
```bash
pip install -r requirements.txt
```
*(Note: If dependencies are already pre-installed in the repository, you can skip directly to Step 3).*

### Step 3: Run the Project
Execute the single runner file:
```bash
python run.py
```

### Step 4: Open Your Excel Report
Once the execution finishes, open the final formatted spreadsheet located at:
```text
data/startups_funding.xlsx
```
You can open this file directly in Microsoft Excel, Google Sheets, Apple Numbers, or LibreOffice.

---

## 2. Executive Summary for Non-Technical Stakeholders

### The Problem It Solves
Tracking startup investments manually requires analysts to spend dozens of hours every week reading news articles across multiple websites, searching through corporate announcements, copying numbers into spreadsheets, converting currencies, and verifying whether a startup fits target investment themes. This manual process is slow, prone to human error, and misses emerging deals.

### What This Platform Does
This platform acts as an automated 24/7 research analyst:
1. **Reads the News**: It monitors reputable venture capital and financial publications (TechCrunch, Inc42, YourStory, Entrackr, PR Newswire, Business Wire, and Google News).
2. **Finds Funding Announcements**: It scans article headlines and bodies to identify financing events, funding amounts, funding stages (Seed, Series A, Series B, etc.), and lead investors.
3. **Validates Geography**: It verifies that the startup is legitimately headquartered in the United States or India, carefully ignoring the location of the venture capital firm.
4. **Classifies Business Sectors**: It checks if the company operates in Private Markets, Alternative Assets, or Wealth Management, while automatically filtering out irrelevant companies such as payment gateways, payday lenders, insurance sellers, or online shopping stores.
5. **Deduplicates Deals**: If five different news websites report on the exact same funding round, the platform intelligently merges them into one single clean record instead of cluttering your spreadsheet with 5 duplicates.
6. **Produces Formatted Deliverables**: It generates a 5-sheet, styled Excel workbook, CSV files, and a database ready for presentation and immediate decision-making.

---

## 3. How to Adjust Settings (No Coding Required)

All settings can be modified easily without modifying internal code. Open the file `run.py` in any text editor and look at the top section labeled `USER CONFIGURATION`:

### Changing the Date Range
To analyze deals within a specific timeframe, change `START_DATE` and `END_DATE` (format: YYYY-MM-DD):
```python
START_DATE = "2024-11-23"
END_DATE = "2026-11-23"
```

### Setting the Number of Deals to Extract
To control how many companies you want to collect, set `TARGET_EXTRACTIONS`:
```python
TARGET_EXTRACTIONS = 100  # Set to 50, 80, 100, 200, or None to process everything
```

### Adding New Websites or RSS Feeds
To add your own news sources or custom blogs, add their details to `ADDITIONAL_CUSTOM_SOURCES`:
```python
ADDITIONAL_CUSTOM_SOURCES = [
    {
        "id": "my_fintech_news",
        "name": "Custom Fintech Source",
        "feed_urls": ["https://example.com/feed/"],
    },
]
```

### Choosing Which News Outlets to Query
You can select or deselect sources in the list `ENABLED_SOURCES`:
```python
ENABLED_SOURCES = [
    "techcrunch",
    "inc42",
    "yourstory",
    "entrackr",
    "businesswire",
    "prnewswire",
    # "venturebeat",
    # "google_news",
]
```

---

## 4. What the Generated Excel Workbook Contains

The primary deliverable is `data/startups_funding.xlsx`. It is structured into 5 sheets:

1. **Funding Announcements**: The master view combining company names, investment rounds, normalized amounts (in USD and INR), round stages, lead investors, and links to the original articles.
2. **Companies**: A clean directory of unique startups, including their normalized names, website domains, headquarters location, operating regions, and primary business classification.
3. **Funding Rounds**: A detailed breakdown of every financial transaction, showing the exact amount reported in the article text alongside normalized numeric figures.
4. **Source Articles**: A complete audit registry of all articles gathered across every news source, recording publication dates, publisher names, and processing status.
5. **Records Requiring Review**: A transparent queue of companies where location or business model was ambiguous or cross-border. Rather than guessing, the platform places them here so a human analyst can review them in seconds.

---

## 5. Target Business Sectors and Boundaries

The platform categorizes startups according to predefined business themes:

### Sectors Included:
- **Private Markets**: Private equity technology, private credit and debt platforms, pre-IPO investment platforms, unlisted shares marketplaces, and secondary market trading platforms.
- **Alternative Investments**: Fractional ownership platforms (commercial real estate, fine art, collectibles), alternative asset managers, hedge fund software, and commodity investment systems.
- **Wealth Management**: Digital wealth advisory, wealthtech, portfolio management systems, family office technology, robo-advisors, and automated brokerage infrastructure.
- **Adjacent Investment Technology**: Financial market intelligence, asset allocation algorithms, portfolio analytics, and investment reporting APIs.

### Sectors Excluded (Negative Filter):
To maintain high relevance, the platform rejects companies that do not belong to the target sectors:
- Payment-only gateways and merchant processing platforms
- Consumer lending, personal loans, and buy-now-pay-later (BNPL) apps
- General insurance aggregators and brokers
- Standard e-commerce, consumer retail, and online shopping apps
- General enterprise software without investment or wealth management products

---

## 6. How the System Ensures Data Accuracy

### Anti-Hallucination Geography
When a news headline states: *"Tiger Global (New York) leads $20M round in Mumbai-based fintech"*, standard scrapers often mistakenly record New York as the startup's location. This platform uses contextual sentence parsing to isolate investor locations and correctly assign Mumbai, India as the startup headquarters.

### Smart Currency Conversion
Funding rounds in India are frequently reported in local denominations such as *"Rs 50 Crore"* or *"Rs 80 Lakh"*. The platform normalizes these denominations into numeric USD and INR values while preserving the original wording for full verification.

### Discarding VC Fund Raises
When a venture capital firm announces: *"Sequoia raises $500M new fund"*, it is not a startup raising capital. The platform recognizes this language and automatically discards fund-raising announcements from startup deals.

### Full Evidence and Auditability
Every single company name, funding amount, and headquarters city links directly back to the sentence and URL where it was published. Nothing is invented or assumed.

---

## 7. Deliverables and Output Files

All output files are saved in the `data/` folder:

| File Name | Format | Description |
|---|---|---|
| `data/startups_funding.xlsx` | Excel (.xlsx) | 5-sheet styled workbook with headers, auto-adjusted columns, and clean formatting. |
| `data/startups.csv` | CSV | Deduplicated company profiles with categories and geography. |
| `data/funding_rounds.csv` | CSV | Structured investment records with stages, amounts, and investors. |
| `data/articles.csv` | CSV | Complete log of all discovered articles and publication dates. |
| `data/startups_funding.sqlite` | SQLite Database | Relational database preserving company relationships, funding rounds, and field-level evidence. |

---

## 8. Automated Quality Checks and Verification

The platform includes a test suite of **162 automated test cases** that verify every aspect of data collection and extraction, including:
- Currency parsing accuracy across USD, INR Crores, Lakhs, EUR, and GBP.
- Business taxonomy classification and exclusion filters.
- Geography verification and cross-border protection.
- Article deduplication and URL canonicalization.
- Multi-sheet Excel workbook export integrity.

To run the automated tests, run:
```bash
pytest tests/
```
Result: **162 passed in under 2 seconds**.

---

## 9. Advanced Usage for Technical Users

For engineers who want to execute individual pipeline phases independently, the CLI tool `main.py` is available:

```bash
# Run the complete pipeline end-to-end
python main.py --mode all

# Discover articles only
python main.py --mode discover

# Extract funding details from discovered articles
python main.py --mode extract

# Classify and verify companies
python main.py --mode classify

# Regenerate Excel and CSV exports from the database
python main.py --mode export

# Query specific sources only
python main.py --mode all --sources techcrunch,yourstory,inc42

# Filter for custom date windows
python main.py --mode all --start-date 2024-11-23 --end-date 2026-11-23
```
