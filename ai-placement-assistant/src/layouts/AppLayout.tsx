import { Link, useRouterState, useNavigate, Outlet } from "@tanstack/react-router";
import { useState } from "react";
import {
  Building2,
  Upload,
  MessageSquare,
  ListChecks,
  Code2,
  BarChart3,
  CalendarDays,
  LogOut,
  Menu,
  Sparkles,
  FileSearch,
  PlayCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCompanies } from "@/context/CompanyContext";

const nav = [
  { to: "/app", label: "Companies", icon: Building2, exact: true },
  { to: "/app/prepare", label: "Preparation", icon: PlayCircle },
  { to: "/app/upload-jd", label: "JD Analysis", icon: Upload },
  { to: "/app/resume-match", label: "Resume Match", icon: FileSearch },
  { to: "/app/mcq", label: "MCQ Test", icon: ListChecks },
  { to: "/app/coding", label: "Coding Test", icon: Code2 },
  { to: "/app/performance", label: "Performance", icon: BarChart3 },
  { to: "/app/schedule", label: "Study Roadmap", icon: CalendarDays },
  { to: "/app/chat", label: "AI Chat", icon: MessageSquare },
];

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { activeCompany } = useCompanies();

  const isActive = (to: string, exact?: boolean) =>
    exact ? pathname === to : pathname === to || pathname.startsWith(to + "/");

  return (
    <div className="min-h-screen flex bg-background">
      <aside
        className={cn(
          "bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col transition-all duration-300 sticky top-0 h-screen",
          collapsed ? "w-16" : "w-64",
        )}
      >
        <div className="h-16 flex items-center gap-2 px-4 border-b border-sidebar-border">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 grid place-items-center shrink-0">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate">PrepAI</div>
              <div className="text-[10px] text-sidebar-foreground/60 truncate">Placement Assistant</div>
            </div>
          )}
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.to, item.exact);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                  active
                    ? "bg-sidebar-accent text-white"
                    : "hover:bg-sidebar-accent/60 text-sidebar-foreground/80",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-2 border-t border-sidebar-border">
          <button
            onClick={() => navigate({ to: "/login" })}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm hover:bg-sidebar-accent/60 text-sidebar-foreground/80"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b bg-card flex items-center px-4 gap-3 sticky top-0 z-10">
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="h-9 w-9 grid place-items-center rounded-lg hover:bg-muted"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="text-sm text-muted-foreground">
            {activeCompany ? (
              <>
                Preparing for <span className="text-foreground font-medium">{activeCompany.company_name}</span>
              </>
            ) : (
              "Select a company to begin preparation"
            )}
          </div>
        </header>
        <main className="flex-1 p-6 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
