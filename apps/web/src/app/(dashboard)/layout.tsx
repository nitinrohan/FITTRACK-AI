"use client";

/**
 * Protected dashboard layout — wraps all /dashboard/* routes.
 *
 * This layout handles the brief window between:
 *   1. The middleware allowing the request through (cookie present).
 *   2. The AuthProvider finishing its /me fetch (isInitialized = true).
 *
 * During that gap it renders a loading screen instead of a flash of
 * unauthenticated content. Once initialized, if there's no user (cookie
 * was present but expired) it redirects to /auth/login.
 */

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/use-auth";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isLoading, isInitialized, needsOnboarding } = useAuth();

  useEffect(() => {
    if (!isInitialized) return;
    if (!user) {
      router.replace("/auth/login");
    } else if (needsOnboarding) {
      // New user: redirect to the onboarding wizard before showing the dashboard.
      router.replace("/onboarding");
    }
  }, [isInitialized, user, needsOnboarding, router]);

  // Show full-screen loader during initial session restore.
  if (!isInitialized || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-50">
        <LoadingSpinner size="lg" label="Loading your account…" />
      </div>
    );
  }

  // Avoid rendering children if we know the user isn't authenticated
  // or needs onboarding. The useEffect above will trigger the redirect.
  if (!user || needsOnboarding) {
    return null;
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/*
       * Navigation shell — placeholder until Phase 5 (Dashboard).
       * A real nav with user menu, links, and mobile drawer will be built then.
       */}
      <header className="border-b border-surface-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
              aria-label="FitTrack AI — home"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500">
                <svg
                  className="h-5 w-5 text-white"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
                  <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
                  <line x1="6" y1="1" x2="6" y2="4" />
                  <line x1="10" y1="1" x2="10" y2="4" />
                  <line x1="14" y1="1" x2="14" y2="4" />
                </svg>
              </div>
              <span className="font-semibold text-surface-900">FitTrack AI</span>
            </Link>
            <NavLinks />
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-surface-500 sm:block">
              {user.profile?.display_name ?? user.email}
            </span>
            {/* Sign-out button — placeholder, will be in proper nav in Phase 5 */}
            <SignOutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/goals", label: "Goals" },
  { href: "/dashboard/weight", label: "Weight" },
] as const;

function NavLinks() {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary navigation">
      <ul className="hidden items-center gap-1 sm:flex">
        {NAV_LINKS.map(({ href, label }) => {
          const active =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-surface-600 hover:bg-surface-100 hover:text-surface-900"
                )}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function SignOutButton() {
  const router = useRouter();
  const { logout } = useAuth();

  async function handleSignOut() {
    await logout();
    router.push("/");
    router.refresh();
  }

  return (
    <button
      onClick={handleSignOut}
      className="rounded-lg px-3 py-1.5 text-sm text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
    >
      Sign out
    </button>
  );
}
