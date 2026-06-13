import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import {
  generateCodingQuestion,
  reviewSolution,
  getRecommendation,
  getErrorMessage,
} from "@/services/api";
import { useCompanies } from "@/context/CompanyContext";
import { TopicSelector } from "@/components/TopicSelector";
import type { TopicCategory } from "@/lib/types/company";

export const Route = createFileRoute("/app/coding")({
  component: Coding,
});

type CodingQuestion = {
  title: string;
  difficulty: string;
  problem_statement: string;
  constraints: string[];
  sample_input: string;
  sample_output: string;
  starter_code_java?: string;
  starter_code_python?: string;
  starter_code_cpp?: string;
  starter_code_c?: string;
};

type ReviewResult = {
  correctness: string;
  time_complexity: string;
  space_complexity: string;
  optimization_suggestions?: string[];
  interview_feedback: string;
};

type Recommendation = {
  next_topic: string;
  difficulty: string;
  reason: string;
};

function Coding() {
  const { activeCompany } = useCompanies();
  const [category, setCategory] = useState<TopicCategory | "">("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [language, setLanguage] = useState("java");
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [problem, setProblem] = useState<CodingQuestion | null>(null);
  const [code, setCode] = useState("");
  const [completed, setCompleted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!activeCompany) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-3">
        <p className="text-sm text-muted-foreground">Select a company before taking a coding assessment.</p>
        <Link to="/app" className="inline-flex h-10 px-5 rounded-lg bg-primary text-primary-foreground items-center">Company Dashboard</Link>
      </div>
    );
  }

  const loadQuestion = async () => {
    if (!topic.trim()) {
      setError("Select a category and topic first.");
      return;
    }
    setError("");
    setCompleted(false);
    setReview(null);
    setLoading(true);
    try {
      const data = await generateCodingQuestion(
        topic.trim(),
        difficulty,
        category,
        activeCompany.company_name,
        language
      );
      setProblem(data);
      if (language === "java") {
        setCode(data.starter_code_java || "");
      } else if (language === "python") {
        setCode(data.starter_code_python || "");
      } else if (language === "cpp") {
        setCode(data.starter_code_cpp || "");
      } else {
        setCode(data.starter_code_c || "");
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async () => {
    if (!problem) return;

    try {
      setReviewLoading(true);

      const data = await reviewSolution(
        problem.problem_statement,
        code,
        language
      );

      setReview(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  };

  if (completed) {
    return (
      <div className="max-w-xl mx-auto space-y-4 py-8 text-center">
        <h1 className="text-2xl font-bold">Coding Question Completed</h1>
        <p className="text-sm text-muted-foreground">Keep practicing to improve your interview readiness.</p>
        <div className="grid grid-cols-2 gap-3">
          <button onClick={() => { setCompleted(false); setProblem(null); }} className="h-10 rounded-lg border">Another Coding Question</button>
          <Link to="/app/mcq" className="h-10 rounded-lg border grid place-items-center">Mixed Assessment</Link>
          <Link to="/app/schedule" className="h-10 rounded-lg border grid place-items-center">View Roadmap</Link>
          <Link to="/app" className="h-10 rounded-lg border grid place-items-center">Main Menu</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">Coding Assessment — {activeCompany.company_name}</h1>
      </div>

      <div className="rounded-2xl border bg-card p-5 space-y-4">
        <TopicSelector
          company={activeCompany}
          category={category}
          topic={topic}
          onCategoryChange={setCategory}
          onTopicChange={setTopic}
        />

        <div className="flex flex-wrap gap-4">
          <label className="space-y-1.5 block">
            <span className="text-sm font-medium">Difficulty</span>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="h-10 rounded-lg border bg-background px-3 text-sm w-40">
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>

          <label className="space-y-1.5 block">
            <span className="text-sm font-medium">Language</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="h-10 rounded-lg border bg-background px-3 text-sm w-40"
            >
              <option value="java">Java</option>
              <option value="python">Python</option>
              <option value="cpp">C++</option>
              <option value="c">C</option>
              <option value="sql">SQL</option>
            </select>
          </label>
        </div>

        <button onClick={loadQuestion} disabled={loading} className="inline-flex items-center gap-2 h-10 px-5 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white disabled:opacity-60">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Loading..." : "Generate Question"}
        </button>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 text-rose-700 px-4 py-3 text-sm">{error}</div>}

      {!problem && !loading && !error && (
        <p className="text-sm text-muted-foreground">Select a topic and generate a coding question.</p>
      )}

      {problem && (
        <div className="grid lg:grid-cols-2 gap-4 h-[calc(100vh-16rem)]">
          <div className="rounded-2xl border bg-card p-6 overflow-y-auto">
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-xl font-bold">{problem.title}</h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700">{problem.difficulty}</span>
            </div>
            <p className="text-sm text-muted-foreground whitespace-pre-line mb-4">{problem.problem_statement}</p>
            {problem.constraints?.length > 0 && (
              <>
                <h3 className="font-semibold text-sm mb-2">Constraints</h3>
                <ul className="text-sm text-muted-foreground list-disc pl-5 mb-4 space-y-1">
                  {problem.constraints.map((c) => <li key={c}>{c}</li>)}
                </ul>
              </>
            )}
            <h3 className="font-semibold text-sm mb-2">Sample Input / Output</h3>
            <div className="rounded-lg bg-muted p-3 text-xs font-mono space-y-2">
              <div><span className="text-muted-foreground">Input: </span>{problem.sample_input}</div>
              <div><span className="text-muted-foreground">Output: </span>{problem.sample_output}</div>
            </div>
          </div>

          <div className="flex flex-col rounded-2xl border bg-[#0d1117] text-slate-100 overflow-hidden">
            <div className="px-4 py-2 border-b border-white/10 text-xs text-slate-400">solution.js</div>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} spellCheck={false} className="flex-1 bg-transparent p-4 font-mono text-sm resize-none focus:outline-none" />

            {review && (
              <div className="border-t border-white/10 p-4 text-sm space-y-2">
                <p>
                  <strong>Correctness: </strong>
                  {review.correctness}
                </p>
                <p>
                  <strong>Time Complexity: </strong>
                  {review.time_complexity}
                </p>
                <p>
                  <strong>Space Complexity: </strong>
                  {review.space_complexity}
                </p>
                <p>
                  <strong>Interview Feedback: </strong>
                  {review.interview_feedback}
                </p>
              </div>
            )}

            <div className="border-t border-white/10 p-3 flex gap-2">
              <button
                onClick={handleReview}
                disabled={reviewLoading}
                className="h-8 px-3 rounded-md bg-blue-600 text-xs"
              >
                {reviewLoading ? "Reviewing..." : "AI Review"}
              </button>

              <button
                onClick={() => setCompleted(true)}
                className="h-8 px-3 rounded-md bg-emerald-600 text-xs"
              >
                Mark Complete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
