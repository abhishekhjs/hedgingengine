"use client";

import { useState } from "react";
import { Warning, Play, ArrowClockwise } from "@phosphor-icons/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { MonteCarloResponse } from "@/lib/types";
import PlotlyChart from "@/components/ui/plotly-chart";
import { MetricCard } from "@/components/dashboard/metric-card";

export default function MonteCarloPage() {
  const [mcResults, setMcResults] = useState<MonteCarloResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iterations] = useState(10000);
  const [selectedCompany] = useState("Toyota Motor Corp");

  const runSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.montecarlo.run(selectedCompany, iterations);
      setMcResults(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run simulation");
    } finally {
      setLoading(false);
    }
  };

  const formatB = (val: number | null | undefined) => {
    if (val == null) return "0.00 B";
    return (val / 1e9).toFixed(2) + " B";
  };

  // Convert histogram data to Tremor format
  const getChartData = (key: string) => {
    if (!mcResults || !mcResults.histogram_data[key]) return [];
    const h = mcResults.histogram_data[key];
    const data = [];
    for (let i = 0; i < h.counts.length; i++) {
      const binStart = h.bins[i];
      const binEnd = h.bins[i + 1];
      if (binStart != null && binEnd != null) {
        data.push({
          bin: `${(binStart / 1e9).toFixed(1)} - ${(binEnd / 1e9).toFixed(1)}`,
          count: h.counts[i],
        });
      }
    }
    return data;
  };

  return (
    <div className="space-y-8 p-8">
      <div className="flex items-center justify-between">
        <h1 className="display-lg font-light tracking-tight">Monte Carlo Simulation</h1>
        <button onClick={runSimulation} disabled={loading} className="btn-pill bg-primary text-primary-foreground flex items-center gap-2 px-6 py-3">
          {loading ? <ArrowClockwise className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />} 
          Run Simulation
        </button>
      </div>

      {error && (
        <div className="flex flex-col items-center justify-center p-8 space-y-4">
          <Warning className="w-12 h-12 text-ruby" />
          <p className="text-muted-foreground">{error}</p>
        </div>
      )}

      {loading && !mcResults && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      )}

      {mcResults && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <MetricCard label="EVaR (95%)" value={formatB(mcResults.risk_metrics?.EV?.var_95)} />
            <MetricCard label="CFaR (95%)" value={formatB(mcResults.risk_metrics?.FCF?.var_95)} />
            <MetricCard label="LaR (95%)" value={formatB(mcResults.risk_metrics?.Cash?.var_95)} />
            <MetricCard label="Shortfall Prob" value={`${((mcResults.liquidity_shortfall_prob ?? 0) * 100).toFixed(2)}%`} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
              <h2 className="text-xl font-light tracking-tight mb-4">FCF Distribution</h2>
              <div className="h-64">
                <PlotlyChart
                  data={[
                    {
                      type: 'bar',
                      x: getChartData("simulated_fcf").map(d => d.bin),
                      y: getChartData("simulated_fcf").map(d => d.count),
                      marker: { color: "#533afd" },
                      hovertemplate: '%{x}<br>Count: %{y}<extra></extra>'
                    }
                  ]}
                  layout={{
                    xaxis: { tickangle: -45 },
                    margin: { t: 10, b: 60, l: 40, r: 20 },
                    bargap: 0.05
                  }}
                />
              </div>
            </div>
            
            <div className="rounded-xl border border-border bg-card shadow-stripi p-6 overflow-x-auto">
              <h2 className="text-xl font-light tracking-tight mb-4">Correlation Matrix</h2>
              {mcResults.correlation_matrix?.columns?.length > 0 ? (
                <Table>
                  <TableBody className="font-tabular text-sm">
                    <TableRow>
                      <TableCell></TableCell>
                      {mcResults.correlation_matrix.columns.map((col, i) => (
                        <TableCell key={i} className="font-medium text-center">{col}</TableCell>
                      ))}
                    </TableRow>
                    {mcResults.correlation_matrix.data.map((row, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{mcResults.correlation_matrix.columns[i]}</TableCell>
                        {row.map((val, j) => (
                          <TableCell 
                            key={j} 
                            className="text-center"
                            style={{ backgroundColor: `rgba(5, 150, 105, ${Math.abs(val)})`, color: Math.abs(val) > 0.5 ? 'white' : 'inherit' }}
                          >
                            {val.toFixed(2)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-muted-foreground">No correlation data available</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
