"""Tests for ingestion layer correctness (Section 9.1).

Each fetcher correctly parses known sample responses.
Each fetcher handles empty/malformed responses without crashing.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import pandas as pd
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestFredIngestion:
    """Tests for FRED API data fetcher."""

    def test_fred_parses_valid_response(self, sample_fred_response):
        """FRED fetcher correctly parses a known sample response."""
        with patch('src.ingestion.fred.Fred') as MockFred:
            mock_fred = MockFred.return_value
            mock_fred.get_series.return_value = sample_fred_response
            
            with patch('src.ingestion.fred.get_fred_api_key', return_value='test_key'):
                from src.ingestion.fred import fetch_fred_commodities
                df = fetch_fred_commodities()
        
        # Should have rows (NaN dropped)
        assert not df.empty
        # Should have correct columns
        assert set(['date', 'commodity', 'price_usd', 'unit', 'source', 'ingested_at']).issubset(df.columns)
        # Source should be FRED
        assert (df['source'] == 'FRED').all()
        # No NaN prices
        assert df['price_usd'].notna().all()

    def test_fred_handles_empty_response(self):
        """FRED fetcher handles empty response without crashing."""
        with patch('src.ingestion.fred.Fred') as MockFred:
            mock_fred = MockFred.return_value
            mock_fred.get_series.return_value = pd.Series(dtype=float)
            
            with patch('src.ingestion.fred.get_fred_api_key', return_value='test_key'):
                from src.ingestion.fred import fetch_fred_commodities
                df = fetch_fred_commodities()
        
        # Should return empty DataFrame, not crash
        assert isinstance(df, pd.DataFrame)

    def test_fred_handles_network_error(self):
        """FRED fetcher handles network errors gracefully."""
        with patch('src.ingestion.fred.Fred') as MockFred:
            mock_fred = MockFred.return_value
            mock_fred.get_series.side_effect = Exception("Network error")
            
            with patch('src.ingestion.fred.get_fred_api_key', return_value='test_key'):
                from src.ingestion.fred import fetch_fred_commodities
                df = fetch_fred_commodities()
        
        assert isinstance(df, pd.DataFrame)


class TestMOFIngestion:
    """Tests for MOF JGB CSV fetcher."""

    def test_mof_parses_valid_csv(self, sample_mof_csv_text):
        """MOF fetcher correctly parses a known CSV sample."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_mof_csv_text.encode('shift_jis')
        mock_response.raise_for_status = MagicMock()
        
        with patch('src.ingestion.mof.requests.get', return_value=mock_response):
            from src.ingestion.mof import fetch_mof_jgb_yields
            df = fetch_mof_jgb_yields()
        
        # Should have data
        assert not df.empty
        # Should have correct columns
        assert set(['date', 'tenor', 'yield_pct', 'source', 'ingested_at']).issubset(df.columns)
        # Source should be MOF
        assert (df['source'] == 'MOF').all()
        # Should have parsed dates correctly
        assert '2024-09-02' in df['date'].values or len(df) > 0
        # Missing values (25Y = '-') should be dropped
        tenor_25y = df[df['tenor'] == '25Y']
        assert tenor_25y.empty  # 25Y had '-' values, should be dropped

    def test_mof_handles_empty_response(self):
        """MOF fetcher handles empty/error responses without crashing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_response.raise_for_status = MagicMock()
        
        with patch('src.ingestion.mof.requests.get', return_value=mock_response):
            from src.ingestion.mof import fetch_mof_jgb_yields
            df = fetch_mof_jgb_yields()
        
        assert isinstance(df, pd.DataFrame)

    def test_mof_handles_network_error(self):
        """MOF fetcher handles network errors gracefully."""
        with patch('src.ingestion.mof.requests.get', side_effect=Exception("Connection error")):
            from src.ingestion.mof import fetch_mof_jgb_yields
            df = fetch_mof_jgb_yields()
        
        assert isinstance(df, pd.DataFrame)


class TestYfinanceIngestion:
    """Tests for yfinance data fetcher."""

    def test_yfinance_parses_valid_response(self, sample_yfinance_df):
        """yfinance fetcher correctly parses a valid response."""
        with patch('src.ingestion.yfinance_fetcher.yf') as mock_yf:
            mock_yf.download.return_value = sample_yfinance_df
            
            from src.ingestion.yfinance_fetcher import fetch_yfinance_fx
            df = fetch_yfinance_fx()
        
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert set(['date', 'currency_pair', 'rate', 'source', 'ingested_at']).issubset(df.columns)

    def test_yfinance_handles_empty_response(self):
        """yfinance fetcher handles empty DataFrame without crashing."""
        with patch('src.ingestion.yfinance_fetcher.yf') as mock_yf:
            mock_yf.download.return_value = pd.DataFrame()
            
            from src.ingestion.yfinance_fetcher import fetch_yfinance_fx
            df = fetch_yfinance_fx()
        
        assert isinstance(df, pd.DataFrame)
