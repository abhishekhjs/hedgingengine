"use client";

import { useEffect, useState } from "react";
import { Warning, ArrowClockwise, Play } from "@phosphor-icons/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { HedgePriorityRow, FactorAttribution, FrontierResult } from "@/lib/types";
import PlotlyChart from "@/components/ui/plotly-chart";

export default function OptimizationPage() {
  const [priorityData, setPriorityData] = useState<HedgePriorityRow[]>([]);
  const [attribution, setAttribution] = useState<FactorAttribution | null>(null);
  const [frontier, setFrontier] = useState<FrontierResult | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCompany] = useState("Toyota Motor Corp");

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const prio = await api.optimization.getPriority(selectedCompany);
      setPriorityData(prio);
      
      const attr = await api.optimization.getAttribution(selectedCompany);
      setAttribution(attr);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load optimization data");
    } finally {
      setLoading(false);
    }
  };

  const computeFrontier = async () => {
    try {
      setComputing(true);
      const res = await api.optimization.getFrontier(selectedCompany, 10);
      setFrontier(res);
    } catch (err) {
      console.error(err);
    } finally {
      setComputing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCompany]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 space-y-4">
        <Warning className="w-12 h-12 text-stripi-ruby" />
        <p className="text-muted-foreground">{error}</p>
        <button onClick={loadData} className="btn-pill bg-primary text-primary-foreground flex items-center gap-2 px-4 py-2">
          <ArrowClockwise className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  const attrData = attribution ? [
    { name: "Commodity", Value: (attribution.Commodity ?? 0) / 1e9 },
    { name: "FX", Value: (attribution.FX ?? 0) / 1e9 },
    { name: "Rates", Value: (attribution.Rates ?? 0) / 1e9 },
    { name: "Interaction", Value: (attribution["Interaction / Diversification"] ?? 0) / 1e9 }
  ] : [];

  return (
    <div className="space-y-8 p-8">
      <div className="flex items-center justify-between">
        <h1 className="display-lg font-light tracking-tight">Hedge Optimization</h1>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="rounded-xl border border-border bg-card shadow-stripi p-6 overflow-x-auto">
              <h2 className="text-xl font-light tracking-tight mb-4">Hedge Priority Ranking</h2>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Factor</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Gross (JPY B)</TableHead>
                    <TableHead>CFaR Contrib</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="font-tabular">
                  {priorityData.map((row, i) => (
                    <TableRow key={i}>
                      <TableCell>{row.Factor}</TableCell>
                      <TableCell>{row.Category}</TableCell>
                      <TableCell>{(row['Gross Exposure (JPY B)'] || 0).toFixed(2)}</TableCell>
                      <TableCell>{(row['CFaR Contrib (JPY B)'] || 0).toFixed(2)}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${row.Action.includes('Hedge') ? 'bg-stripi-emerald/10 text-stripi-emerald' : 'bg-slate-100 text-slate-700'}`}>
                          {row.Action}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
              <h2 className="text-xl font-light tracking-tight mb-4">Factor Attribution (JPY B)</h2>
              <div className="h-64">
                <PlotlyChart
                  data={[
                    {
                      type: 'bar',
                      x: attrData.map(d => d.name),
                      y: attrData.map(d => d.Value),
                      marker: { color: "#533afd" },
                      hovertemplate: '%{x}<br>Attribution: %{y:.2f} B<extra></extra>'
                    }
                  ]}
                  layout={{
                    margin: { t: 10, b: 30, l: 40, r: 20 }
                  }}
                />
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-light tracking-tight">Efficient Frontier</h2>
              <button onClick={computeFrontier} disabled={computing} className="btn-pill bg-primary text-primary-foreground flex items-center gap-2 px-4 py-2 text-sm">
                {computing ? <ArrowClockwise className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Compute Frontier
              </button>
            </div>
            
            {frontier && (
              <div className="overflow-x-auto">
                <Table>
                  <TableBody className="font-tabular text-sm">
                    <TableRow>
                      <TableCell></TableCell>
                      {frontier.columns.map((col, i) => (
                        <TableCell key={i} className="font-medium text-center">{col}</TableCell>
                      ))}
                    </TableRow>
                    {frontier.data.map((row, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{frontier.index[i]}</TableCell>
                        {row.map((val, j) => (
                          <TableCell 
                            key={j} 
                            className="text-center"
                            style={{ backgroundColor: `rgba(5, 150, 105, ${val > 0 ? Math.min(val / 100, 1) : 0})` }}
                          >
                            {val.toFixed(2)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            {!frontier && !computing && (
              <div className="py-12 text-center text-muted-foreground">
                Click compute to generate efficient frontier heatmap
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
