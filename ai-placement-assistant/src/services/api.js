import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export function getErrorMessage(error) {
  return error?.response?.data?.error || error?.message || "Something went wrong.";
}

export async function fetchCompanies() {
  const { data } = await api.get("/companies/");
  return data;
}

export async function createCompany(payload) {
  const { data } = await api.post("/companies/", payload);
  return data;
}

export async function updateCompany(companyId, payload) {
  const { data } = await api.put(`/companies/${companyId}`, payload);
  return data;
}

export async function deleteCompany(companyId) {
  const { data } = await api.delete(`/companies/${companyId}`);
  return data;
}

export async function activateCompany(companyId) {
  const { data } = await api.post(`/companies/${companyId}/activate`);
  return data;
}

export async function advanceCompanyRound(companyId) {
  const { data } = await api.post(`/companies/${companyId}/round/next`);
  return data;
}

export async function setCompanyRoundStatus(companyId, status) {
  const { data } = await api.post(`/companies/${companyId}/round/status`, { status });
  return data;
}

export async function analyzeJD(jdText) {
  const { data } = await api.post("/jd/analyze", { jdText });
  return data;
}

export async function analyzeResume(resumeText, jdText) {
  const { data } = await api.post("/resume/analyze", { resumeText, jdText });
  return data;
}

export async function generateMCQ(topic, difficulty, count) {
  const { data } = await api.post("/assessment/mcq", { topic, difficulty, count });
  return data;
}

export async function generateCodingQuestion(
  topic,
  difficulty = "medium",
  category = "DSA",
  company_name = null,
  language = "java"
) {
  const { data } = await api.post("/assessment/coding", {
    topic,
    difficulty,
    category,
    company_name,
    language,
  });

  return data;
}

export async function reviewSolution(
  question,
  solution,
  language
) {
  const { data } = await api.post("/assessment/review", {
    question,
    solution,
    language,
  });

  return data;
}

export async function getRecommendation(company) {
  const { data } = await api.get(
    `/assessment/recommendation/${company}`
  );

  return data;
}

export async function analyzePerformance(studentAnswers, correctAnswers) {
  const { data } = await api.post("/performance/analyze", {
    student_answers: studentAnswers,
    correct_answers: correctAnswers,
  });
  return data;
}

export async function generateRoadmap(payload) {
  const { data } = await api.post("/roadmap/generate", payload);
  return data;
}

export async function sendChatMessage(message) {
  const { data } = await api.post("/chat", { message });
  return data;
}

export default api;
