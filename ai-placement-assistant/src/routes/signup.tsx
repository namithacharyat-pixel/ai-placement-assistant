import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Sparkles } from "lucide-react";

export const Route = createFileRoute("/signup")({
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-indigo-700 via-violet-600 to-fuchsia-600 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_70%_30%,white,transparent_40%)]" />
        <div className="relative flex items-center gap-2">
          <div className="h-10 w-10 rounded-xl bg-white/15 grid place-items-center backdrop-blur">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="font-semibold text-lg">PrepAI</span>
        </div>
        <div className="relative space-y-4">
          <h1 className="text-4xl font-bold leading-tight">
            Start prepping smarter, not harder.
          </h1>
          <p className="text-white/80">
            Join thousands of students cracking placements with AI-driven preparation.
          </p>
        </div>
        <div className="relative text-xs text-white/60">© 2026 PrepAI</div>
      </div>

      <div className="flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md space-y-6">
          <div>
            <h2 className="text-2xl font-bold">Create your account</h2>
            <p className="text-sm text-muted-foreground">Get started in less than a minute.</p>
          </div>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              navigate({ to: "/app" });
            }}
          >
            {[
              { label: "Full name", type: "text", placeholder: "Aarav Sharma" },
              { label: "Email", type: "email", placeholder: "you@college.edu" },
              { label: "Password", type: "password", placeholder: "••••••••" },
              { label: "Confirm password", type: "password", placeholder: "••••••••" },
            ].map((f) => (
              <div className="space-y-1.5" key={f.label}>
                <label className="text-sm font-medium">{f.label}</label>
                <input
                  type={f.type}
                  required
                  placeholder={f.placeholder}
                  className="w-full h-11 rounded-lg border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            ))}
            <button
              type="submit"
              className="w-full h-11 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-medium hover:opacity-90 transition"
            >
              Create account
            </button>
          </form>
          <div className="text-sm text-center text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="text-primary font-medium hover:underline">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
