import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number | null;
  changePeriod?: string;
  sublabel?: string;
  className?: string;
}

/**
 * Stripi-styled KPI metric card.
 * 12px radius, hairline border, blue-tinted shadow, tnum for values.
 */
export function MetricCard({
  label,
  value,
  change,
  changePeriod = "1D",
  sublabel,
  className,
}: MetricCardProps) {
  const isPositive = change != null && change >= 0;
  const changeColor = change == null
    ? "text-muted-foreground"
    : isPositive
      ? "text-stripi-emerald"
      : "text-stripi-ruby";

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4 shadow-stripi",
        className
      )}
    >
      <p className="text-xs font-medium text-muted-foreground tracking-wide">
        {label}
      </p>
      <p className="mt-1 text-2xl font-light tracking-tight text-card-foreground font-tabular">
        {value}
      </p>
      <div className="mt-2 flex items-center gap-2">
        {change != null && (
          <span className={cn("text-xs font-medium font-tabular", changeColor)}>
            {isPositive ? "+" : ""}
            {typeof change === "number" ? change.toFixed(2) : change}%
          </span>
        )}
        {changePeriod && change != null && (
          <span className="text-[11px] text-muted-foreground">
            {changePeriod}
          </span>
        )}
        {sublabel && (
          <span className="text-[11px] text-muted-foreground">{sublabel}</span>
        )}
      </div>
    </div>
  );
}
