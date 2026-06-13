import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Upload, FileText, Sparkles, Loader2 } from "lucide-react";
import { analyzeJD, getErrorMessage } from "@/services/api";
import { useCompanies } from "@/context/CompanyContext";
import type { JDAnalysis } from "@/lib/types/company";

export const Route = createFileRoute("/app/upload-jd")({
  component: UploadJD,
});

function UploadJD() {
  const { activeCompany, patchCompany } = useCompanies();
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<JDAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (activeCompany?.jd_analysis) setAnalysis(activeCompany.jd_analysis);
    if (activeCompany?.jd_text) setText(activeCompany.jd_text);
  }, [activeCompany]);

  if (!activeCompany) {
    return <NoCompany message="Select a company before analyzing a job description." />;
  }

  const handleAnalyze = async () => {
    setError("");
    setAnalysis(null);

    let jdText = text.trim();
    if (file && !jdText) {
      if (file.type === "application/pdf") {
        setError("PDF parsing is not supported. Please paste the JD text instead.");
        return;
      }
      try {
        jdText = (await file.text()).trim();
      } catch {
        setError("Unable to read the uploaded file.");
        return;
      }
    }

    if (!jdText) {
      setError("Please paste a job description or upload a text file.");
      return;
    }

    setLoading(true);
    try {
      const result = await analyzeJD(jdText);
      setAnalysis(result);
      await patchCompany(activeCompany.id, {
        jd_text: jdText,
        jd_analysis: result,
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
        <h1 className="text-2xl font-bold">JD Analysis — {activeCompany.company_name}</h1>
        <p className="text-sm text-muted-foreground">Extract skills and topics for this company profile.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <label
          className="border-2 border-dashed border-border rounded-2xl p-8 text-center cursor-pointer hover:border-primary hover:bg-accent/30 transition flex flex-col items-center justify-center min-h-[220px]"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
          }}
        >
          <input
            type="file"
            accept=".pdf,.txt,.md"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Upload className="h-10 w-10 text-primary mb-3" />
          <div className="font-medium">Drag & drop file here</div>
          {file && (
            <div className="mt-3 text-xs flex items-center gap-2 text-foreground">
              <FileText className="h-3 w-3" /> {file.name}
            </div>
          )}
        </label>

        <div className="border rounded-2xl p-5 bg-card">
          <div className="font-medium mb-2">Paste JD text</div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the job description here..."
            className="w-full h-44 rounded-lg border bg-background p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {error && <ErrorBox message={error} />}

      <button
        onClick={handleAnalyze}
        disabled={loading}
        className="inline-flex items-center gap-2 h-11 px-6 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-medium hover:opacity-90 disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {loading ? "Analyzing..." : "Analyze JD"}
      </button>

      {analysis && (
        <div className="grid md:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-2">
          <TagSection title="Skills" items={analysis.skills} className="bg-violet-100 text-violet-700" />
          <TagSection title="Technologies" items={analysis.technologies} className="bg-fuchsia-100 text-fuchsia-700" />
          <TagSection title="DSA Topics" items={analysis.dsa_topics} className="bg-indigo-100 text-indigo-700" />
          <TagSection title="CS Topics" items={analysis.cs_topics} className="bg-emerald-100 text-emerald-700" />
        </div>
      )}
    </div>
  );
}

function TagSection({ title, items, className }: { title: string; items: string[]; className: string }) {
  return (
    <div className="rounded-2xl border bg-card p-5">
      <div className="text-sm text-muted-foreground mb-3">{title}</div>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items found.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((s) => (
            <span key={s} className={`px-3 py-1 rounded-full text-xs font-medium ${className}`}>{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function NoCompany({ message }: { message: string }) {
  return (
    <div className="rounded-xl border bg-card p-8 text-center space-y-3">
      <p className="text-sm text-muted-foreground">{message}</p>
      <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">
        Company Dashboard
      </Link>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">{message}</div>;
}
