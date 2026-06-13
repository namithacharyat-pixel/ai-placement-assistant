import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";
import { generateRoadmap, getErrorMessage } from "@/services/api";
import { useCompanies } from "@/context/CompanyContext";
import {
  buildPrioritizedTopics,
  buildRoadmapProgressFromRoadmap,
  calcRoadmapProgress,
  flattenRoadmapDays,
} from "@/lib/companyUtils";

export const Route = createFileRoute("/app/schedule")({
  component: Schedule,
});

function Schedule() {
  const { activeCompany, patchCompany } = useCompanies();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [days, setDays] = useState(flattenRoadmapDays(activeCompany ?? ({} as never)));

  useEffect(() => {
    if (activeCompany) setDays(flattenRoadmapDays(activeCompany));
  }, [activeCompany]);

  if (!activeCompany) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-3">
        <p className="text-sm text-muted-foreground">Select a company to view or generate a roadmap.</p>
        <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">Company Dashboard</Link>
      </div>
    );
  }

  const progress = calcRoadmapProgress(activeCompany);
  const hasRoadmap = Boolean(activeCompany.roadmap_data);

  const generateIfNeeded = async () => {
    if (hasRoadmap) return;
    setError("");
    setLoading(true);
    try {
      const topics = buildPrioritizedTopics(activeCompany);
      if (!topics.length) {
        setError("Analyze a JD or complete resume match before generating a roadmap.");
        return;
      }

      const roadmap = await generateRoadmap({
        target_company: activeCompany.company_name,
        interview_date: activeCompany.interview_date ?? undefined,
        hours_per_day: activeCompany.hours_per_day ?? 2,
        weak_topics: activeCompany.weak_topics ?? [],
        missing_skills: activeCompany.missing_skills ?? [],
      });

      const daily_plan_progress = buildRoadmapProgressFromRoadmap(
        roadmap,
        activeCompany.daily_plan_progress ?? {},
      );

      await patchCompany(activeCompany.id, {
        roadmap_data: roadmap,
        roadmap_topics: topics,
        daily_plan_progress,
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleDay = async (dayKey: string, completed: boolean) => {
    const daily_plan_progress = {
      ...(activeCompany.daily_plan_progress ?? {}),
      [dayKey]: {
        completed,
        completed_at: completed ? new Date().toISOString() : null,
      },
    };
    const completed_days = {
      ...(activeCompany.completed_days ?? {}),
      [dayKey]: completed,
    };
    await patchCompany(activeCompany.id, { daily_plan_progress, completed_days });
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Study Roadmap — {activeCompany.company_name}</h1>
          <p className="text-sm text-muted-foreground">
            {hasRoadmap ? "Continue your saved roadmap." : "Generate once and continue daily."}
          </p>
        </div>
        <div className="rounded-xl border bg-card px-4 py-2 text-sm">
          <span className="text-muted-foreground">Roadmap progress:</span>{" "}
          <span className="font-semibold">{progress}%</span>
        </div>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">{error}</div>}

      {!hasRoadmap ? (
        <div className="rounded-xl border bg-card p-8 text-center space-y-4">
          <p className="text-sm text-muted-foreground">No roadmap saved for this company yet.</p>
          <button
            onClick={generateIfNeeded}
            disabled={loading}
            className="inline-flex items-center gap-2 h-11 px-6 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? "Generating..." : "Generate Roadmap"}
          </button>
        </div>
      ) : (
        <div className="rounded-2xl border bg-card p-5 space-y-2">
          {days.length === 0 ? (
            <p className="text-sm text-muted-foreground">Roadmap has no daily tasks yet.</p>
          ) : (
            days.map((day) => (
              <button
                key={day.dayKey}
                onClick={() => toggleDay(day.dayKey, !day.completed)}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted text-left"
              >
                <span className={`h-5 w-5 rounded-md border grid place-items-center ${day.completed ? "bg-primary border-primary" : ""}`}>
                  {day.completed && <Check className="h-3 w-3 text-primary-foreground" />}
                </span>
                <span className={`text-sm ${day.completed ? "line-through text-muted-foreground" : ""}`}>
                  {day.completed ? "✓" : "□"} {day.label}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
