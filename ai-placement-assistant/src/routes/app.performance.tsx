import { createFileRoute } from "@tanstack/react-router";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { AlertTriangle, TrendingUp, Lightbulb } from "lucide-react";
import { useCompanies } from "@/context/CompanyContext";
import { aggregatePerformance } from "@/lib/companyUtils";

export const Route = createFileRoute("/app/performance")({
  component: Performance,
});

function Performance() {
  const { companies } = useCompanies();
  const data = aggregatePerformance(companies);

  if (!data.completedAssessments) {
    return (
      <div className="space-y-4 max-w-3xl">
        <div>
          <h1 className="text-2xl font-bold">Performance Analysis</h1>
          <p className="text-sm text-muted-foreground">Real insights from completed assessments</p>
        </div>
        <div className="rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">
          No assessment results yet. Complete an MCQ test for any company to see performance analytics.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Performance Analysis</h1>
          <p className="text-sm text-muted-foreground">Aggregated across all companies</p>
        </div>
        <div className="rounded-2xl px-5 py-3 bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white shadow">
          <div className="text-xs opacity-80">Average score</div>
          <div className="text-3xl font-bold">{data.averageScore}%</div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Completed Assessments" value={String(data.completedAssessments)} />
        <StatCard label="Strong Topics" value={String(data.strongTopics.length)} />
        <StatCard label="Weak Topics" value={String(data.weakTopics.length)} />
        <StatCard label="Companies Tracked" value={String(companies.length)} />
      </div>

      {data.trend.length > 1 && (
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-semibold mb-3">Improvement Trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data.trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis fontSize={12} domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#d946ef" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        <Panel title="Weak Topics" icon={AlertTriangle} color="text-rose-500" items={data.weakTopics} />
        <Panel title="Strong Topics" icon={TrendingUp} color="text-emerald-500" items={data.strongTopics} />
        <Panel title="Next Focus" icon={Lightbulb} color="text-amber-500" items={data.weakTopics.slice(0, 5)} />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold mt-2">{value}</div>
    </div>
  );
}

function Panel({
  title,
  icon: Icon,
  color,
  items,
}: {
  title: string;
  icon: typeof AlertTriangle;
  color: string;
  items: string[];
}) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`h-4 w-4 ${color}`} />
        <h3 className="font-semibold">{title}</h3>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items to show.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {items.map((it) => (
            <li key={it} className="flex gap-2">
              <span className="text-muted-foreground">•</span>
              <span>{it}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
