/** Company and preparation workflow types. */

export const INTERVIEW_ROUNDS = [
  "OA",
  "Coding Round",
  "Technical Interview",
  "Group Discussion",
  "HR Interview",
] as const;

export const TERMINAL_STATUSES = ["Selected", "Rejected", "Waiting For Result"] as const;

export type TopicCategory = "technologies" | "dsa" | "cs" | "skills";

export type JDAnalysis = {
  skills: string[];
  technologies: string[];
  dsa_topics: string[];
  cs_topics: string[];
};

export type ResumeMatch = {
  match_score: number;
  ats_rating?: number;
  matched_skills: string[];
  missing_skills: string[];
  resume_suggestions: string[];
  saved_at?: string;
};

export type PerformanceReport = {
  score: number;
  strong_topics: string[];
  weak_topics: string[];
  recommendations: string[];
  topic?: string;
  type?: "mcq" | "coding";
  completed_at?: string;
};

export type RoadmapDay = {
  dayKey: string;
  dayNumber: number;
  weekNumber: number;
  label: string;
  topics: string[];
  completed: boolean;
};

export type Company = {
  id: string;
  company_name: string;
  name: string;
  interview_date: string | null;
  hours_per_day: number;
  current_round: string;
  interview_status: string | null;
  interview_rounds: Array<{ name: string; status: string }>;
  jd_text: string;
  jd_analysis: JDAnalysis | null;
  resume_match: ResumeMatch | null;
  missing_skills: string[];
  weak_topics: string[];
  roadmap_data: Record<string, unknown> | null;
  roadmap_topics: string[];
  completed_days: Record<string, boolean>;
  daily_plan_progress: Record<string, { completed: boolean; completed_at?: string | null }>;
  performance_history: PerformanceReport[];
  assessments: PerformanceReport[];
  created_at?: string;
  updated_at?: string;
};

export const TOPIC_CATEGORY_LABELS: Record<TopicCategory, string> = {
  technologies: "Technologies",
  dsa: "DSA",
  cs: "CS Fundamentals",
  skills: "Soft Skills",
};

export const TOPIC_CATEGORY_ORDER: TopicCategory[] = [
  "technologies",
  "dsa",
  "cs",
  "skills",
];
