import { Sidebar } from "@/components/dashboard/sidebar";
import { MasterCheckupButton } from "@/components/dashboard/master-checkup-button";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full min-h-[100dvh]">
      <Sidebar />
      {/* Main content area: offset by sidebar width */}
      <main className="flex-1 ml-60 flex flex-col h-screen overflow-hidden">
        {/* Global Header */}
        <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_0_3px_rgba(83,58,253,0.25)]"></div>
            <span className="text-xs font-medium text-foreground">Live Market Feed Active</span>
          </div>
          <MasterCheckupButton />
        </header>

        {/* Scrollable Page Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[1400px] mx-auto px-6 py-8">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
