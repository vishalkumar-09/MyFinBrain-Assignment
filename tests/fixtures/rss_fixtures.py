# Sample RSS feed XML fixture – used in unit tests.
# This is a minimal but valid RSS 2.0 feed simulating a TechCrunch funding article.

TECHCRUNCH_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>TechCrunch</title>
    <link>https://techcrunch.com</link>
    <description>TechCrunch funding news</description>
    <atom:link href="https://techcrunch.com/tag/funding/feed/" rel="self" type="application/rss+xml"/>
    <item>
      <title>WealthAI raises $12.5M Series A to expand private market analytics platform</title>
      <link>https://techcrunch.com/2025/03/15/wealthai-series-a/</link>
      <pubDate>Sat, 15 Mar 2025 09:00:00 +0000</pubDate>
      <description>San Francisco-based WealthAI, which provides AI-powered private market analytics for family offices, has raised $12.5 million in a Series A funding round led by Sequoia Capital.</description>
      <author>Jane Reporter</author>
      <guid>https://techcrunch.com/2025/03/15/wealthai-series-a/</guid>
    </item>
    <item>
      <title>PortfolioOS secures $5M seed round for portfolio management software</title>
      <link>https://techcrunch.com/2025/04/10/portfolioos-seed/</link>
      <pubDate>Thu, 10 Apr 2025 14:00:00 +0000</pubDate>
      <description>New York-based PortfolioOS has closed a $5 million seed round led by Accel Partners to build next-generation portfolio management software for digital wealth managers.</description>
      <author>Bob Writer</author>
      <guid>https://techcrunch.com/2025/04/10/portfolioos-seed/</guid>
    </item>
    <item>
      <title>PayWidget raises $50M for payment processing</title>
      <link>https://techcrunch.com/2025/02/01/paywidget-funding/</link>
      <pubDate>Sat, 01 Feb 2025 10:00:00 +0000</pubDate>
      <description>PayWidget, a payment processing company, has raised $50M in its latest funding round.</description>
      <author>Carol Reporter</author>
      <guid>https://techcrunch.com/2025/02/01/paywidget-funding/</guid>
    </item>
  </channel>
</rss>
"""

# A minimal Atom feed simulating Inc42 Indian startup news
INC42_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Inc42</title>
  <link href="https://inc42.com/feed/" rel="self"/>
  <id>https://inc42.com/</id>
  <updated>2025-05-01T08:00:00Z</updated>
  <entry>
    <title>WealthBridge raises INR 50 crore in Series B for private market platform</title>
    <link href="https://inc42.com/buzz/wealthbridge-series-b/"/>
    <id>https://inc42.com/buzz/wealthbridge-series-b/</id>
    <published>2025-05-01T08:00:00Z</published>
    <updated>2025-05-01T08:00:00Z</updated>
    <summary>Mumbai-based WealthBridge, a private market investment platform, has raised INR 50 crore in its Series B round led by Tiger Global.</summary>
    <author><name>Priya Journalist</name></author>
  </entry>
  <entry>
    <title>AltFunds secures Rs 25 Cr angel investment for alternative investment marketplace</title>
    <link href="https://inc42.com/buzz/altfunds-angel/"/>
    <id>https://inc42.com/buzz/altfunds-angel/</id>
    <published>2025-03-20T10:00:00Z</published>
    <updated>2025-03-20T10:00:00Z</updated>
    <summary>Bengaluru-based AltFunds, which operates an alternative investment marketplace, has raised Rs 25 crore in an angel round from prominent family offices.</summary>
    <author><name>Rahul Writer</name></author>
  </entry>
</feed>
"""

# A feed entry with a date OUTSIDE the target range (before 2024-11-23)
OUT_OF_RANGE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>OldCo raises $1M seed – 2023 article</title>
      <link>https://example.com/oldco-seed/</link>
      <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
      <description>This article is from 2024 Q1, before the target range.</description>
      <guid>https://example.com/oldco-seed/</guid>
    </item>
  </channel>
</rss>
"""

# A feed with a duplicate URL (same GUID, different tracking params)
DUPLICATE_URL_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>InvestCo raises $20M Series A</title>
      <link>https://example.com/investco/?utm_source=twitter&amp;utm_medium=social</link>
      <pubDate>Mon, 01 Dec 2025 10:00:00 +0000</pubDate>
      <description>InvestCo raised $20M.</description>
      <guid>https://example.com/investco/</guid>
    </item>
    <item>
      <title>InvestCo raises $20M Series A</title>
      <link>https://example.com/investco/?utm_source=newsletter&amp;utm_medium=email</link>
      <pubDate>Mon, 01 Dec 2025 10:00:00 +0000</pubDate>
      <description>InvestCo raised $20M (duplicate).</description>
      <guid>https://example.com/investco/</guid>
    </item>
  </channel>
</rss>
"""

# A malformed RSS feed (bozo=True) – should not crash the parser
MALFORMED_RSS = """\
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Broken Feed</title>
    <item>
      <title>Article without link</title>
      <!-- No <link> tag -->
      <pubDate>Mon, 01 Jun 2025 00:00:00 +0000</pubDate>
    </item>
    <item>
      <title></title>
      <link>https://example.com/no-title/</link>
      <pubDate>Mon, 01 Jun 2025 00:00:00 +0000</pubDate>
    </item>
  </channel>
"""  # Note: no closing </rss>

# A feed with no entries
EMPTY_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <link>https://example.com</link>
    <description>No items yet</description>
  </channel>
</rss>
"""
