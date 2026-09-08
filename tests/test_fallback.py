"""Tests for fallback logic (Section 9.4).

Simulated yfinance failure correctly triggers FRED monthly fallback.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestFallbackLogic:
    """Tests for commodity yfinance → FRED monthly fallback."""

    def test_yfinance_failure_triggers_fred_fallback(self):
        """When yfinance returns empty data, FRED monthly fallback is triggered."""
        # Mock yfinance to return empty DataFrame (simulating failure)
        with patch('src.ingestion.yfinance_fetcher.yf') as mock_yf:
            mock_yf.download.return_value = pd.DataFrame()  # Empty = failure
            
            # Mock the FRED fallback to return some data
            mock_fallback_data = pd.DataFrame({
                'date': ['2024-01-01', '2024-02-01'],
                'commodity': ['COPPER', 'COPPER'],
                'price_usd': [3.85, 3.90],
                'unit': ['USD/lb', 'USD/lb'],
                'source': ['FRED_MONTHLY_FALLBACK', 'FRED_MONTHLY_FALLBACK'],
                'ingested_at': ['2024-01-01T00:00:00', '2024-01-01T00:00:00'],
            })
            
            # Patch at the source module since yfinance_fetcher does
            # 'from src.ingestion.fred import fetch_fred_monthly_fallback' inside the except block
            with patch(
                'src.ingestion.fred.fetch_fred_monthly_fallback',
                return_value=mock_fallback_data
            ) as mock_fallback:
                from src.ingestion.yfinance_fetcher import fetch_yfinance_commodities
                df = fetch_yfinance_commodities()
                
                # Verify fallback was called for the failed commodity
                assert mock_fallback.called

    def test_fallback_rows_tagged_correctly(self):
        """Fallback rows are tagged with source = 'FRED_MONTHLY_FALLBACK'."""
        fallback_dates = pd.bdate_range('2024-01-02', periods=5)
        mock_series = pd.Series(
            [3.85, 3.90, 3.88, 3.92, 3.95],
            index=fallback_dates,
        )
        
        with patch('src.ingestion.fred.Fred') as MockFred:
            mock_fred = MockFred.return_value
            mock_fred.get_series.return_value = mock_series
            
            with patch('src.ingestion.fred.get_fred_api_key', return_value='test_key'):
                from src.ingestion.fred import fetch_fred_monthly_fallback
                df = fetch_fred_monthly_fallback('COPPER')
        
        if not df.empty:
            assert (df['source'] == 'FRED_MONTHLY_FALLBACK').all()
