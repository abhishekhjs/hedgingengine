"use client";

import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";

// Dynamically import Plotly factory to avoid SSR issues and use the lightweight dist
const Plot = dynamic(
  () => import("react-plotly.js/factory").then((mod) => {
    const Plotly = require("plotly.js-dist-min");
    return mod.default(Plotly);
  }),
  { ssr: false }
);

// Stripi color palette from Streamlit dashboard
const stripiPalette = ["#533afd", "#665efd", "#ea2261", "#f96bee", "#1c1e54", "#059669"];

export default function PlotlyChart({ data, layout, config, ...props }: PlotParams) {
  // Merge Stripi theme into layout
  const stripiLayout = {
    font: { family: "Inter, -apple-system, sans-serif", color: "#0d253d", size: 12 },
    colorway: stripiPalette,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    xaxis: {
      showgrid: true,
      gridcolor: "#e3e8ee",
      zeroline: false,
      linecolor: "#e3e8ee",
      tickfont: { color: "#64748d", size: 11 },
      ...((layout as any)?.xaxis || {}),
    },
    yaxis: {
      showgrid: true,
      gridcolor: "#e3e8ee",
      zeroline: false,
      linecolor: "#e3e8ee",
      tickfont: { color: "#64748d", size: 11 },
      ...((layout as any)?.yaxis || {}),
    },
    margin: { l: 40, r: 20, t: 30, b: 30, ...((layout as any)?.margin || {}) },
    hovermode: "closest",
    ...(layout || {}),
  };

  return (
    <div className="w-full h-full overflow-hidden">
      <Plot
        data={data}
        layout={stripiLayout as any}
        config={{ displayModeBar: false, responsive: true, ...(config || {}) }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler={true}
        {...props}
      />
    </div>
  );
}
