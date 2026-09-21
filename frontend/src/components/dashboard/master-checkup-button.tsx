"use client";

import { useState } from "react";
import { DownloadSimple, SpinnerGap, ArrowRight, Target, Lightning, ShieldCheck, PresentationChart } from "@phosphor-icons/react";
import { api } from "@/lib/api";

export function MasterCheckupButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const steps = [
    { name: "Gathering Live Market Data", icon: Lightning },
    { name: "Computing Exposure & Hedge Match", icon: Target },
    { name: "Running Financial Transmission", icon: ShieldCheck },
    { name: "Executing 10,000 Monte Carlo Sims", icon: SpinnerGap },
    { name: "Generating Efficient Frontier PDF", icon: PresentationChart },
  ];

  const handleGenerate = async () => {
    setIsGenerating(true);
    
    // Simulate step progression purely for UX (the backend handles it monolithically)
    const interval = setInterval(() => {
      setStep((s) => (s < 4 ? s + 1 : s));
    }, 2500);

    try {
      // In a real app we'd fetch the company name from context
      const res = await fetch("http://localhost:8000/api/report/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_name: "Toyota (Real FY24)" })
      });
      
      if (!res.ok) throw new Error("Failed to generate report");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Master_Risk_Report_${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      
    } catch (e) {
      console.error(e);
      alert("Failed to generate report.");
    } finally {
      clearInterval(interval);
      setStep(0);
      setIsGenerating(false);
      setIsOpen(false);
    }
  };

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 bg-[#533afd] text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-[#4434d4] transition-colors shadow-sm"
      >
        <DownloadSimple weight="bold" />
        Master Check-up Report
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-[#0d253d]/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-xl font-light tracking-tight text-[#0d253d] mb-2">Master Risk Check-up</h3>
            <p className="text-sm text-[#64748d] mb-6">
              This will run the full end-to-end risk pipeline and export an exhaustive PDF report.
            </p>

            {isGenerating ? (
              <div className="space-y-4 mb-6">
                {steps.map((s, i) => {
                  const Icon = s.icon;
                  const isActive = i === step;
                  const isDone = i < step;
                  return (
                    <div key={i} className={`flex items-center gap-3 ${isActive ? 'text-[#533afd]' : isDone ? 'text-[#059669]' : 'text-[#64748d] opacity-50'}`}>
                      {isActive ? (
                        <SpinnerGap weight="bold" className="animate-spin" />
                      ) : isDone ? (
                        <div className="w-4 h-4 rounded-full bg-[#059669] flex items-center justify-center text-white text-[10px]">✓</div>
                      ) : (
                        <Icon weight="bold" />
                      )}
                      <span className="text-sm font-medium">{s.name}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-[#f6f9fc] rounded-xl p-4 mb-6 text-sm text-[#273951]">
                <strong>Time Estimate:</strong> ~15 seconds. The engine will run 10,000 Monte Carlo simulations and grid-search the optimal hedge frontier.
              </div>
            )}

            <div className="flex justify-end gap-3">
              {!isGenerating && (
                <button 
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-[#64748d] hover:text-[#0d253d] transition-colors"
                >
                  Cancel
                </button>
              )}
              <button 
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex items-center gap-2 bg-[#533afd] disabled:bg-[#b9b9f9] text-white px-5 py-2 rounded-full text-sm font-medium hover:bg-[#4434d4] transition-colors"
              >
                {isGenerating ? "Generating..." : "Run Analysis & Export"}
                {!isGenerating && <ArrowRight weight="bold" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
