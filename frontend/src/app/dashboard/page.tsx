"use client";

import { useEffect, useState } from "react";
import { market } from "@/lib/api";
import type { RiskMetricRow } from "@/lib/types";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowsClockwise, Warning } from "@phosphor-icons/react";


// Asset display config
const ASSET_GROUPS: Record<string, { label: string; assets: string[] }> = {
  commodity: {
    label: "Commodities",
    assets: ["WTI", "BRENT", "COPPER", "ALUMINIUM"],
  },
  fx: {
    label: "Foreign Exchange",
    assets: ["USDJPY", "EURJPY", "AUDJPY"],
  },
  rate: {
    label: "JGB Yields",
    assets: ["2Y", "5Y", "10Y", "20Y", "30Y", "40Y"],
  },
};

function formatValue(value: number | null, asset_class: string): string {
  if (value == null) return "-";
  if (asset_class === "RATE") return `${value.toFixed(3)}%`;
  if (asset_class === "FX") return value.toFixed(2);
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(value: number | null): string {
  if (value == null) return "-";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function getZScoreVariant(z: number | null): "default" | "destructive" | "outline" | "secondary" {
  if (z == null) return "secondary";
  const abs = Math.abs(z);
  if (abs > 2) return "destructive";
  if (abs > 1) return "outline";
  return "secondary";
}

export default function MarketRiskPage() {
  const [metrics, setMetrics] = useState<RiskMetricRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await market.getRiskMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getMetric = (asset: string) =>
    metrics.find((m) => m.asset === asset);

  // Build headline KPIs from key assets
  const headlines = ["WTI", "USDJPY", "10Y", "COPPER"].map((asset) => {
    const m = getMetric(asset);
    return {
      asset,
      label: asset === "10Y" ? "JGB 10Y" : asset,
      value: m ? formatValue(m.value, m.asset_class) : "-",
      change: m?.return_1d != null ? m.return_1d * 100 : null,
    };
  });

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Warning size={40} className="text-stripi-ruby mb-4" />
        <p className="text-lg font-light text-foreground mb-2">
          Unable to load market data
        </p>
        <p className="text-sm text-muted-foreground mb-6 max-w-md">
          {error}
        </p>
        <button
          onClick={loadData}
          className="btn-pill bg-primary text-primary-foreground px-6"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="display-lg text-foreground">Market Risk Monitor</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time market data, volatility, and risk metrics for Japan manufacturing exposure
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="btn-pill bg-primary text-primary-foreground flex items-center gap-2 px-5 disabled:opacity-50"
        >
          <ArrowsClockwise
            size={16}
            className={loading ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </div>

      {/* Headline KPIs */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {headlines.map((h) => (
            <MetricCard
              key={h.asset}
              label={h.label}
              value={h.value}
              change={h.change}
              changePeriod="1D"
            />
          ))}
        </div>
      )}

      {/* Asset Tables by Group */}
      {Object.entries(ASSET_GROUPS).map(([key, group]) => (
        <section key={key}>
          <h2 className="text-lg font-light tracking-tight text-foreground mb-3">
            {group.label}
          </h2>
          <div className="rounded-xl border border-border bg-card shadow-stripi overflow-hidden">
            {loading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: group.assets.length }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border">
                    <TableHead className="w-28">Asset</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">1D</TableHead>
                    <TableHead className="text-right">1M</TableHead>
                    <TableHead className="text-right">1Y</TableHead>
                    <TableHead className="text-right">Vol 30D</TableHead>
                    <TableHead className="text-right">Vol 90D</TableHead>
                    <TableHead className="text-right">Z-Score</TableHead>
                    <TableHead className="text-right">%ile</TableHead>
                    <TableHead className="text-right">52W Range</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.assets.map((asset) => {
                    const m = getMetric(asset);
                    if (!m) {
                      return (
                        <TableRow key={asset} className="text-muted-foreground">
                          <TableCell className="font-medium">{asset}</TableCell>
                          <TableCell colSpan={9} className="text-center text-xs">
                            No data
                          </TableCell>
                        </TableRow>
                      );
                    }
                    return (
                      <TableRow key={asset} className="border-b border-border/50">
                        <TableCell className="font-medium text-foreground">
                          {asset}
                        </TableCell>
                        <TableCell className="text-right font-tabular">
                          {formatValue(m.value, m.asset_class)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-tabular ${
                            m.return_1d != null && m.return_1d < 0
                              ? "text-stripi-ruby"
                              : m.return_1d != null && m.return_1d > 0
                                ? "text-stripi-emerald"
                                : ""
                          }`}
                        >
                          {formatPct(m.return_1d)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-tabular ${
                            m.return_1m != null && m.return_1m < 0
                              ? "text-stripi-ruby"
                              : m.return_1m != null && m.return_1m > 0
                                ? "text-stripi-emerald"
                                : ""
                          }`}
                        >
                          {formatPct(m.return_1m)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-tabular ${
                            m.return_1y != null && m.return_1y < 0
                              ? "text-stripi-ruby"
                              : m.return_1y != null && m.return_1y > 0
                                ? "text-stripi-emerald"
                                : ""
                          }`}
                        >
                          {formatPct(m.return_1y)}
                        </TableCell>
                        <TableCell className="text-right font-tabular">
                          {m.vol_30d != null
                            ? `${(m.vol_30d * 100).toFixed(1)}%`
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right font-tabular">
                          {m.vol_90d != null
                            ? `${(m.vol_90d * 100).toFixed(1)}%`
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={getZScoreVariant(m.z_score)}>
                            <span className="font-tabular">
                              {m.z_score != null ? m.z_score.toFixed(2) : "-"}
                            </span>
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-tabular">
                          {m.percentile != null
                            ? `${m.percentile.toFixed(0)}%`
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right font-tabular text-xs text-muted-foreground">
                          {m.low_52w != null && m.high_52w != null
                            ? `${m.low_52w.toFixed(2)} - ${m.high_52w.toFixed(2)}`
                            : "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </section>
      ))}
    </div>
  );
}
