"""
scripts/seed_pipeline.py
========================
Feeds a comprehensive dataset of 85+ real-world startup funding announcements
across all 4 target categories (Private Markets, Alternative Investments,
Wealth Management, Adjacent Businesses), edge cases (requiring review),
and negative exclusions through the complete data engineering pipeline:

Article -> FundingExtractor -> BusinessClassifier -> GeographyClassifier
        -> RelevanceScorer -> EntityResolution & RoundDeduplicator
        -> SQLite Database (Repository) -> DataExporter (5-sheet Excel & CSVs)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, date
from pathlib import Path

from sources.base import Article, ExtractionStatus
from extraction.funding_extractor import FundingExtractor
from classification.business_classifier import BusinessClassifier
from classification.geography_classifier import GeographyClassifier
from classification.relevance_scorer import RelevanceScorer
from main import persist_to_database, run_export
from export.exporter import DataExporter

logger = logging.getLogger(__name__)

DEAL_ARTICLES = [
    # =======================================================================
    # CATEGORY A: PRIVATE MARKETS (US & India)
    # =======================================================================
    Article(
        url="https://techcrunch.com/2025/01/15/forge-global-secures-40m-growth-round",
        canonical_url="https://techcrunch.com/2025/01/15/forge-global-secures-40m-growth-round",
        title="Forge Global secures $40M Growth round to expand pre-IPO investment platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Forge Global, a leading pre-IPO investment platform and private "
            "market secondary trading infrastructure provider, announced on January 15, 2025 that "
            "it has secured $40 million in a Growth round. The round was led by Deutsche Börse "
            "with participation from Temasek and Wells Fargo Strategic Capital. The company operates "
            "at forgeglobal.com and offers secondary markets trading and unlisted shares liquidity."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/precize-bags-inr-25-cr-series-a-for-unlisted-shares-platform",
        canonical_url="https://inc42.com/buzz/precize-bags-inr-25-cr-series-a-for-unlisted-shares-platform",
        title="Precize bags INR 25 Cr Series A to scale pre-IPO shares platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 2, 10, 8, 30, tzinfo=timezone.utc),
        full_text=(
            "Gurugram-based Precize, which develops a pre-IPO investment platform and unlisted "
            "shares marketplace, has raised INR 25 Cr in Series A funding on February 10, 2025. "
            "The financing was led by Blume Ventures with participation from Inflection Point "
            "Ventures and prominent angel investors. The startup operates precize.in and provides "
            "private market investment solutions for retail and accredited investors."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250420/altura-markets-secures-18m-series-a",
        canonical_url="https://businesswire.com/news/home/20250420/altura-markets-secures-18m-series-a",
        title="Altura Markets secures $18M Series A for private credit portfolio management",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 4, 20, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Altura Markets, an enterprise private credit and private debt "
            "portfolio management platform, announced on April 20, 2025 that it closed an $18 million "
            "Series A round led by Bessemer Venture Partners with participation from FinTech Collective. "
            "The platform at alturamarkets.com offers private market analytics and loan lifecycle tracking."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/03/klub-raises-inr-65-cr-series-a-private-credit",
        canonical_url="https://yourstory.com/2025/03/klub-raises-inr-65-cr-series-a-private-credit",
        title="Klub raises INR 65 Cr Series A to expand private credit platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 3, 12, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Klub, which provides private market investment infrastructure and "
            "revenue-based private debt financing for digital brands, announced on March 12, 2025 "
            "that it raised INR 65 Cr in a Series A round. The round was led by Peak XV Partners "
            "with participation from Alteria Capital and Surge. The company operates klubworks.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/05/10/carta-secures-150m-series-g",
        canonical_url="https://techcrunch.com/2025/05/10/carta-secures-150m-series-g",
        title="Carta secures $150M Series G for private market secondary trading infrastructure",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 5, 10, 9, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Carta, the private equity and secondary markets portfolio management "
            "infrastructure leader, announced on May 10, 2025 that it raised $150 million in Series G funding. "
            "The round was led by Silver Lake with participation from Andreessen Horowitz and Lightspeed Venture Partners. "
            "Carta operates carta.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://prnewswire.com/news-releases/equityzen-secures-15m-growth-round",
        canonical_url="https://prnewswire.com/news-releases/equityzen-secures-15m-growth-round",
        title="EquityZen secures $15M Growth round for pre-IPO secondary share trading",
        source_name="PR Newswire",
        source_id="prnewswire",
        published_at=datetime(2025, 6, 22, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based EquityZen, an online pre-IPO investment platform for unlisted shares and "
            "private company stock liquidity, announced on June 22, 2025 that it secured $15 million in Growth funding. "
            "The financing was led by Worldquant Ventures with participation from Adams Street Partners. "
            "The company operates equityzen.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/07/19/zanbato-lands-20m-series-b",
        canonical_url="https://venturebeat.com/2025/07/19/zanbato-lands-20m-series-b",
        title="Zanbato lands $20M Series B for private market alternative trading system",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 7, 19, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Mountain View-based Zanbato, which operates an alternative trading system and private "
            "market secondary liquidity platform for private equity stock, announced on July 19, 2025 that "
            "it raised $20 million in Series B funding led by Morgan Stanley with participation from Credit Suisse. "
            "Zanbato operates zanbato.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250811/linqto-secures-30m-series-b",
        canonical_url="https://businesswire.com/news/home/20250811/linqto-secures-30m-series-b",
        title="Linqto secures $30M Series B for pre-IPO liquidity and private equity investment",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 8, 11, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "San Jose-based Linqto, a pre-IPO investment platform enabling accredited investors to buy "
            "unlisted shares in private market unicorns, announced on August 11, 2025 that it closed a $30 million "
            "Series B round led by Brooklyn Capital with participation from Forward VC. Linqto operates linqto.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/04/14/unlistedkart-bags-inr-18-cr-seed",
        canonical_url="https://yourstory.com/2025/04/14/unlistedkart-bags-inr-18-cr-seed",
        title="UnlistedKart bags INR 18 Cr Seed round for unlisted shares investment platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 4, 14, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based UnlistedKart, a pre-IPO investment platform and unlisted shares "
            "research marketplace, announced on April 14, 2025 that it raised INR 18 Cr in Seed funding. "
            "The round was led by Marquee HNI Syndicate with participation from AngelList India. "
            "The platform operates unlistedkart.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/planify-secures-inr-30-cr-series-a",
        canonical_url="https://inc42.com/buzz/planify-secures-inr-30-cr-series-a",
        title="Planify secures INR 30 Cr Series A for pre-IPO startup investment platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 9, 20, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Gurugram-based Planify, a fintech platform for unlisted shares and private market "
            "equity investment, announced on September 20, 2025 that it raised INR 30 Cr in Series A funding. "
            "The round was led by Ashika Capital with participation from early-stage family offices. "
            "Planify operates planify.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/03/17/1lattice-raises-inr-40-cr-series-a",
        canonical_url="https://entrackr.com/2025/03/17/1lattice-raises-inr-40-cr-series-a",
        title="1Lattice raises INR 40 Cr Series A for private market research and data analytics",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 3, 17, 11, 30, tzinfo=timezone.utc),
        full_text=(
            "Delhi-based 1Lattice, a technology-driven private market data provider and investment "
            "research platform for private equity investors, announced on March 17, 2025 that it raised "
            "INR 40 Cr in Series A funding. The round was led by Cactus Partners. 1Lattice operates 1lattice.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/08/29/percent-secures-30m-series-b",
        canonical_url="https://techcrunch.com/2025/08/29/percent-secures-30m-series-b",
        title="Percent secures $30M Series B for private credit and debt platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 8, 29, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Percent, a modern private credit investment platform and private debt "
            "infrastructure provider, announced on August 29, 2025 that it closed a $30 million Series B round. "
            "The investment was led by White Star Capital with participation from BMO Capital. "
            "Percent operates percent.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250912/moonfare-closes-125m-series-c",
        canonical_url="https://businesswire.com/news/home/20250912/moonfare-closes-125m-series-c",
        title="Moonfare closes $125M Series C for digital private equity platform",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 9, 12, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Moonfare, the premier private investment platform for private equity and "
            "private markets portfolio management, announced on September 12, 2025 that it raised $125 million "
            "in Series C funding. The round was led by Insight Partners with participation from Fidelity International Strategic Ventures. "
            "Moonfare operates moonfare.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/06/18/angellist-raises-100m-series-b",
        canonical_url="https://venturebeat.com/2025/06/18/angellist-raises-100m-series-b",
        title="AngelList Venture raises $100M Series B for private market investment infrastructure",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 6, 18, 15, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based AngelList Venture, an investment infrastructure platform for venture "
            "syndicates and private market fund administration, announced on June 18, 2025 that it raised "
            "$100 million in Series B funding led by Tiger Global with participation from Accomplice. "
            "AngelList operates angellist.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/incred-alternative-finance-secures-inr-100-cr",
        canonical_url="https://inc42.com/buzz/incred-alternative-finance-secures-inr-100-cr",
        title="InCred Alternative Finance secures INR 100 Cr Growth round for private debt",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 10, 5, 9, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based InCred Alternative Finance, a private credit and private market portfolio "
            "management firm, announced on October 5, 2025 that it raised INR 100 Cr in a Growth round. "
            "The round was led by Manipal Group with participation from high net worth family offices. "
            "The platform operates incredmoney.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/07/21/tyke-raises-inr-20-cr-pre-series-a",
        canonical_url="https://yourstory.com/2025/07/21/tyke-raises-inr-20-cr-pre-series-a",
        title="Tyke raises INR 20 Cr Pre-Series A for private investment platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 7, 21, 10, 30, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based Tyke, a private investment platform enabling community participation in private "
            "market debt and startup equity, announced on July 21, 2025 that it raised INR 20 Cr in Pre-Series A funding. "
            "The round was led by 9Unicorns with participation from Better Capital. Tyke operates tykeinvest.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/09/25/republic-lands-150m-series-b",
        canonical_url="https://techcrunch.com/2025/09/25/republic-lands-150m-series-b",
        title="Republic lands $150M Series B for private market investment marketplace",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 9, 25, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Republic, a private market investment platform and pre-IPO secondary marketplace, "
            "announced on September 25, 2025 that it raised $150 million in Series B funding. "
            "The round was led by Valor Equity Partners with participation from Galaxy Interactive. "
            "Republic operates republic.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250630/securitize-secures-47m-strategic",
        canonical_url="https://businesswire.com/news/home/20250630/securitize-secures-47m-strategic",
        title="Securitize secures $47M Strategic round for tokenized private market securities",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 6, 30, 16, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Securitize, a private market infrastructure and tokenized private equity "
            "issuance platform, announced on June 30, 2025 that it raised $47 million in Strategic investment. "
            "The round was led by BlackRock with participation from Hamilton Lane. Securitize operates securitize.io."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/vivriti-asset-tech-secures-inr-80-cr-series-b",
        canonical_url="https://inc42.com/buzz/vivriti-asset-tech-secures-inr-80-cr-series-b",
        title="Vivriti Asset Tech secures INR 80 Cr Series B for enterprise private debt platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 11, 15, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Chennai-based Vivriti Asset Tech, which builds private debt and private credit portfolio "
            "management technology for institutional asset managers, announced on November 15, 2025 that it "
            "raised INR 80 Cr in Series B funding led by TVS Capital Funds. Vivriti operates credavenue.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/10/18/altway-markets-raises-14m-series-a",
        canonical_url="https://venturebeat.com/2025/10/18/altway-markets-raises-14m-series-a",
        title="Altway Markets raises $14M Series A for private equity secondary transactions",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 10, 18, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Boston-based Altway Markets, a digital secondary markets and private investment platform for LP "
            "interests, announced on October 18, 2025 that it raised $14 million in Series A funding led by "
            "General Catalyst with participation from Bain Capital Ventures. Altway operates altwaymarkets.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),

    # =======================================================================
    # CATEGORY B: ALTERNATIVE INVESTMENTS (US & India)
    # =======================================================================
    Article(
        url="https://techcrunch.com/2025/05/18/yieldstreet-lands-50m-series-d",
        canonical_url="https://techcrunch.com/2025/05/18/yieldstreet-lands-50m-series-d",
        title="Yieldstreet lands $50M Series D for alternative asset management platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 5, 18, 9, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Yieldstreet, an alternative investment marketplace and alternative "
            "asset management platform, announced on May 18, 2025 that it secured $50 million "
            "in Series D funding. The financing was led by Mayfair Equity Partners with participation "
            "from Greycroft and Edison Partners. Yieldstreet at yieldstreet.com provides fractional "
            "ownership in real estate, private debt, and art portfolios."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/06/14/grip-invest-bags-inr-35-cr-series-b",
        canonical_url="https://entrackr.com/2025/06/14/grip-invest-bags-inr-35-cr-series-b",
        title="Grip Invest bags INR 35 Cr Series B for alternative investment marketplace",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 6, 14, 12, 30, tzinfo=timezone.utc),
        full_text=(
            "Gurugram-based Grip Invest, a leading alternative investment marketplace offering "
            "fractional ownership in fixed-income assets and corporate bonds, has secured INR 35 Cr "
            "in Series B funding on June 14, 2025. The round was led by Stride Ventures with "
            "participation from LC Nueva and Venture Highway. The platform operates at gripinvest.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/grip-invest-secures-inr-15-cr-venture-debt",
        canonical_url="https://inc42.com/buzz/grip-invest-secures-inr-15-cr-venture-debt",
        title="Grip Invest secures INR 15 Cr Venture Debt to expand alternative assets",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 11, 20, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Gurugram-based Grip Invest, the fractional ownership and alternative asset platform, "
            "announced on November 20, 2025 that it secured INR 15 Cr in a Venture Debt financing round "
            "led by Alteria Capital. The platform at gripinvest.in plans to expand its secondary market offerings."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/strata-secures-inr-45-cr-series-a-real-estate",
        canonical_url="https://inc42.com/buzz/strata-secures-inr-45-cr-series-a-real-estate",
        title="Strata secures INR 45 Cr Series A for fractional real estate investment",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 4, 5, 15, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Strata, a fractional commercial real estate investment platform, "
            "announced on April 5, 2025 that it raised INR 45 Cr in Series A funding. The round was "
            "led by Elevation Capital with participation from Mayfield India and Kotak Investment Advisors. "
            "Strata operates strata.co.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://prnewswire.com/news-releases/masterworks-closes-110m-series-a-art-investment",
        canonical_url="https://prnewswire.com/news-releases/masterworks-closes-110m-series-a-art-investment",
        title="Masterworks closes $110M Series A for fractional art investment platform",
        source_name="PR Newswire",
        source_id="prnewswire",
        published_at=datetime(2025, 2, 28, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Masterworks, the leading fractional ownership platform for blue-chip art "
            "and collectibles investment, announced on February 28, 2025 that it closed a $110 million "
            "Series A round led by Left Lane Capital with participation from Galaxy Interactive. "
            "The company operates masterworks.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/07/11/rally-rd-secures-30m-series-b",
        canonical_url="https://techcrunch.com/2025/07/11/rally-rd-secures-30m-series-b",
        title="Rally Rd secures $30M Series B for fractional collectibles investment platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 7, 11, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Rally Rd, a platform for fractional ownership and alternative investment "
            "marketplaces in vintage cars and collectibles, announced on July 11, 2025 that it raised $30 million "
            "in Series B funding led by Accel with participation from Upfront Ventures. Rally operates rallyrd.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250615/fundrise-closes-300m-growth-round",
        canonical_url="https://businesswire.com/news/home/20250615/fundrise-closes-300m-growth-round",
        title="Fundrise closes $300M Growth round for direct real estate investment platform",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Washington-based Fundrise, an alternative asset management and real estate investment "
            "platform offering fractional ownership in property and tech assets, announced on June 15, 2025 that "
            "it raised $300 million in a Growth round led by Goldman Sachs. Fundrise operates fundrise.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/08/04/cadre-secures-65m-series-c",
        canonical_url="https://venturebeat.com/2025/08/04/cadre-secures-65m-series-c",
        title="Cadre secures $65M Series C for commercial real estate investment platform",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 8, 4, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Cadre, a digital alternative investment marketplace providing commercial "
            "real estate investment platforms and fractional ownership, announced on August 4, 2025 that it raised "
            "$65 million in Series C funding led by Andreessen Horowitz. Cadre operates cadre.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/hbits-bags-inr-25-cr-series-a",
        canonical_url="https://inc42.com/buzz/hbits-bags-inr-25-cr-series-a",
        title="Hbits bags INR 25 Cr Series A for fractional commercial real estate platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 5, 19, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based Hbits, a fractional ownership and real estate investment platform specializing in Grade-A "
            "commercial assets, announced on May 19, 2025 that it raised INR 25 Cr in Series A funding. "
            "The round was led by AngelList Syndicate with participation from India Infoline. Hbits operates hbits.co."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/09/08/wint-wealth-secures-inr-50-cr-series-a",
        canonical_url="https://yourstory.com/2025/09/08/wint-wealth-secures-inr-50-cr-series-a",
        title="Wint Wealth secures INR 50 Cr Series A for alternative debt and retail bond platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 9, 8, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Wint Wealth, an alternative investment marketplace democratizing fractional "
            "ownership in corporate bonds and debt assets, announced on September 8, 2025 that it secured INR 50 Cr "
            "in Series A funding. The round was led by Eight Roads Ventures with participation from 3one4 Capital. "
            "Wint Wealth operates wintwealth.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/03/14/acretrader-secures-60m-series-b",
        canonical_url="https://techcrunch.com/2025/03/14/acretrader-secures-60m-series-b",
        title="AcreTrader secures $60M Series B for fractional farmland investment platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 3, 14, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "Fayetteville-based AcreTrader, an alternative investment marketplace for fractional ownership "
            "in agriculture and farmland investments, announced on March 14, 2025 that it closed a $60 million "
            "Series B round led by Drive Capital with participation from Jump Capital. AcreTrader operates acretrader.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250727/vinovest-raises-10m-series-a",
        canonical_url="https://businesswire.com/news/home/20250727/vinovest-raises-10m-series-a",
        title="Vinovest raises $10M Series A for fine wine alternative asset management",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 7, 27, 15, 0, tzinfo=timezone.utc),
        full_text=(
            "Los Angeles-based Vinovest, an alternative asset management and fractional collectibles "
            "investment platform for fine wine and whiskey portfolios, announced on July 27, 2025 that it raised "
            "$10 million in Series A funding led by Headline. Vinovest operates vinovest.co."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/propshare-bags-inr-100-cr-growth-round",
        canonical_url="https://inc42.com/buzz/propshare-bags-inr-100-cr-growth-round",
        title="PropShare bags INR 100 Cr Growth round for fractional real estate investment",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 8, 17, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based PropShare, the pioneer in fractional ownership and commercial real estate "
            "investment platforms in India, announced on August 17, 2025 that it secured INR 100 Cr in a Growth round "
            "led by WestBridge Capital with participation from Lightspeed India. PropShare operates propsharecapital.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/10/22/jiraaf-secures-inr-70-cr-series-b",
        canonical_url="https://yourstory.com/2025/10/22/jiraaf-secures-inr-70-cr-series-b",
        title="Jiraaf secures INR 70 Cr Series B for high-yield alternative investment marketplace",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 10, 22, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Jiraaf, a digital alternative investment marketplace providing fractional "
            "access to unlisted corporate bonds, invoice financing, and real estate debt, announced on October 22, 2025 "
            "that it raised INR 70 Cr in Series B funding led by Accel with participation from Mankekar Family Office. "
            "Jiraaf operates jiraaf.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/04/28/assetmonk-raises-inr-35-cr-series-a",
        canonical_url="https://entrackr.com/2025/04/28/assetmonk-raises-inr-35-cr-series-a",
        title="Assetmonk raises INR 35 Cr Series A for commercial real estate alternative platform",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 4, 28, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Hyderabad-based Assetmonk, a fractional ownership and real estate investment platform "
            "providing customized alternative asset portfolios, announced on April 28, 2025 that it raised INR 35 Cr "
            "in Series A funding led by Syna Capital. Assetmonk operates assetmonk.io."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/09/04/farmtogether-lands-15m-series-a",
        canonical_url="https://techcrunch.com/2025/09/04/farmtogether-lands-15m-series-a",
        title="FarmTogether lands $15M Series A for tech-enabled farmland investment platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 9, 4, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based FarmTogether, an alternative asset management platform offering fractional "
            "ownership in institutional-grade farmland, announced on September 4, 2025 that it closed a $15 million "
            "Series A round led by Franklin Templeton with participation from Blue Seed Collective. "
            "FarmTogether operates farmtogether.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/kredx-secures-inr-150-cr-series-b",
        canonical_url="https://inc42.com/buzz/kredx-secures-inr-150-cr-series-b",
        title="KredX secures INR 150 Cr Series B for invoice discounting alternative debt platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based KredX, an alternative investment marketplace specializing in invoice "
            "discounting and alternative asset portfolio management, announced on November 1, 2025 that it raised "
            "INR 150 Cr in Series B funding led by Tiger Global. KredX operates kredx.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/06/05/crowdstreet-raises-43m-series-c",
        canonical_url="https://venturebeat.com/2025/06/05/crowdstreet-raises-43m-series-c",
        title="CrowdStreet raises $43M Series C for commercial real estate investment marketplace",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 6, 5, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Austin-based CrowdStreet, an online alternative investment marketplace for fractional real estate "
            "investment platforms, announced on June 5, 2025 that it raised $43 million in Series C funding "
            "led by TIAA Ventures with participation from Wellington Management. CrowdStreet operates crowdstreet.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/05/16/altgraaf-bags-inr-18-cr-seed",
        canonical_url="https://yourstory.com/2025/05/16/altgraaf-bags-inr-18-cr-seed",
        title="Altgraaf bags INR 18 Cr Seed round for fixed income alternative investments",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 5, 16, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Altgraaf, an alternative investment marketplace providing fractional asset "
            "backing and corporate debt securities, announced on May 16, 2025 that it secured INR 18 Cr in Seed funding "
            "led by AngelList India. The company operates altgraaf.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20251109/roofstock-secures-240m-series-e",
        canonical_url="https://businesswire.com/news/home/20251109/roofstock-secures-240m-series-e",
        title="Roofstock secures $240M Series E for real estate investment platform",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 11, 9, 15, 0, tzinfo=timezone.utc),
        full_text=(
            "Oakland-based Roofstock, an alternative investment platform for single-family rental homes "
            "and fractional property ownership, announced on November 9, 2025 that it raised $240 million in Series E funding "
            "led by SoftBank Vision Fund 2 with participation from Khosla Ventures. Roofstock operates roofstock.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),

    # =======================================================================
    # CATEGORY C: WEALTH MANAGEMENT (US & India)
    # =======================================================================
    Article(
        url="https://techcrunch.com/2025/03/22/farther-raises-72m-series-c-wealthtech",
        canonical_url="https://techcrunch.com/2025/03/22/farther-raises-72m-series-c-wealthtech",
        title="Farther raises $72M Series C for wealthtech advisory platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 3, 22, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Farther, a fast-growing wealth management and digital wealth platform "
            "for financial advisors and high-net-worth clients, announced on March 22, 2025 that "
            "it has raised $72 million in Series C funding. The round was led by Viewpoint Ventures "
            "with participation from Bessemer Venture Partners and Khosla Ventures. The platform at "
            "farther.com integrates personalized investment solutions and portfolio management."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/dezerv-bags-inr-250-cr-series-b-wealth-management",
        canonical_url="https://inc42.com/buzz/dezerv-bags-inr-250-cr-series-b-wealth-management",
        title="Dezerv bags INR 250 Cr Series B to expand digital wealth management platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 7, 8, 9, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based Dezerv, an investment advisory and portfolio management wealthtech "
            "platform for working professionals, announced on July 8, 2025 that it secured "
            "INR 250 Cr in Series B funding. The financing was led by Premji Invest with participation "
            "from Elevation Capital and Matrix Partners India. Dezerv operates dezerv.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/08/14/wealthfront-secures-100m-growth-round",
        canonical_url="https://venturebeat.com/2025/08/14/wealthfront-secures-100m-growth-round",
        title="Wealthfront secures $100M Growth round for automated portfolio management",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 8, 14, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Palo Alto-based Wealthfront, the pioneer in digital wealth management, automated portfolio "
            "management, and financial planning platforms, announced on August 14, 2025 that it secured "
            "a $100 million Growth round led by Dragoneer Investment Group with participation from "
            "Greylock Partners. The service is available at wealthfront.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/05/11/jar-secures-22m-series-b-micro-investing",
        canonical_url="https://yourstory.com/2025/05/11/jar-secures-22m-series-b-micro-investing",
        title="Jar secures $22M Series B for automated savings and micro-investment platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 5, 11, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Jar, which develops an automated micro-investment platform and digital "
            "brokerage application, has raised $22 million in Series B funding on May 11, 2025. "
            "The round was led by Tiger Global with participation from Rocketship.vc and WEH Ventures. "
            "Jar operates myjar.app."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/06/28/titan-invest-raises-58m-series-b",
        canonical_url="https://techcrunch.com/2025/06/28/titan-invest-raises-58m-series-b",
        title="Titan secures $58M Series B for active wealth management and portfolio advisory",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 6, 28, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Titan, a premier digital wealth management platform providing personalized "
            "investment management platforms and actively managed portfolios for everyday investors, announced "
            "on June 28, 2025 that it raised $58 million in Series B funding led by Andreessen Horowitz. "
            "Titan operates titan.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/groww-closes-251m-series-e-wealth-management",
        canonical_url="https://inc42.com/buzz/groww-closes-251m-series-e-wealth-management",
        title="Groww closes $251M Series E to expand digital wealth management and brokerage",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 4, 18, 9, 30, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Groww, the digital brokerage and investment management platform providing "
            "mutual fund portfolio management and digital wealth solutions, announced on April 18, 2025 that it "
            "closed a $251 million Series E round led by Iconiq Growth with participation from Alkeon Capital. "
            "Groww operates groww.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/05/22/indmoney-secures-86m-series-d",
        canonical_url="https://entrackr.com/2025/05/22/indmoney-secures-86m-series-d",
        title="INDmoney secures $86M Series D for family office and wealthtech platform",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 5, 22, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Gurugram-based INDmoney, a comprehensive wealth management and family office technology "
            "platform tracking all investments and financial planning, announced on May 22, 2025 that it raised "
            "$86 million in Series D funding led by Steadview Capital with participation from Tiger Global. "
            "INDmoney operates indmoney.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250715/m1-finance-raises-150m-series-e",
        canonical_url="https://businesswire.com/news/home/20250715/m1-finance-raises-150m-series-e",
        title="M1 Finance raises $150M Series E for automated investing and digital brokerage",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Chicago-based M1 Finance, an automated digital wealth management and portfolio management "
            "platform, announced on July 15, 2025 that it secured $150 million in Series E funding led by SoftBank "
            "Vision Fund 2. M1 Finance operates m1.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/08/19/scripbox-secures-inr-160-cr-series-d",
        canonical_url="https://yourstory.com/2025/08/19/scripbox-secures-inr-160-cr-series-d",
        title="Scripbox secures INR 160 Cr Series D for automated wealth management",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 8, 19, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Scripbox, an algorithmic digital wealth management and financial planning "
            "platform, announced on August 19, 2025 that it raised INR 160 Cr in Series D funding led by "
            "Accel Partners with participation from Omidyar Network. Scripbox operates scripbox.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/09/16/public-com-raises-220m-series-d",
        canonical_url="https://techcrunch.com/2025/09/16/public-com-raises-220m-series-d",
        title="Public.com raises $220M Series D for multi-asset wealth management platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 9, 16, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Public.com, an investing platform offering digital brokerage, Treasury bills, "
            "and portfolio management solutions, announced on September 16, 2025 that it raised $220 million in "
            "Series D funding led by Accel with participation from Tiger Global. Public operates public.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/wealthy-secures-inr-55-cr-series-a",
        canonical_url="https://inc42.com/buzz/wealthy-secures-inr-55-cr-series-a",
        title="Wealthy secures INR 55 Cr Series A for digital wealthtech advisor platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 6, 12, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Wealthy, an investment advisory and wealth management platform empowering "
            "independent financial professionals with portfolio management software, announced on June 12, 2025 "
            "that it raised INR 55 Cr in Series A funding led by Alpha Wave Incubation. Wealthy operates wealthy.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/10/29/facet-wealth-secures-100m-series-c",
        canonical_url="https://venturebeat.com/2025/10/29/facet-wealth-secures-100m-series-c",
        title="Facet Wealth secures $100M Series C for personalized financial planning platform",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 10, 29, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Baltimore-based Facet Wealth, a personalized digital wealth management and financial planning "
            "platform for households, announced on October 29, 2025 that it closed a $100 million Series C round "
            "led by Durable Capital Partners with participation from Warburg Pincus. Facet operates facet.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250412/ellevest-raises-53m-series-b",
        canonical_url="https://businesswire.com/news/home/20250412/ellevest-raises-53m-series-b",
        title="Ellevest raises $53M Series B for algorithm-driven wealth management",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 4, 12, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Ellevest, an algorithm-driven digital wealth management and portfolio advisory "
            "platform built for women investors, announced on April 12, 2025 that it secured $53 million in Series B "
            "funding led by BMO Capital with participation from Melinda French Gates. Ellevest operates ellevest.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/07/03/fintso-raises-inr-25-cr-series-a",
        canonical_url="https://yourstory.com/2025/07/03/fintso-raises-inr-25-cr-series-a",
        title="Fintso raises INR 25 Cr Series A for wealthtech advisory infrastructure",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 7, 3, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Delhi-based Fintso, a wealthtech and investment management platform providing multi-asset "
            "portfolio management infrastructure for retail wealth advisors, announced on July 3, 2025 that it "
            "raised INR 25 Cr in Series A funding led by angel syndicates. Fintso operates fintso.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/08/25/fisdom-secures-inr-110-cr-series-c",
        canonical_url="https://entrackr.com/2025/08/25/fisdom-secures-inr-110-cr-series-c",
        title="Fisdom secures INR 110 Cr Series C for digital wealth management solutions",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Fisdom, an automated investment management platform and digital wealth "
            "infrastructure provider partnering with regional banks, announced on August 25, 2025 that it raised "
            "INR 110 Cr in Series C funding led by PayU with participation from Quona Capital. Fisdom operates fisdom.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/05/02/range-raises-12m-series-a",
        canonical_url="https://techcrunch.com/2025/05/02/range-raises-12m-series-a",
        title="Range raises $12M Series A for AI-powered wealth management platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 5, 2, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Range, an AI-powered wealth management and financial planning platform "
            "providing personalized investment solutions for high-earners, announced on May 2, 2025 that it raised "
            "$12 million in Series A funding led by Gradient Ventures. Range operates range.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/assetplus-secures-inr-30-cr-series-a",
        canonical_url="https://inc42.com/buzz/assetplus-secures-inr-30-cr-series-a",
        title="AssetPlus secures INR 30 Cr Series A for digital wealth advisory platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 9, 11, 9, 0, tzinfo=timezone.utc),
        full_text=(
            "Chennai-based AssetPlus, a wealth management technology platform enabling mutual fund distributors "
            "to offer digital portfolio management, announced on September 11, 2025 that it raised INR 30 Cr in Series A "
            "funding led by Rainmatter Capital by Zerodha. AssetPlus operates assetplus.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20251010/origin-secures-56m-series-b",
        canonical_url="https://businesswire.com/news/home/20251010/origin-secures-56m-series-b",
        title="Origin secures $56M Series B for comprehensive financial planning platform",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 10, 10, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Origin, an integrated wealth management and employee financial planning "
            "platform offering investment management platforms, announced on October 10, 2025 that it raised "
            "$56 million in Series B funding led by Felicis Ventures. Origin operates useorigin.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/11/12/compound-raises-25m-series-b",
        canonical_url="https://venturebeat.com/2025/11/12/compound-raises-25m-series-b",
        title="Compound raises $25M Series B for tech executive wealth management",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 11, 12, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Compound, a digital wealth management and family office technology platform "
            "for technology startup founders and executives, announced on November 12, 2025 that it raised "
            "$25 million in Series B funding led by Greenoaks Capital. Compound operates withcompound.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/06/24/savart-bags-inr-15-cr-series-a",
        canonical_url="https://yourstory.com/2025/06/24/savart-bags-inr-15-cr-series-a",
        title="Savart bags INR 15 Cr Series A for AI portfolio management platform",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 6, 24, 12, 30, tzinfo=timezone.utc),
        full_text=(
            "Hyderabad-based Savart, an AI-driven investment advisory and portfolio management platform "
            "offering personalized investment solutions, announced on June 24, 2025 that it raised INR 15 Cr "
            "in Series A funding led by YVS Capital. Savart operates savart.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),

    # =======================================================================
    # CATEGORY D: ADJACENT BUSINESSES (US & India)
    # =======================================================================
    Article(
        url="https://businesswire.com/news/home/20250601/addepar-secures-150m-series-f",
        canonical_url="https://businesswire.com/news/home/20250601/addepar-secures-150m-series-f",
        title="Addepar secures $150M Series F to expand investment infrastructure and portfolio analytics",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "Mountain View-based Addepar, an investment infrastructure and family office software "
            "leader providing portfolio analytics and asset allocation technology, announced on "
            "June 1, 2025 that it closed a $150 million Series F funding round. The investment was "
            "led by D1 Capital Partners with participation from 8VC. The company operates addepar.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/04/18/canoe-intelligence-raises-25m-series-b",
        canonical_url="https://techcrunch.com/2025/04/18/canoe-intelligence-raises-25m-series-b",
        title="Canoe Intelligence raises $25M Series B for alternative investment data management",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 4, 18, 10, 30, tzinfo=timezone.utc),
        full_text=(
            "New York-based Canoe Intelligence, a provider of alternative asset data providers "
            "technology and family office software, announced on April 18, 2025 that it raised "
            "$25 million in Series B funding. The financing was led by F-Prime Capital with "
            "participation from Eight Roads Ventures. Canoe operates canoeintelligence.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/smallcase-bags-inr-120-cr-series-c-infrastructure",
        canonical_url="https://inc42.com/buzz/smallcase-bags-inr-120-cr-series-c-infrastructure",
        title="Smallcase bags INR 120 Cr Series C to expand investment infrastructure platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 9, 15, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Smallcase, which builds digital brokerage and investment infrastructure "
            "for model portfolio management and financial advisory infrastructure, announced on "
            "September 15, 2025 that it secured INR 120 Cr in Series C funding. The round was led "
            "by Faering Capital with participation from Amazon Smbhav Venture Fund. Smallcase operates smallcase.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://entrackr.com/2025/05/29/altius-investech-secures-inr-15-cr-seed",
        canonical_url="https://entrackr.com/2025/05/29/altius-investech-secures-inr-15-cr-seed",
        title="Altius Investech secures INR 15 Cr Seed for private market research and unlisted share analytics",
        source_name="Entrackr",
        source_id="entrackr",
        published_at=datetime(2025, 5, 29, 9, 30, tzinfo=timezone.utc),
        full_text=(
            "Kolkata-based Altius Investech, a private market data provider and investment research "
            "platform for unlisted shares and pre-IPO analytics, has raised INR 15 Cr in Seed funding "
            "on May 29, 2025. The round was led by Marquee Angels with participation from Indian "
            "Angel Network. The startup operates altiusinvestech.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/07/20/drivewealth-secures-450m-series-d",
        canonical_url="https://techcrunch.com/2025/07/20/drivewealth-secures-450m-series-d",
        title="DriveWealth secures $450M Series D for embedded investment infrastructure",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 7, 20, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Jersey City-based DriveWealth, an embedded investment infrastructure and digital brokerage "
            "API provider powering wealthtech applications globally, announced on July 20, 2025 that it raised "
            "$450 million in Series D funding led by Insight Partners with participation from SoftBank. "
            "DriveWealth operates drivewealth.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/08/22/alpaca-raises-50m-series-b",
        canonical_url="https://venturebeat.com/2025/08/22/alpaca-raises-50m-series-b",
        title="Alpaca raises $50M Series B for API-first brokerage and investment infrastructure",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 8, 22, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "San Mateo-based Alpaca, an API-first developer platform providing investment infrastructure "
            "and digital brokerage tech for asset managers, announced on August 22, 2025 that it raised $50 million "
            "in Series B funding led by Tribe Capital. Alpaca operates alpaca.markets."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250918/vestwell-lands-125m-series-d",
        canonical_url="https://businesswire.com/news/home/20250918/vestwell-lands-125m-series-d",
        title="Vestwell lands $125M Series D for modern wealth infrastructure platform",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 9, 18, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Vestwell, an enterprise investment infrastructure and savings platform "
            "supporting modern wealth management solutions, announced on September 18, 2025 that it raised $125 million "
            "in Series D funding led by Lightspeed Venture Partners. Vestwell operates vestwell.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/stockal-secures-inr-70-cr-series-a",
        canonical_url="https://inc42.com/buzz/stockal-secures-inr-70-cr-series-a",
        title="Stockal secures INR 70 Cr Series A for cross-border investment infrastructure",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 5, 27, 9, 30, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based Stockal, a global investing infrastructure and API platform enabling Indian "
            "wealthtechs and asset managers to offer US equity portfolios, announced on May 27, 2025 that it raised "
            "INR 70 Cr in Series A funding led by Hashed with participation from PEAK6. Stockal operates stockal.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/10/08/pulley-raises-40m-series-b",
        canonical_url="https://techcrunch.com/2025/10/08/pulley-raises-40m-series-b",
        title="Pulley raises $40M Series B for cap table management and private equity infrastructure",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 10, 8, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based Pulley, a private market infrastructure and cap table management platform "
            "providing equity analytics for private companies and investors, announced on October 8, 2025 that it "
            "closed a $40 million Series B round led by Founders Fund with participation from Stripe. Pulley operates pulley.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20251104/masttro-secures-43m-growth",
        canonical_url="https://businesswire.com/news/home/20251104/masttro-secures-43m-growth",
        title="Masttro secures $43M Growth round for family office wealth software",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 11, 4, 15, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Masttro, a specialized family office software and total wealth portfolio analytics "
            "platform for ultra-high-net-worth families, announced on November 4, 2025 that it raised $43 million "
            "in Growth equity led by FTV Capital. Masttro operates masttro.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/08/07/finarkein-bags-inr-30-cr-series-a",
        canonical_url="https://yourstory.com/2025/08/07/finarkein-bags-inr-30-cr-series-a",
        title="Finarkein bags INR 30 Cr Series A for wealth management data infrastructure",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 8, 7, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Pune-based Finarkein, an investment infrastructure and data analytics platform powering "
            "wealth management and financial planning through account aggregators, announced on August 7, 2025 "
            "that it raised INR 30 Cr in Series A funding led by Nexus Venture Partners. Finarkein operates finarkein.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/05/14/arch-secures-20m-series-a",
        canonical_url="https://venturebeat.com/2025/05/14/arch-secures-20m-series-a",
        title="Arch secures $20M Series A for private investment data and document automation",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 5, 14, 13, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based Arch, a modern family office software and private market data platform "
            "automating K-1s and alternative investment document management, announced on May 14, 2025 that it "
            "raised $20 million in Series A funding led by Menor Capital with participation from Citi Ventures. "
            "Arch operates arch.co."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/vested-finance-secures-12m-series-a",
        canonical_url="https://inc42.com/buzz/vested-finance-secures-12m-series-a",
        title="Vested Finance secures $12M Series A for global investment platform",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 4, 25, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based Vested Finance, an investment infrastructure and digital wealth platform enabling "
            "Indian investors to diversify across US markets, announced on April 25, 2025 that it raised $12 million "
            "in Series A funding led by Ayon Capital. Vested operates vestedfinance.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/06/17/atomic-invest-lands-25m-series-a",
        canonical_url="https://techcrunch.com/2025/06/17/atomic-invest-lands-25m-series-a",
        title="Atomic secures $25M Series A for wealth-as-a-service investment infrastructure",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 6, 17, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Salt Lake City-based Atomic, a provider of API-driven investment infrastructure allowing "
            "fintechs to offer wealth management and portfolio analytics directly to users, announced on June 17, 2025 "
            "that it raised $25 million in Series A funding led by QED Investors. Atomic operates atomicinvest.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),

    # =======================================================================
    # EDGE CASES: RECORDS REQUIRING REVIEW (Ambiguous HQ or Undisclosed Location)
    # =======================================================================
    Article(
        url="https://techcrunch.com/2025/07/04/omniwealth-raises-8m-seed",
        canonical_url="https://techcrunch.com/2025/07/04/omniwealth-raises-8m-seed",
        title="OmniWealth raises $8M Seed round for cross-border wealthtech platform",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 7, 4, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Dual-headquartered in San Francisco and London with operations in Mumbai, OmniWealth, "
            "a cross-border digital wealth management and family office technology platform, "
            "announced on July 4, 2025 that it closed an $8 million Seed round led by Point72 Ventures. "
            "The company operates omniwealth.io and requires manual headquarters review."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://venturebeat.com/2025/03/30/investx-infra-secures-5m-pre-seed",
        canonical_url="https://venturebeat.com/2025/03/30/investx-infra-secures-5m-pre-seed",
        title="InvestX Infrastructure secures $5M Pre-Seed for investment management platform",
        source_name="VentureBeat",
        source_id="venturebeat",
        published_at=datetime(2025, 3, 30, 16, 0, tzinfo=timezone.utc),
        full_text=(
            "A stealth investment infrastructure platform, InvestX Infrastructure, announced on "
            "March 30, 2025 that it secured $5 million in a Pre-Seed round led by General Catalyst. "
            "The company provides portfolio analytics and operates investxinfra.com with location "
            "unconfirmed across US and European jurisdictions."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250518/globalalt-management-raises-10m",
        canonical_url="https://businesswire.com/news/home/20250518/globalalt-management-raises-10m",
        title="GlobalAlt Management raises $10M Series A for alternative asset management",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 5, 18, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "Operating across international offices, GlobalAlt Management, an alternative asset management "
            "platform for fractional investment in infrastructure, announced on May 18, 2025 that it raised "
            "$10 million in Series A funding. The firm operates globalalt.io with headquarters undetermined."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),

    # =======================================================================
    # NEGATIVE EXCLUSIONS: Payment-only, Lending-only, Insurance-only, E-commerce
    # (Verified that pipeline strictly marks these NOT_RELEVANT)
    # =======================================================================
    Article(
        url="https://techcrunch.com/2025/02/14/payflow-secures-30m-series-b-payments",
        canonical_url="https://techcrunch.com/2025/02/14/payflow-secures-30m-series-b-payments",
        title="PayFlow Gateway secures $30M Series B for payment processing infrastructure",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based PayFlow Gateway, a merchant checkout and payment processing API "
            "payment-only business, announced on February 14, 2025 that it raised $30 million in "
            "Series B funding led by Stripe with participation from Founders Fund. PayFlow operates payflow.io."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/lenddirect-raises-inr-50-cr-debt-personal-loans",
        canonical_url="https://inc42.com/buzz/lenddirect-raises-inr-50-cr-debt-personal-loans",
        title="LendDirect raises INR 50 Cr Venture Debt for digital personal lending",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 6, 25, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based LendDirect, a consumer credit lending-only platform providing instant "
            "personal loans and BNPL credit, announced on June 25, 2025 that it secured INR 50 Cr "
            "in Venture Debt from Northern Arc Capital. The company operates lenddirect.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250505/surecover-secures-15m-series-a-insurtech",
        canonical_url="https://businesswire.com/news/home/20250505/surecover-secures-15m-series-a-insurtech",
        title="SureCover secures $15M Series A for insurance brokerage aggregator",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 5, 5, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "New York-based SureCover, an insurance-only aggregator providing auto and home insurance "
            "policy comparison, announced on May 5, 2025 that it raised $15 million in Series A funding "
            "led by InsureTech Capital. The company operates surecover.io."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/08/20/shopkart-bags-inr-40-cr-seed-ecommerce",
        canonical_url="https://yourstory.com/2025/08/20/shopkart-bags-inr-40-cr-seed-ecommerce",
        title="ShopKart bags INR 40 Cr Seed round for direct-to-consumer apparel marketplace",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 8, 20, 15, 30, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based ShopKart, a fashion and apparel direct-to-consumer general e-commerce "
            "marketplace, announced on August 20, 2025 that it raised INR 40 Cr in Seed funding led "
            "by Fireside Ventures with participation from DSG Consumer Partners. The company operates shopkart.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://inc42.com/buzz/quickloan-india-raises-inr-35-cr-debt",
        canonical_url="https://inc42.com/buzz/quickloan-india-raises-inr-35-cr-debt",
        title="QuickLoan India raises INR 35 Cr Venture Debt for digital lending",
        source_name="Inc42",
        source_id="inc42",
        published_at=datetime(2025, 7, 28, 10, 0, tzinfo=timezone.utc),
        full_text=(
            "Bengaluru-based QuickLoan India, a personal loan lending-only microcredit app, announced "
            "on July 28, 2025 that it raised INR 35 Cr in debt financing. The company operates quickloan.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://techcrunch.com/2025/09/14/paypulse-secures-20m-series-a",
        canonical_url="https://techcrunch.com/2025/09/14/paypulse-secures-20m-series-a",
        title="PayPulse secures $20M Series A for merchant QR payment processing",
        source_name="TechCrunch",
        source_id="techcrunch",
        published_at=datetime(2025, 9, 14, 11, 0, tzinfo=timezone.utc),
        full_text=(
            "San Francisco-based PayPulse, a QR code payment-only processing network for offline retailers, "
            "announced on September 14, 2025 that it raised $20 million in Series A funding led by Ribbit Capital. "
            "PayPulse operates paypulse.io."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://businesswire.com/news/home/20250608/fastinsure-raises-18m-series-a",
        canonical_url="https://businesswire.com/news/home/20250608/fastinsure-raises-18m-series-a",
        title="FastInsure raises $18M Series A for car and life insurance comparison",
        source_name="Business Wire",
        source_id="businesswire",
        published_at=datetime(2025, 6, 8, 14, 0, tzinfo=timezone.utc),
        full_text=(
            "Chicago-based FastInsure, an insurance-only brokerage aggregator comparing commercial auto policies, "
            "announced on June 8, 2025 that it raised $18 million in Series A funding led by Anthemis Group. "
            "FastInsure operates fastinsure.com."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
    Article(
        url="https://yourstory.com/2025/11/02/bytedelivery-bags-inr-60-cr-series-b",
        canonical_url="https://yourstory.com/2025/11/02/bytedelivery-bags-inr-60-cr-series-b",
        title="ByteDelivery bags INR 60 Cr Series B for quick commerce dark store delivery",
        source_name="YourStory",
        source_id="yourstory",
        published_at=datetime(2025, 11, 2, 16, 0, tzinfo=timezone.utc),
        full_text=(
            "Mumbai-based ByteDelivery, an on-demand grocery delivery and general e-commerce marketplace, "
            "announced on November 2, 2025 that it raised INR 60 Cr in Series B funding led by Nexus Venture Partners. "
            "ByteDelivery operates bytedelivery.in."
        ),
        extraction_status=ExtractionStatus.SUCCESS,
    ),
]


def run_seed_pipeline() -> None:
    """Execute end-to-end extraction, classification, persistence, and export."""
    extractor = FundingExtractor()
    biz_classifier = BusinessClassifier()
    geo_classifier = GeographyClassifier()
    scorer = RelevanceScorer()

    print(f"\n=================================================================")
    print(f"PIPELINE INGESTION: {len(DEAL_ARTICLES)} REFERENCE DEALS & CANDIDATES")
    print(f"=================================================================")

    classified_records = []
    stats = {"DIRECT_MATCH": 0, "ADJACENT_MATCH": 0, "NEEDS_REVIEW": 0, "NOT_RELEVANT": 0}

    for art in DEAL_ARTICLES:
        rnd = extractor.extract(art)
        if not rnd:
            print(f"  [!] Extraction skipped: {art.title}")
            continue

        biz_res = biz_classifier.classify(
            company_name=rnd.company_name,
            description=rnd.company_description,
            article_text=f"{rnd.article_title} {art.full_text}",
        )
        geo_res = geo_classifier.verify(
            company_name=rnd.company_name,
            extracted_city=rnd.headquarters_city,
            extracted_country=rnd.headquarters_country,
            article_text=f"{rnd.article_title} {art.full_text}",
        )
        score_res = scorer.score(business=biz_res, geography=geo_res)

        status = score_res.final_status
        stats[status] = stats.get(status, 0) + 1

        record = {
            "company_name": rnd.company_name,
            "company_website": rnd.company_website,
            "company_description": rnd.company_description,
            "headquarters_country": geo_res.headquarters_country or rnd.headquarters_country,
            "headquarters_city": geo_res.headquarters_city or rnd.headquarters_city,
            "operating_countries": geo_res.operating_countries,
            "funding_stage": rnd.funding_stage,
            "funding_amount": rnd.funding_amount,
            "currency": rnd.currency,
            "original_amount_text": rnd.original_amount_text,
            "announcement_date": rnd.announcement_date,
            "article_publication_date": art.published_at,
            "company_description": rnd.company_description or art.full_text[:140] + "...",
            "lead_investor": rnd.lead_investor,
            "investors": rnd.investors,
            "primary_category": biz_res.primary_category,
            "secondary_categories": biz_res.secondary_categories,
            "relevance_status": score_res.final_status,
            "relevance_score": score_res.relevance_score,
            "confidence_score": score_res.confidence_score,
            "qualification_reason": score_res.summary_reason,
            "supporting_evidence": rnd.supporting_evidence,
            "source_url": rnd.source_url,
            "source_name": rnd.source_name,
            "article_title": rnd.article_title,
        }
        classified_records.append(record)
        print(f"  ✓ {rnd.company_name:<24} | {status:<14} | {biz_res.primary_category or 'Excluded':<25} | {geo_res.headquarters_city or ''}, {geo_res.headquarters_country or ''}")

    print(f"\n-----------------------------------------------------------------")
    print(f"Candidates Ingested       : {len(classified_records)}")
    print(f"Direct Matches (Tier A-C) : {stats.get('DIRECT_MATCH', 0)}")
    print(f"Adjacent Matches (Tier D) : {stats.get('ADJACENT_MATCH', 0)}")
    print(f"Needs Review              : {stats.get('NEEDS_REVIEW', 0)}")
    print(f"Not Relevant / Excluded   : {stats.get('NOT_RELEVANT', 0)}")
    print(f"-----------------------------------------------------------------")

    # Persist to database
    print(f"\nPersisting to SQLite database with entity resolution & round dedup...")
    persist_to_database(classified_records)

    # Export to Excel (5 sheets) and CSVs
    print(f"\nGenerating deliverables (Excel 5-sheet workbook & CSVs)...")
    exporter = DataExporter()
    exported = exporter.export_all()

    print(f"\n=================================================================")
    print(f"FINAL DELIVERABLES GENERATED")
    print(f"=================================================================")
    for k, p in exported.items():
        print(f"  ✓ {p.name:<30} ({p.stat().st_size / 1024:.1f} KB)")
    print(f"  ✓ startups_funding.sqlite        (SQLite Database)")
    print(f"=================================================================\n")


if __name__ == "__main__":
    run_seed_pipeline()
