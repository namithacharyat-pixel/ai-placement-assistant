import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { FileText, Sparkles, Loader2 } from "lucide-react";
import { analyzeResume, getErrorMessage } from "@/services/api";
import { useCompanies } from "@/context/CompanyContext";
import { deriveAtsRating } from "@/lib/companyUtils";
import type { ResumeMatch } from "@/lib/types/company";

export const Route = createFileRoute("/app/resume-match")({
  component: ResumeMatch,
});

function ResumeMatch() {
  const { activeCompany, patchCompany } = useCompanies();
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState<ResumeMatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (activeCompany?.jd_text) setJdText(activeCompany.jd_text);
    if (activeCompany?.resume_match) setResult(activeCompany.resume_match);
  }, [activeCompany]);

  if (!activeCompany) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-3">
        <p className="text-sm text-muted-foreground">Select a company before running resume match.</p>
        <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">
          Company Dashboard
        </Link>
      </div>
    );
  }

  const handleAnalyze = async () => {
    setError("");
    setResult(null);

    if (!resumeText.trim() || !jdText.trim()) {
      setError("Please provide both resume and JD text.");
      return;
    }

    setLoading(true);
    try {
      const data = await analyzeResume(resumeText.trim(), jdText.trim());
      const saved: ResumeMatch = {
        ...data,
        ats_rating: deriveAtsRating(data.match_score ?? 0),
        saved_at: new Date().toISOString(),
      };
      setResult(saved);
      await patchCompany(activeCompany.id, {
        resume_match: saved,
        missing_skills: data.missing_skills ?? activeCompany.missing_skills,
        jd_text: jdText.trim(),
      });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Resume Match — {activeCompany.company_name}</h1>
        <p className="text-sm text-muted-foreground">Compare your resume against the company JD.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="border rounded-2xl p-5 bg-card">
          <div className="font-medium mb-2 flex items-center gap-2"><FileText className="h-4 w-4" /> Resume text</div>
          <textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste your resume here..."
            className="w-full h-52 rounded-lg border bg-background p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="border rounded-2xl p-5 bg-card">
          <div className="font-medium mb-2 flex items-center gap-2"><FileText className="h-4 w-4" /> Job description</div>
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste the job description here..."
            className="w-full h-52 rounded-lg border bg-background p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">{error}</div>}

      <button
        onClick={handleAnalyze}
        disabled={loading}
        className="inline-flex items-center gap-2 h-11 px-6 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-medium hover:opacity-90 disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {loading ? "Analyzing..." : "Analyze Resume Match"}
      </button>

      {result && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex flex-wrap gap-4">
            <StatCard label="Match score" value={`${result.match_score}%`} />
            <StatCard label="ATS rating" value={`${result.ats_rating ?? deriveAtsRating(result.match_score)}/5`} />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <ListPanel title="Matched skills" items={result.matched_skills} />
            <ListPanel title="Missing skills" items={result.missing_skills} />
          </div>
          <div className="rounded-2xl border bg-card p-5">
            <h3 className="font-semibold mb-3">Suggestions</h3>
            <ul className="space-y-2 text-sm">
              {(result.resume_suggestions ?? []).map((item) => (
                <li key={item} className="flex gap-2"><span className="text-muted-foreground">•</span><span>{item}</span></li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl px-6 py-4 bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white shadow">
      <div className="text-xs opacity-80">{label}</div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}

function ListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border bg-card p-5">
      <div className="text-sm text-muted-foreground mb-3">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((s) => (
          <span key={s} className="px-3 py-1 rounded-full text-xs font-medium bg-accent text-accent-foreground">{s}</span>
        ))}
      </div>
    </div>
  );
}
