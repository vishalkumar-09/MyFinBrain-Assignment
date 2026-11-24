"""
tests/test_amount_parser.py
===========================
Unit tests for funding amount extraction and currency normalization.

Tests cover:
- Standard USD amounts ($10M, $12.5 million, USD 20 million, $1.2B)
- Indian rupee amounts (₹50 crore, INR 25 Cr, Rs. 10 crore, Rs 50 lakh)
- European currencies (€5 million, £8 million)
- Undisclosed funding rounds
- Negative cases: VC firm raising a fund (not a startup round)
- Negative cases: Valuations and revenues discarded
"""

from __future__ import annotations

import pytest
from extraction.amount_parser import extract_funding_amount, parse_numeric_amount, normalize_currency


class TestAmountParsingUSD:

    def test_parse_10m_dollar(self):
        text = "WealthAI has raised $10M in fresh funding."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 10_000_000.0
        assert res.currency == "USD"
        assert res.raw_text == "$10M"
        assert not res.is_undisclosed

    def test_parse_12_point_5_million(self):
        text = "The startup secured $12.5 million in Series A funding."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 12_500_000.0
        assert res.currency == "USD"

    def test_parse_usd_code(self):
        text = "PrivateMarkets Inc announced USD 20 million funding round."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 20_000_000.0
        assert res.currency == "USD"

    def test_parse_billion_dollars(self):
        text = "GiantCorp bags $1.2 billion growth investment."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 1_200_000_000.0
        assert res.currency == "USD"


class TestAmountParsingINR:

    def test_parse_50_crore_rupee_symbol(self):
        text = "WealthBridge bags ₹50 crore in Series B funding."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 500_000_000.0  # 50 * 10^7
        assert res.currency == "INR"
        assert "50 crore" in res.raw_text.lower() or "₹50" in res.raw_text

    def test_parse_inr_code_cr(self):
        text = "AltFunds closes INR 25 Cr seed investment round."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 250_000_000.0
        assert res.currency == "INR"

    def test_parse_rs_crore(self):
        text = "Fintech platform lands Rs. 10 crore from angel investors."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 100_000_000.0
        assert res.currency == "INR"

    def test_parse_lakh(self):
        text = "Early-stage venture secures Rs 50 lakh pre-seed check."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 5_000_000.0  # 50 * 10^5
        assert res.currency == "INR"


class TestAmountParsingOtherCurrencies:

    def test_parse_eur(self):
        text = "European wealthtech raises €5 million seed round."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 5_000_000.0
        assert res.currency == "EUR"

    def test_parse_gbp(self):
        text = "London-based asset manager secures £8 million funding."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.amount == 8_000_000.0
        assert res.currency == "GBP"


class TestUndisclosedAndEdgeCases:

    def test_undisclosed_funding(self):
        text = "AdvisoryOS raises undisclosed funding from prominent angels."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.is_undisclosed is True
        assert res.amount is None

    def test_undisclosed_amount(self):
        text = "InvestCo secured an undisclosed amount in a seed round."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.is_undisclosed is True

    def test_vc_raising_fund_distinguished(self):
        """A VC firm raising a new venture fund must be flagged."""
        text = "Peak XV Partners closes its $100M second fund for early-stage investments."
        res = extract_funding_amount(text)
        assert res is not None
        assert res.is_vc_fund_raise is True

    def test_valuation_not_parsed_as_funding(self):
        """Valuation metrics should not be parsed as funding amounts."""
        text = "The startup was valued at $1B following strong revenue growth."
        res = extract_funding_amount(text)
        # Should not extract the valuation as a funding round amount
        assert res is None or res.amount != 1_000_000_000.0

    def test_currency_normalization(self):
        assert normalize_currency("$") == "USD"
        assert normalize_currency("usd") == "USD"
        assert normalize_currency("₹") == "INR"
        assert normalize_currency("inr") == "INR"
        assert normalize_currency("rs.") == "INR"
        assert normalize_currency("€") == "EUR"
        assert normalize_currency("£") == "GBP"
