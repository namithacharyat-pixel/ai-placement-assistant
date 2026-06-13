import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect, type ReactNode } from "react";
import { Clock, CheckCircle2, Loader2 } from "lucide-react";
import { analyzePerformance, generateMCQ, getErrorMessage } from "@/services/api";
import { useCompanies } from "@/context/CompanyContext";
import { TopicSelector } from "@/components/TopicSelector";
import { appendPerformance } from "@/lib/companyUtils";
import type { PerformanceReport, TopicCategory } from "@/lib/types/company";

export const Route = createFileRoute("/app/mcq")({
  component: MCQ,
});

type McqItem = {
  question: string;
  options: string[];
  correct_answer: string;
};

function resolveAnswer(options: string[], answer: any) {
  const trimmed = String(answer ?? "").trim();

  if (options.includes(trimmed)) {
    return trimmed;
  }

  const letter = trimmed.toUpperCase();

  if (letter.length === 1 && letter >= "A" && letter <= "Z") {
    const idx = letter.charCodeAt(0) - 65;

    if (options[idx]) {
      return options[idx];
    }
  }

  const numeric = Number(trimmed);

  if (!Number.isNaN(numeric)) {
    const idx = numeric - 1;

    if (options[idx]) {
      return options[idx];
    }
  }

  return trimmed;
}

