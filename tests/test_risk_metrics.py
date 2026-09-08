"""Tests for risk metrics correctness (Section 9.3).

All tests verify against hand-computed expected values.
This is the highest-value test file in the suite.
"""
import sys
from pathlib import Path
import math

import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.risk_metrics import compute_metrics_for_series


class TestLogReturns:
    """Test log return calculations."""

    def test_log_return_1d_matches_hand_computed(self):
        """1-day log return matches manual calculation."""
        # Hand-computed: ln(105/100) = 0.04879...
        prices = pd.Series([100.0, 105.0])
        dates = pd.Index(['2024-01-02', '2024-01-03'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        expected_r1d = math.log(105.0 / 100.0)  # 0.04879016...
        actual_r1d = result.iloc[-1]['return_1d']
        assert actual_r1d is not None
        assert abs(float(actual_r1d) - expected_r1d) < 1e-10

    def test_log_return_1m_matches_hand_computed(self):
        """1-month (21-day) log return matches manual calculation."""
        # Create exactly 22 data points
        prices = pd.Series([100.0] + [101.0] * 20 + [110.0])
        dates = pd.Index([f'2024-01-{i+2:02d}' for i in range(22)])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # 1m return = ln(P_21 / P_0) = ln(110/100) = 0.09531...
        expected = math.log(110.0 / 100.0)
        actual = result.iloc[-1]['return_1m']
        assert actual is not None
        assert abs(float(actual) - expected) < 1e-10

    def test_insufficient_history_returns_null(self):
        """With < 21 data points, return_1m should be NULL (NaN)."""
        prices = pd.Series([100.0, 105.0, 103.0])
        dates = pd.Index(['2024-01-02', '2024-01-03', '2024-01-04'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # Only 3 points — can't compute 1m (21d), 3m (63d), or 1y (252d)
        assert pd.isna(result.iloc[-1]['return_1m'])
        assert pd.isna(result.iloc[-1]['return_3m'])
        assert pd.isna(result.iloc[-1]['return_1y'])


class TestVolatility:
    """Test volatility calculations."""

    def test_vol_30d_matches_numpy_crosscheck(self):
        """30-day volatility matches numpy cross-check with correct annualization."""
        np.random.seed(123)
        n = 30
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0, 0.01, n))))
        dates = pd.Index([f'2024-01-{i+2:02d}' if i < 29 else f'2024-02-{i-28:02d}' for i in range(n)])
        
        # Use valid dates
        dates = pd.Index(pd.bdate_range('2024-01-02', periods=n).strftime('%Y-%m-%d'))
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # Cross-check: compute manually with numpy
        log_returns = np.log(prices.values[1:] / prices.values[:-1])
        # Last 21 log returns
        window_returns = log_returns[-21:]
        expected_vol = float(np.std(window_returns, ddof=1) * math.sqrt(252))
        
        actual_vol = result.iloc[-1]['vol_30d']
        assert actual_vol is not None
        assert abs(float(actual_vol) - expected_vol) < 1e-8

    def test_vol_insufficient_history_is_null(self):
        """Volatility is None when insufficient data."""
        prices = pd.Series([100.0, 105.0, 103.0])
        dates = pd.Index(['2024-01-02', '2024-01-03', '2024-01-04'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        assert pd.isna(result.iloc[-1]['vol_30d'])
        assert pd.isna(result.iloc[-1]['vol_90d'])


class TestZScore:
    """Test z-score calculation."""

    def test_z_score_matches_hand_computed(self):
        """Z-score matches manual calculation."""
        # Simple series: [10, 20, 30, 40, 50]
        prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        dates = pd.Index(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # For the last value (50), trailing window is [10, 20, 30, 40, 50]
        # mean = 30, std (ddof=1) = sqrt(250/4) = sqrt(62.5) = 7.9056...
        # z = (50 - 30) / 7.9056... = 2.5298...
        window = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        expected_mean = np.mean(window)
        expected_std = np.std(window, ddof=1)
        expected_z = (50.0 - expected_mean) / expected_std
        
        actual_z = result.iloc[-1]['z_score']
        assert actual_z is not None
        assert abs(float(actual_z) - expected_z) < 1e-8


class TestPercentile:
    """Test percentile calculation."""

    def test_percentile_matches_scipy(self):
        """Percentile matches scipy.stats.percentileofscore with kind='rank'."""
        prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        dates = pd.Index(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # For value 50 in [10, 20, 30, 40, 50], kind='rank'
        expected_pct = percentileofscore([10, 20, 30, 40, 50], 50, kind='rank')
        
        actual_pct = result.iloc[-1]['percentile']
        assert actual_pct is not None
        assert abs(float(actual_pct) - expected_pct) < 1e-8

    def test_percentile_max_is_100(self):
        """The maximum value in the window should have percentile ~100."""
        prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dates = pd.Index(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        assert float(result.iloc[-1]['percentile']) == 100.0


class TestDrawdown:
    """Test drawdown calculation."""

    def test_drawdown_from_52w_high(self):
        """Drawdown correctly computes from trailing 252-day high."""
        # Create 260 data points (> 252)
        # Start at 100, peak at 120 around day 100, then decline to 90
        n = 260
        prices_list = []
        for i in range(n):
            if i <= 100:
                prices_list.append(100.0 + 0.2 * i)  # rise to 120
            else:
                prices_list.append(120.0 - 0.1875 * (i - 100))  # decline
        
        prices = pd.Series(prices_list)
        dates = pd.Index(pd.bdate_range('2023-01-02', periods=n).strftime('%Y-%m-%d'))
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        last = result.iloc[-1]
        # The 52w high should be ~120 (peak was around day 100)
        # Current value is 120 - 0.1875 * 159 = 120 - 29.8125 = 90.1875
        current = float(last['value'])
        high = float(last['high_52w'])
        
        expected_dd = (current - high) / high * 100
        actual_dd = float(last['drawdown_pct'])
        
        assert abs(actual_dd - expected_dd) < 1e-6
        assert actual_dd < 0  # Should be negative (below high)

    def test_drawdown_is_zero_at_high(self):
        """Drawdown is 0 when price equals the 52w high."""
        # Create 260 points of monotonically increasing prices
        n = 260
        prices = pd.Series([100.0 + i * 0.1 for i in range(n)])
        dates = pd.Index(pd.bdate_range('2023-01-02', periods=n).strftime('%Y-%m-%d'))
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        
        # Since price always increases, current = 52w high, drawdown = 0
        assert float(result.iloc[-1]['drawdown_pct']) == pytest.approx(0.0)


class TestEdgeCases:
    """Test edge cases."""

    def test_insufficient_history_returns_null_fields(self):
        """Instrument with fewer than required lookback returns None."""
        prices = pd.Series([100.0, 105.0])
        dates = pd.Index(['2024-01-02', '2024-01-03'])
        
        result = compute_metrics_for_series(dates, prices, 'COMMODITY', 'TEST')
        last = result.iloc[-1]
        
        # 1d return should exist (we have 2 values)
        assert pd.notna(last['return_1d'])
        
        # These all need more history
        assert pd.isna(last['return_1m'])
        assert pd.isna(last['return_3m'])
        assert pd.isna(last['return_1y'])
        assert pd.isna(last['vol_30d'])
        assert pd.isna(last['vol_90d'])
        # Drawdown requires 252 trading days
        assert pd.isna(last['drawdown_pct'])

    def test_empty_series_returns_empty_df(self):
        """Empty input returns empty DataFrame."""
        result = compute_metrics_for_series(
            pd.Index([]), pd.Series(dtype=float), 'COMMODITY', 'TEST'
        )
        assert result.empty
