import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Building2, CalendarDays, Loader2, Plus, Trash2, ArrowRight } from "lucide-react";
import { useCompanies } from "@/context/CompanyContext";
import { calcOverallProgress, calcRoadmapProgress, needsInterviewFollowUp } from "@/lib/companyUtils";
import { TERMINAL_STATUSES } from "@/lib/types/company";

export const Route = createFileRoute("/app/")({
  component: CompanyDashboard,
});

function CompanyDashboard() {
  const navigate = useNavigate();
  const { companies, loading, error, addCompany, removeCompany, selectCompany, setRoundStatus } = useCompanies();
  const [name, setName] = useState("");
  const [interviewDate, setInterviewDate] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState("");

  const handleAdd = async () => {
    setFormError("");
    if (!name.trim()) {
      setFormError("Enter a company name.");
      return;
    }
    setCreating(true);
    try {
      await addCompany(name.trim(), interviewDate || undefined);
      setName("");
      setInterviewDate("");
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const handleContinue = async (id: string) => {
    await selectCompany(id);
    navigate({ to: "/app/prepare" });
  };

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold">Company Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Manage multiple interview preparations and continue where you left off.
        </p>
      </div>

      <div className="rounded-2xl border bg-card p-5 grid md:grid-cols-3 gap-4 items-end">
        <label className="space-y-1.5 md:col-span-1">
          <span className="text-sm font-medium">Company name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Google"
            className="w-full h-10 rounded-lg border bg-background px-3 text-sm"
          />
        </label>
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Interview date</span>
          <input
            type="date"
            value={interviewDate}
            onChange={(e) => setInterviewDate(e.target.value)}
            className="w-full h-10 rounded-lg border bg-background px-3 text-sm"
          />
        </label>
        <button
          onClick={handleAdd}
          disabled={creating}
          className="h-10 px-5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white inline-flex items-center justify-center gap-2 disabled:opacity-60"
        >
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Add Company
        </button>
      </div>

      {(formError || error) && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">
          {formError || error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading companies...
        </div>
      ) : companies.length === 0 ? (
        <div className="rounded-xl border bg-card p-8 text-center text-sm text-muted-foreground">
          No companies yet. Add your first target company to start preparation.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {companies.map((company) => (
            <CompanyCard
              key={company.id}
              company={company}
              onContinue={() => handleContinue(company.id)}
              onDelete={() => removeCompany(company.id)}
              onFollowUp={(status) => setRoundStatus(company.id, status)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CompanyCard({
  company,
  onContinue,
  onDelete,
  onFollowUp,
}: {
  company: import("@/lib/types/company").Company;
  onContinue: () => void;
  onDelete: () => void;
  onFollowUp: (status: string) => void;
}) {
  const progress = calcOverallProgress(company);
  const roadmapProgress = calcRoadmapProgress(company);
  const showFollowUp = needsInterviewFollowUp(company);

  return (
    <div className="rounded-2xl border bg-card p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            <h2 className="text-lg font-semibold">{company.company_name}</h2>
          </div>
          <div className="text-sm text-muted-foreground mt-1 flex items-center gap-1.5">
            <CalendarDays className="h-3.5 w-3.5" />
            Interview: {company.interview_date || "Not set"}
          </div>
          <div className="text-sm mt-1">Round: {company.current_round}</div>
        </div>
        <button onClick={onDelete} className="text-muted-foreground hover:text-rose-600">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-muted px-3 py-2">
          <div className="text-xs text-muted-foreground">Progress</div>
          <div className="font-semibold">{progress}%</div>
        </div>
        <div className="rounded-lg bg-muted px-3 py-2">
          <div className="text-xs text-muted-foreground">Roadmap</div>
          <div className="font-semibold">{roadmapProgress}%</div>
        </div>
      </div>

      {showFollowUp && (
        <div className="rounded-lg border p-3 space-y-2">
          <div className="text-sm font-medium">How was your interview?</div>
          <div className="flex flex-wrap gap-2">
            {TERMINAL_STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => onFollowUp(status)}
                className="text-xs px-3 py-1.5 rounded-full border hover:bg-muted"
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={onContinue}
        className="w-full h-10 rounded-lg bg-primary text-primary-foreground inline-flex items-center justify-center gap-2"
      >
        Continue Preparation <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}

function getErrorMessage(err: unknown) {
  if (typeof err === "object" && err && "message" in err) return String((err as Error).message);
  return "Something went wrong.";
}
