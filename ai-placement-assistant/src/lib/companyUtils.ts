import type { Company, JDAnalysis, PerformanceReport, RoadmapDay, TopicCategory } from "@/lib/types/company";
import { TOPIC_CATEGORY_ORDER } from "@/lib/types/company";

const STORAGE_KEY = "prepai_companies_fallback";

export function calcRoadmapProgress(company: Company): number {
  const days = flattenRoadmapDays(company);
  if (!days.length) return 0;
  const done = days.filter((d) => d.completed).length;
  return Math.round((done / days.length) * 100);
}

export function calcOverallProgress(company: Company): number {
  const roadmapPct = calcRoadmapProgress(company);
  const hasJd = company.jd_analysis ? 15 : 0;
  const hasResume = company.resume_match ? 15 : 0;
  const assessmentCount = (company.performance_history ?? []).length;
  const assessmentPct = Math.min(assessmentCount * 10, 30);
  const roundPct = company.interview_rounds.filter((r) => r.status === "completed").length * 5;
  return Math.min(100, Math.round(roadmapPct * 0.4 + hasJd + hasResume + assessmentPct + roundPct));
}

export function flattenRoadmapDays(company: Company): RoadmapDay[] {
  const progress = company.daily_plan_progress ?? {};
  const completedDays = company.completed_days ?? {};
  const roadmap = company.roadmap_data as {
    weeks?: Array<{
      week: number;
      daily_plan?: Array<{ day: number; topics?: string[]; tasks?: string[] }>;
    }>;
  } | null;

  if (!roadmap?.weeks?.length) {
    return Object.entries(progress).map(([dayKey, entry]) => ({
      dayKey,
      dayNumber: Number(dayKey),
      weekNumber: 1,
      label: `Day ${dayKey}`,
      topics: [],
      completed: Boolean(entry?.completed ?? completedDays[dayKey]),
    }));
  }

  const days: RoadmapDay[] = [];
  for (const week of roadmap.weeks) {
    for (const day of week.daily_plan ?? []) {
      const dayKey = `${week.week}-${day.day}`;
      const topics = day.topics?.length ? day.topics : (day.tasks ?? []);
      const label = topics[0] ? `Day ${day.day} ${topics[0]}` : `Day ${day.day}`;
      days.push({
        dayKey,
        dayNumber: day.day,
        weekNumber: week.week,
        label,
        topics,
        completed: Boolean(progress[dayKey]?.completed ?? completedDays[dayKey]),
      });
    }
  }
  return days;
}

export function buildRoadmapProgressFromRoadmap(
  roadmap: Record<string, unknown>,
  existing: Record<string, { completed: boolean; completed_at?: string | null }> = {},
) {
  const progress: Record<string, { completed: boolean; completed_at: string | null }> = {};
  const weeks = (roadmap.weeks as Array<{ week: number; daily_plan?: Array<{ day: number }> }>) ?? [];
  for (const week of weeks) {
    for (const day of week.daily_plan ?? []) {
      const key = `${week.week}-${day.day}`;
      progress[key] = existing[key] ?? { completed: false, completed_at: null };
    }
  }
  return progress;
}

export function buildPrioritizedTopics(company: Company): string[] {
  const jd = company.jd_analysis;
  const groups = [
    company.missing_skills ?? [],
    company.weak_topics ?? [],
    jd?.technologies ?? [],
    jd?.dsa_topics ?? [],
    jd?.cs_topics ?? [],
    jd?.skills ?? [],
  ];

  const seen = new Set<string>();
  const result: string[] = [];
  for (const group of groups) {
    for (const item of group) {
      const cleaned = String(item).trim();
      if (!cleaned) continue;
      const key = cleaned.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(cleaned);
    }
  }
  return result;
}

export function getTopicsByCategory(company: Company): Record<TopicCategory, string[]> {
  const jd = company.jd_analysis;
  return {
    technologies: jd?.technologies ?? [],
    dsa: jd?.dsa_topics ?? [],
    cs: jd?.cs_topics ?? [],
    skills: jd?.skills ?? [],
  };
}

export function getCategoryTopics(company: Company, category: TopicCategory): string[] {
  return getTopicsByCategory(company)[category] ?? [];
}

export function isInterviewDatePassed(interviewDate: string | null): boolean {
  if (!interviewDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(interviewDate);
  return target < today;
}

export function needsInterviewFollowUp(company: Company): boolean {
  return (
    isInterviewDatePassed(company.interview_date) &&
    !company.interview_status &&
    !["Selected", "Rejected"].includes(company.current_round)
  );
}

export function aggregatePerformance(companies: Company[]) {
  const history = companies.flatMap((c) => c.performance_history ?? []);
  if (!history.length) {
    return {
      averageScore: 0,
      completedAssessments: 0,
      weakTopics: [] as string[],
      strongTopics: [] as string[],
      trend: [] as Array<{ label: string; score: number }>,
    };
  }

  const averageScore = Math.round(
    history.reduce((sum, item) => sum + (item.score ?? 0), 0) / history.length,
  );

  const weakSet = new Map<string, number>();
  const strongSet = new Map<string, number>();
  for (const item of history) {
    for (const topic of item.weak_topics ?? []) weakSet.set(topic, (weakSet.get(topic) ?? 0) + 1);
    for (const topic of item.strong_topics ?? []) strongSet.set(topic, (strongSet.get(topic) ?? 0) + 1);
  }

  return {
    averageScore,
    completedAssessments: history.length,
    weakTopics: [...weakSet.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t),
    strongTopics: [...strongSet.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t),
    trend: history.map((item, index) => ({
      label: `#${index + 1}`,
      score: item.score ?? 0,
    })),
  };
}

export function saveFallbackCompanies(data: {
  active_company_id: string | null;
  companies: Company[];
}) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function loadFallbackCompanies(): {
  active_company_id: string | null;
  companies: Company[];
} {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { active_company_id: null, companies: [] };
    const parsed = JSON.parse(raw);
    return {
      active_company_id: parsed.active_company_id ?? null,
      companies: parsed.companies ?? [],
    };
  } catch {
    return { active_company_id: null, companies: [] };
  }
}

export function appendPerformance(company: Company, report: PerformanceReport): Company {
  const performance_history = [...(company.performance_history ?? []), report];
  const weak_topics = [...new Set([...(company.weak_topics ?? []), ...(report.weak_topics ?? [])])];
  return {
    ...company,
    performance_history,
    assessments: performance_history,
    weak_topics,
  };
}

export function deriveAtsRating(matchScore: number): number {
  if (matchScore >= 85) return 5;
  if (matchScore >= 70) return 4;
  if (matchScore >= 55) return 3;
  if (matchScore >= 40) return 2;
  return 1;
}

export { TOPIC_CATEGORY_ORDER };
