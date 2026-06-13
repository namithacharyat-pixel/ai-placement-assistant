import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/layouts/AppLayout";
import { CompanyProvider } from "@/context/CompanyContext";

export const Route = createFileRoute("/app")({
  component: AppShell,
});

function AppShell() {
  return (
    <CompanyProvider>
      <AppLayout />
    </CompanyProvider>
  );
}
