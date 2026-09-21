import React from "react";

export function InsightCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 p-4 rounded-xl bg-[#f6f9fc] border border-[#e3e8ee] text-[#273951] flex gap-3 items-start shadow-sm">
      <div className="p-1.5 rounded-full bg-[#533afd]/10 text-[#533afd] shrink-0 mt-0.5">
        <svg width="16" height="16" viewBox="0 0 256 256" fill="currentColor">
          <path d="M176,232a8,8,0,0,1-8,8H88a8,8,0,0,1,0-16h80A8,8,0,0,1,176,232Zm40-104a87.55,87.55,0,0,1-33.64,69.21A16.24,16.24,0,0,0,176,209.6V216a8,8,0,0,1-8,8H88a8,8,0,0,1-8-8v-6.4a16.24,16.24,0,0,0-6.36-12.39A88,88,0,1,1,216,128Zm-16,0a72,72,0,1,0-122.9,51.05A32.22,32.22,0,0,1,88,190.54V208h80V190.54a32.22,32.22,0,0,1,10.9-11.49A71.49,71.49,0,0,0,200,128Z"></path>
        </svg>
      </div>
      <div className="leading-relaxed text-sm font-medium">{children}</div>
    </div>
  );
}
