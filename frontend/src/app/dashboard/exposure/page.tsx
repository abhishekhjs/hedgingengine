"use client";

import { useEffect, useState } from "react";
import { Warning, ArrowClockwise } from "@phosphor-icons/react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { CompanyExposure, HedgeInstrument, CompanyFinancials, RiskProfile } from "@/lib/types";
import PlotlyChart from "@/components/ui/plotly-chart";
import { MetricCard } from "@/components/dashboard/metric-card";
import { InsightCard } from "@/components/ui/insight-card";

export default function ExposurePage() {
  const [exposures, setExposures] = useState<CompanyExposure[]>([]);
  const [hedges, setHedges] = useState<HedgeInstrument[]>([]);
  const [financials, setFinancials] = useState<CompanyFinancials | null>(null);
  const [riskProfile, setRiskProfile] = useState<RiskProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string>("Toyota Motor Corp");

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const exps = await api.exposure.getCompanies();
      setExposures(exps);
      const companyToUse = exps.length > 0 ? exps[0].company_name : "Toyota Motor Corp";
      setSelectedCompany(companyToUse);
      const hdgs = await api.exposure.getHedges();
      setHedges(hdgs.filter(h => h.company_name === companyToUse));
      const fins = await api.exposure.getFinancials(companyToUse);
      setFinancials(fins);
      const rp = await api.exposure.getRiskProfile(companyToUse);
      setRiskProfile(rp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  // Format helper
  const formatB = (val: number | null | undefined) =>
    val != null ? `¥${(val / 1e9).toFixed(2)}B` : "-";

  const chartData = riskProfile ? [
    ...Object.entries(riskProfile.commodity).map(([k, v]) => ({ name: k, value: v.gross_exposure_jpy / 1e9 })),
    ...Object.entries(riskProfile.fx).map(([k, v]) => ({ name: k, value: v.gross_exposure_jpy / 1e9 }))
  ] : [];

  // Compute total gross exposure and total hedged for the insight
  let totalGross = 0;
  let totalHedged = 0;
  let topFactor = { name: "None", value: 0 };

  if (riskProfile) {
    const categories = ["commodity", "fx", "rates"] as const;
    categories.forEach(cat => {
      const metrics = riskProfile[cat];
      if (metrics) {
        Object.values(metrics).forEach(m => {
          totalGross += m.gross_exposure_jpy;
          totalHedged += m.hedged_jpy;
        });
      }
    });
    
    chartData.forEach(d => {
      if (d.value > topFactor.value) {
        topFactor = d;
      }
    });
  }

  const netExposure = totalGross - totalHedged;
  const coverageRatio = totalGross > 0 ? (totalHedged / totalGross) * 100 : 0;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Warning size={40} className="text-stripi-ruby mb-4" />
        <p className="text-lg font-light text-foreground mb-2">Unable to load exposure data</p>
        <p className="text-sm text-muted-foreground mb-6">{error}</p>
        <button onClick={loadData} className="btn-pill bg-primary text-primary-foreground px-6">Retry</button>
      </div>
    );
  }

  const chartData = riskProfile ? [
    ...Object.entries(riskProfile.commodity).map(([k, v]) => ({ name: k, value: v.gross_exposure_jpy / 1e9 })),
    ...Object.entries(riskProfile.fx).map(([k, v]) => ({ name: k, value: v.gross_exposure_jpy / 1e9 }))
  ] : [];

  return (
    <div className="space-y-8">
      <h1 className="display-lg text-foreground">Company Exposure Mapping</h1>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard label="Base Revenue" value={formatB(financials?.base_revenue)} />
            <MetricCard label="Base COGS" value={formatB(financials?.base_cogs)} />
            <MetricCard label="Starting Debt" value={formatB(financials?.starting_debt)} />
          </div>

          {chartData.length > 0 && (
            <div className="rounded-xl border border-border bg-card shadow-stripi p-6">
              <h2 className="text-lg font-light tracking-tight text-foreground mb-4">Gross Exposure by Factor (JPY B)</h2>
              <div className="h-64">
                <PlotlyChart
                  data={[
                    {
                      values: chartData.map(d => d.value),
                      labels: chartData.map(d => d.name),
                      type: 'pie',
                      hole: 0.6,
                      textinfo: 'label+percent',
                      hoverinfo: 'label+value',
                      hovertemplate: '%{label}: %{value:.2f} B<extra></extra>',
                      marker: {
                        colors: ["#533afd", "#ea2261", "#059669", "#665efd", "#f96bee"],
                        line: { color: '#ffffff', width: 2 }
                      }
                    }
                  ]}
                  layout={{
                    showlegend: true,
                    margin: { t: 10, b: 10, l: 10, r: 10 }
                  }}
                />
              </div>
            </div>
          )}

          <div className="rounded-xl border border-border bg-card shadow-stripi overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-light tracking-tight text-foreground">Underlying Exposures</h2>
            </div>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Commodity</TableHead><TableHead className="text-right">Quantity</TableHead><TableHead>Currency</TableHead><TableHead className="text-right">Imports (B)</TableHead><TableHead className="text-right">Debt (B)</TableHead><TableHead className="text-right">Floating %</TableHead></TableRow>
              </TableHeader>
              <TableBody className="font-tabular">
                {exposures.map((exp, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{exp.commodity ?? "-"}</TableCell>
                    <TableCell className="text-right">{exp.annual_quantity?.toLocaleString() ?? "-"}</TableCell>
                    <TableCell>{exp.currency ?? "-"}</TableCell>
                    <TableCell className="text-right">{formatB(exp.annual_imports)}</TableCell>
                    <TableCell className="text-right">{formatB(exp.debt_amount)}</TableCell>
                    <TableCell className="text-right">{exp.floating_rate_percentage != null ? (exp.floating_rate_percentage * 100).toFixed(1) + "%" : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-stripi overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-light tracking-tight text-foreground">Active Hedges</h2>
            </div>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Instrument</TableHead><TableHead>Underlying</TableHead><TableHead className="text-right">Notional</TableHead><TableHead className="text-right">Strike</TableHead><TableHead>Maturity</TableHead><TableHead className="text-right">Hedge Ratio</TableHead></TableRow>
              </TableHeader>
              <TableBody className="font-tabular">
                {hedges.map((h, i) => (
                  <TableRow key={i}>
                    <TableCell>{h.instrument ?? "-"}</TableCell>
                    <TableCell>{h.underlying ?? "-"}</TableCell>
                    <TableCell className="text-right">{h.notional?.toLocaleString() ?? "-"}</TableCell>
                    <TableCell className="text-right">{h.strike ?? "-"}</TableCell>
                    <TableCell>{h.maturity ?? "-"}</TableCell>
                    <TableCell className="text-right">{h.hedge_ratio != null ? (h.hedge_ratio * 100).toFixed(1) + "%" : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