function MCQ() {
  const { activeCompany, patchCompany } = useCompanies();
  const [phase, setPhase] = useState<"setup" | "quiz" | "result">("setup");
  const [category, setCategory] = useState<TopicCategory | "">("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);
  const [questions, setQuestions] = useState<McqItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [time, setTime] = useState(15 * 60);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState<PerformanceReport | null>(null);

  useEffect(() => {
    if (phase !== "quiz") return;
    const t = setInterval(() => setTime((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [phase]);

  if (!activeCompany) {
    return <EmptyCompany />;
  }

  const startTest = async () => {
    if (!topic.trim()) {
      setError("Select a category and topic first.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const data = await generateMCQ(topic.trim(), difficulty, count);
      const mcqs = data.mcqs ?? [];
      if (!mcqs.length) {
        setError("No questions were generated.");
        return;
      }
      setQuestions(mcqs);
      setAnswers({});
      setIdx(0);
      setTime(15 * 60);
      setPhase("quiz");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const submitTest = async () => {
    setSubmitting(true);
    setError("");
    try {
      const studentAnswers = questions.map((q, i) => ({
        question_id: `q${i + 1}`,
        topic,
        answer: answers[i] ?? "",
      }));
      const correctAnswers = questions.map((q, i) => ({
        question_id: `q${i + 1}`,
        topic,
        answer: resolveAnswer(q.options, q.correct_answer),
      }));

      const result = await analyzePerformance(studentAnswers, correctAnswers);
      const saved: PerformanceReport = {
        ...result,
        topic,
        type: "mcq",
        completed_at: new Date().toISOString(),
      };
      setReport(saved);
      await patchCompany(activeCompany.id, appendPerformance(activeCompany, saved));
      setPhase("result");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setPhase("setup");
    setQuestions([]);
    setAnswers({});
    setIdx(0);
    setReport(null);
    setError("");
    setTime(15 * 60);
  };

  if (phase === "setup") {
    return (
      <div className="max-w-xl mx-auto space-y-6">
        <Header companyName={activeCompany.company_name} />
        <div className="rounded-2xl border bg-card p-6 space-y-4">
          <TopicSelector
            company={activeCompany}
            category={category}
            topic={topic}
            onCategoryChange={setCategory}
            onTopicChange={setTopic}
          />
          <Field label="Difficulty">
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="w-full h-10 rounded-lg border bg-background px-3 text-sm">
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </Field>
          <Field label="Number of questions">
            <input type="number" min={1} max={20} value={count} onChange={(e) => setCount(Number(e.target.value))} className="w-full h-10 rounded-lg border bg-background px-3 text-sm" />
          </Field>
        </div>
        {error && <ErrorBox message={error} />}
        <button onClick={startTest} disabled={loading} className="h-10 px-6 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white inline-flex items-center gap-2 disabled:opacity-60">
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Generating..." : "Start Test"}
        </button>
      </div>
    );
  }

  if (phase === "result" && report) {
    return (
      <div className="max-w-xl mx-auto space-y-5 py-8">
        <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto" />
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold">Assessment Complete</h1>
          <p className="text-muted-foreground">Score: <span className="font-semibold text-foreground">{report.score}%</span></p>
        </div>
        <ResultPanel title="Strong Topics" items={report.strong_topics} />
        <ResultPanel title="Weak Topics" items={report.weak_topics} />
        <ResultPanel title="Recommendations" items={report.recommendations} />
        <div className="grid grid-cols-2 gap-3">
          <button onClick={reset} className="h-10 rounded-lg border bg-card text-sm hover:bg-muted">More MCQs</button>
          <ActionLink to="/app/coding" label="Coding Questions" />
          <ActionLink to="/app/schedule" label="View Roadmap" />
          <ActionLink to="/app" label="Main Menu" />
        </div>
      </div>
    );
  }

  const mm = String(Math.floor(time / 60)).padStart(2, "0");
  const ss = String(time % 60).padStart(2, "0");
  const q = questions[idx];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Header companyName={activeCompany.company_name} subtitle={`Question ${idx + 1} of ${questions.length}`} />
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-sm font-mono">
          <Clock className="h-4 w-4" /> {mm}:{ss}
        </div>
      </div>
      {error && <ErrorBox message={error} />}
      <div className="rounded-2xl border bg-card p-6 space-y-5">
        <div className="text-lg font-medium">{q.question}</div>
        <div className="grid gap-3">
          {q.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => setAnswers({ ...answers, [idx]: opt })}
              className={`text-left px-4 py-3 rounded-xl border transition flex items-center gap-3 ${
                answers[idx] === opt ? "border-primary bg-primary/5" : "hover:bg-muted"
              }`}
            >
              <span className={`h-7 w-7 rounded-full grid place-items-center text-xs font-semibold ${
                answers[idx] === opt ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}>{String.fromCharCode(65 + i)}</span>
              <span className="text-sm">{opt}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="flex justify-between">
        <button onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0} className="h-10 px-4 rounded-lg border disabled:opacity-50">Previous</button>
        {idx < questions.length - 1 ? (
          <button onClick={() => setIdx((i) => i + 1)} className="h-10 px-6 rounded-lg bg-primary text-primary-foreground">Next</button>
        ) : (
          <button onClick={submitTest} disabled={submitting} className="h-10 px-6 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white inline-flex items-center gap-2 disabled:opacity-60">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Submit
          </button>
        )}
      </div>
    </div>
  );
}

function Header({ companyName, subtitle }: { companyName: string; subtitle?: string }) {
  return (
    <div>
      <h1 className="text-xl font-bold">MCQ Assessment — {companyName}</h1>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block space-y-1.5"><span className="text-sm font-medium">{label}</span>{children}</label>;
}

function ResultPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <h3 className="font-semibold mb-2">{title}</h3>
      {items.length ? (
        <ul className="space-y-1 text-sm">{items.map((item) => <li key={item}>• {item}</li>)}</ul>
      ) : (
        <p className="text-sm text-muted-foreground">None identified.</p>
      )}
    </div>
  );
}

function ActionLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="h-10 rounded-lg border bg-card text-sm grid place-items-center hover:bg-muted">
      {label}
    </Link>
  );
}

function EmptyCompany() {
  return (
    <div className="rounded-xl border bg-card p-8 text-center space-y-3">
      <p className="text-sm text-muted-foreground">Select a company before taking an assessment.</p>
      <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">Company Dashboard</Link>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">{message}</div>;
}
