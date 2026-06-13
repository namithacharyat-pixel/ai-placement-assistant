import {
  activateCompany,
  createCompany,
  deleteCompany,
  fetchCompanies,
  updateCompany,
  advanceCompanyRound,
  setCompanyRoundStatus,
} from "@/services/api";
import type { Company } from "@/lib/types/company";
import { loadFallbackCompanies, saveFallbackCompanies } from "@/lib/companyUtils";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type CompanyContextValue = {
  companies: Company[];
  activeCompany: Company | null;
  activeCompanyId: string | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  addCompany: (name: string, interviewDate?: string, hoursPerDay?: number) => Promise<Company>;
  removeCompany: (id: string) => Promise<void>;
  selectCompany: (id: string) => Promise<void>;
  patchCompany: (id: string, patch: Partial<Company>) => Promise<Company>;
  nextRound: (id: string) => Promise<Company>;
  setRoundStatus: (id: string, status: string) => Promise<Company>;
};

const CompanyContext = createContext<CompanyContextValue | null>(null);

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchCompanies();
      setCompanies(data.companies ?? []);
      setActiveCompanyId(data.active_company_id ?? null);
      saveFallbackCompanies({
        active_company_id: data.active_company_id ?? null,
        companies: data.companies ?? [],
      });
    } catch {
      const fallback = loadFallbackCompanies();
      setCompanies(fallback.companies);
      setActiveCompanyId(fallback.active_company_id);
      setError("Could not reach backend. Using saved local company data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const patchCompany = useCallback(async (id: string, patch: Partial<Company>) => {
    const updated = await updateCompany(id, patch);
    await refresh();
    return updated;
  }, [refresh]);

  const addCompany = useCallback(async (name: string, interviewDate?: string, hoursPerDay = 2) => {
    const created = await createCompany({ company_name: name, interview_date: interviewDate, hours_per_day: hoursPerDay });
    setCompanies((prev) => [...prev, created]);
    setActiveCompanyId(created.id);
    await refresh();
    return created;
  }, [refresh]);

  const removeCompany = useCallback(async (id: string) => {
    await deleteCompany(id);
    await refresh();
  }, [refresh]);

  const selectCompany = useCallback(async (id: string) => {
    await activateCompany(id);
    setActiveCompanyId(id);
    await refresh();
  }, [refresh]);

  const nextRound = useCallback(async (id: string) => {
    const updated = await advanceCompanyRound(id);
    setCompanies((prev) => prev.map((c) => (c.id === id ? updated : c)));
    return updated;
  }, []);

  const setRoundStatus = useCallback(async (id: string, status: string) => {
    const updated = await setCompanyRoundStatus(id, status);
    setCompanies((prev) => prev.map((c) => (c.id === id ? updated : c)));
    return updated;
  }, []);

  const activeCompany = useMemo(
    () => companies.find((c) => c.id === activeCompanyId) ?? null,
    [companies, activeCompanyId],
  );

  const value = useMemo(
    () => ({
      companies,
      activeCompany,
      activeCompanyId,
      loading,
      error,
      refresh,
      addCompany,
      removeCompany,
      selectCompany,
      patchCompany,
      nextRound,
      setRoundStatus,
    }),
    [
      companies,
      activeCompany,
      activeCompanyId,
      loading,
      error,
      refresh,
      addCompany,
      removeCompany,
      selectCompany,
      patchCompany,
      nextRound,
      setRoundStatus,
    ],
  );

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}

export function useCompanies() {
  const ctx = useContext(CompanyContext);
  if (!ctx) throw new Error("useCompanies must be used within CompanyProvider");
  return ctx;
}
