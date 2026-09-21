"use client";

import { useEffect, useState } from "react";
import { Warning, ArrowClockwise } from "@phosphor-icons/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Slider } from "@/components/ui/slider";
import { api } from "@/lib/api";
import type { TransmissionResult } from "@/lib/types";
import PlotlyChart from "@/components/ui/plotly-chart";

export default function TransmissionPage() {
  const [transmissionResult, setTransmissionResult] = useState<TransmissionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sigma, setSigma] = useState(1.0);
  const [selectedCompany] = useState<string>("Toyota Motor Corp");

  const loadData = async (s: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.transmission.compute(selectedCompany, s);
      setTransmissionResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compute transmission");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(sigma);
  }, [sigma, selectedCompany]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-4">
        <Warning className="w-12 h-12 text-ruby" />
        <p className="text-muted-foreground">{error}</p>
        <button onClick={() => loadData(sigma)} className="btn-pill bg-primary text-primary-foreground flex items-center gap-2 px-4 py-2">
          <ArrowClockwise className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  const formatB = (val: number | null | undefined) => {
    if (val == null) return "0.00 B";
    return (val / 1e9).toFixed(2);
  };

  const shockData = transmissionResult ? Object.entries(transmissionResult.transmission['Shock Drivers']).map(([k, v]) => ({
    name: k,
    Impact: Number(formatB(v))
  })) : [];

  return (
    <div className="space-y-8 p-8">
      <div className="flex items-center justify-between">
        <h1 className="display-lg font-light tracking-tight">Financial Transmission</h1>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-stripi p-6 space-y-4">
        <label className="text-sm font-medium">Shock Severity (Sigma: {sigma.toFixed(1)}x)</label>
        <Slider 
          value={[sigma]} 
          min={0.5} 
          max={3.0} 
          step={0.5} 
          onValueChange={(val) => setSigma(Array.isArray(val) ? val[0] : (val as number))} 
        />
      </div>

      {loading || !transmissionResult ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="rounded-xl border border-border bg-card shadow-stripi p-6 overflow-x-auto">
            <h2 className="text-xl font-light tracking-tight mb-4">Income Statement Impact (JPY B)</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead className="text-right">Base</TableHead>
                  <TableHead className="text-right">Shocked</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="font-tabular">
                {Object.entries(transmissionResult.transmission['Income Statement']).map(([k, v]) => (
                  <TableRow key={k}>
                    <TableCell>{k}</TableCell>
                    <TableCell className="text-right">{formatB(v.Base)}</TableCell>
                    <TableCell className="text-right">{formatB(v.Shocked)}</TableCell>
                    <TableCell className={`text-right ${v.Shocked - v.Base < 0 ? 'text-stripi-ruby' : 'text-stripi-emerald'}`}>
                      {formatB(v.Shocked - v.Base)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-stripi p-6 overflow-x-auto">
            <h2 className="text-xl font-light tracking-tight mb-4">Balance Sheet & Value (JPY B)</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead className="text-right">Base</TableHead>
                  <TableHead className="text-right">Shocked</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="font-tabular">
                {Object.entries(transmissionResult.transmission['Balance Sheet & Value']).map(([k, v]) => (
                  <TableRow key={k}>
                    <TableCell>{k}</TableCell>
                    <TableCell className="text-right">{formatB(v.Base)}</TableCell>
                    <TableCell className="text-right">{formatB(v.Shocked)}</TableCell>
                    <TableCell className={`text-right ${v.Shocked - v.Base < 0 ? 'text-stripi-ruby' : 'text-stripi-emerald'}`}>
                      {formatB(v.Shocked - v.Base)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
            <h2 className="text-xl font-light tracking-tight mb-4">Shock Drivers (JPY B)</h2>
            <div className="h-64">
              <PlotlyChart
                data={[
                  {
                    type: 'bar',
                    x: shockData.map(d => d.Impact),
                    y: shockData.map(d => d.name),
                    orientation: 'h',
                    marker: { color: "#533afd" },
                    hovertemplate: '%{y}: %{x:.2f} B<extra></extra>'
                  }
                ]}
                layout={{
                  xaxis: { title: 'Impact (JPY B)' },
                  yaxis: { autorange: 'reversed' },
                  margin: { l: 120, t: 10, b: 40, r: 20 }
                }}
              />
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
            <h2 className="text-xl font-light tracking-tight mb-4">Proximity Scores</h2>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(transmissionResult.proximity_scores).map(([k, v]) => (
                <div key={k} className={`p-4 rounded-xl border font-tabular flex flex-col justify-center items-center ${v.proximity < 1.5 ? 'bg-stripi-ruby/10 border-stripi-ruby/20 text-stripi-ruby' : 'bg-stripi-emerald/10 border-stripi-emerald/20 text-stripi-emerald'}`}>
                  <span className="text-sm font-medium mb-1">{v.label}</span>
                  <span className="text-2xl font-bold">{v.proximity.toFixed(2)}x</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
