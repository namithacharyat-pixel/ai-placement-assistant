import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  Upload,
  FileSearch,
  ListChecks,
  Code2,
  CalendarDays,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { useCompanies } from "@/context/CompanyContext";
import { calcOverallProgress, calcRoadmapProgress } from "@/lib/companyUtils";
import { INTERVIEW_ROUNDS, TERMINAL_STATUSES } from "@/lib/types/company";

export const Route = createFileRoute("/app/prepare")({
  component: PrepareHub,
});

const quickLinks = [
  { to: "/app/upload-jd", label: "JD Analysis", icon: Upload },
  { to: "/app/resume-match", label: "Resume Match", icon: FileSearch },
  { to: "/app/mcq", label: "MCQ Assessment", icon: ListChecks },
  { to: "/app/coding", label: "Coding Assessment", icon: Code2 },
  { to: "/app/schedule", label: "Study Roadmap", icon: CalendarDays },
];

function PrepareHub() {
  const { activeCompany, loading, patchCompany, nextRound, setRoundStatus } = useCompanies();
  const [savingDate, setSavingDate] = useState(false);
  const [interviewDate, setInterviewDate] = useState("");

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading preparation...
      </div>
    );
  }

  if (!activeCompany) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-3">
        <p className="text-sm text-muted-foreground">Select a company from the dashboard to continue preparation.</p>
        <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">
          Go to Company Dashboard
        </Link>
      </div>
    );
  }

  const progress = calcOverallProgress(activeCompany);
  const roadmapProgress = calcRoadmapProgress(activeCompany);
  const currentDate = interviewDate || activeCompany.interview_date || "";

  const saveInterviewDate = async () => {
    if (!currentDate) return;
    setSavingDate(true);
    try {
      await patchCompany(activeCompany.id, {
        interview_date: currentDate,
        roadmap_data: null,
        daily_plan_progress: {},
        completed_days: {},
      });
    } finally {
      setSavingDate(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="rounded-2xl p-6 bg-gradient-to-br from-violet-600 via-fuchsia-600 to-indigo-600 text-white shadow-lg">
        <div className="text-xs uppercase tracking-wider opacity-80">Active preparation</div>
        <h1 className="text-2xl md:text-3xl font-bold mt-1">{activeCompany.company_name}</h1>
        <p className="text-white/80 mt-2 text-sm">
          Round: {activeCompany.current_round} • Progress: {progress}% • Roadmap: {roadmapProgress}%
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl border bg-card p-5 space-y-3">
          <h2 className="font-semibold">Interview Round</h2>
          <div className="text-sm">Current: <span className="font-medium">{activeCompany.current_round}</span></div>
          <div className="flex flex-wrap gap-2">
            {INTERVIEW_ROUNDS.map((round) => (
              <button
                key={round}
                onClick={() => setRoundStatus(activeCompany.id, round)}
                className={`text-xs px-3 py-1.5 rounded-full border ${
                  activeCompany.current_round === round ? "bg-primary text-primary-foreground border-primary" : "hover:bg-muted"
                }`}
              >
                {round}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => nextRound(activeCompany.id)}
              className="text-xs px-3 py-1.5 rounded-full border hover:bg-muted"
            >
              Move to next round
            </button>
            {TERMINAL_STATUSES.slice(0, 2).map((status) => (
              <button
                key={status}
                onClick={() => setRoundStatus(activeCompany.id, status)}
                className="text-xs px-3 py-1.5 rounded-full border hover:bg-muted"
              >
                Mark {status}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border bg-card p-5 space-y-3">
          <h2 className="font-semibold">Interview Date</h2>
          <input
            type="date"
            value={currentDate}
            onChange={(e) => setInterviewDate(e.target.value)}
            className="w-full h-10 rounded-lg border bg-background px-3 text-sm"
          />
          <button
            onClick={saveInterviewDate}
            disabled={savingDate || !currentDate}
            className="h-9 px-4 rounded-lg border text-sm disabled:opacity-50 inline-flex items-center gap-2"
          >
            {savingDate && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {savingDate ? "Updating..." : "Reschedule / Update"}
          </button>
          <p className="text-xs text-muted-foreground">
            Updating the interview date clears the saved roadmap so a new schedule can be generated.
          </p>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {quickLinks.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-xl border bg-card p-4 hover:shadow-md transition flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
