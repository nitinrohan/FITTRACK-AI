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

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/use-auth";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";

// ── Theme toggle ──────────────────────────────────────────────────────────────

function useTheme() {
  const [isDark, setIsDark] = useState(false);

  // On mount: read saved preference, then apply it.
  useEffect(() => {
    const saved = localStorage.getItem("fittrack-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = saved ? saved === "dark" : prefersDark;
    setIsDark(dark);
    document.documentElement.classList.toggle("dark", dark);
  }, []);

  function toggle() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("fittrack-theme", next ? "dark" : "light");
  }

  return { isDark, toggle };
}

function ThemeToggle() {
  const { isDark, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
        "text-surface-500 hover:bg-surface-100 hover:text-surface-700",
        "dark:text-surface-400 dark:hover:bg-surface-700 dark:hover:text-surface-200",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
      )}
    >
      {isDark ? (
        // Sun icon
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </svg>
      ) : (
        // Moon icon
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}

// ── Layout ────────────────────────────────────────────────────────────────────

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
      router.replace("/onboarding");
    }
  }, [isInitialized, user, needsOnboarding, router]);

  if (!isInitialized || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-50 dark:bg-surface-900">
        <LoadingSpinner size="lg" label="Loading your account…" />
      </div>
    );
  }

  if (!user || needsOnboarding) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface-50 dark:bg-surface-900">
      <header className="relative border-b border-surface-200 bg-white dark:border-surface-700 dark:bg-surface-800">
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
              <span className="font-semibold text-surface-900 dark:text-surface-50">
                FitTrack AI
              </span>
            </Link>
            <NavLinks />
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden text-sm text-surface-500 dark:text-surface-400 sm:block">
              {user.profile?.display_name ?? user.email}
            </span>
            <ThemeToggle />
            <div className="hidden sm:block">
              <SignOutButton />
            </div>
            <MobileMenu displayName={user.profile?.display_name ?? user.email} />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>

      <footer className="border-t border-surface-200 dark:border-surface-700">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-1 px-4 py-5 text-sm text-surface-500 dark:text-surface-400 sm:flex-row">
          <p>&copy; {new Date().getFullYear()} FitTrack AI</p>
          <p>Your personal fitness companion.</p>
        </div>
      </footer>
    </div>
  );
}

// ── Nav links ─────────────────────────────────────────────────────────────────

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/goals", label: "Goals" },
  { href: "/dashboard/weight", label: "Weight" },
  { href: "/dashboard/templates", label: "Templates" },
  { href: "/dashboard/workouts", label: "Workouts" },
  { href: "/dashboard/nutrition", label: "Nutrition" },
  { href: "/dashboard/measurements", label: "Measurements" },
  { href: "/dashboard/wellness", label: "Wellness" },
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
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
                    : "text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-700 dark:hover:text-surface-100"
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

// ── Sign-out ──────────────────────────────────────────────────────────────────

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
      className={cn(
        "rounded-lg px-3 py-1.5 text-sm transition-colors",
        "text-surface-600 hover:bg-surface-100",
        "dark:text-surface-400 dark:hover:bg-surface-700",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
      )}
    >
      Sign out
    </button>
  );
}

// ── Mobile menu (hamburger) ─────────────────────────────────────────────────────

function MobileMenu({ displayName }: { displayName: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);

  // Close the menu whenever the route changes.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Close on Escape for keyboard users.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function handleSignOut() {
    await logout();
    router.push("/");
    router.refresh();
  }

  const linkClass = (active: boolean) =>
    cn(
      "block rounded-lg px-3 py-2.5 text-base font-medium transition-colors",
      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
      active
        ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
        : "text-surface-700 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-300 dark:hover:bg-surface-700 dark:hover:text-surface-50",
    );

  return (
    <div className="sm:hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls="mobile-menu"
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
          "text-surface-600 hover:bg-surface-100 hover:text-surface-900",
          "dark:text-surface-300 dark:hover:bg-surface-700 dark:hover:text-surface-50",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
          aria-hidden="true"
        >
          {open ? (
            <path d="M18 6 6 18M6 6l12 12" />
          ) : (
            <path d="M3 12h18M3 6h18M3 18h18" />
          )}
        </svg>
      </button>

      {open && (
        <>
          {/* Backdrop — tap anywhere outside the panel to close. */}
          <button
            type="button"
            tabIndex={-1}
            aria-hidden="true"
            onClick={() => setOpen(false)}
            className="fixed inset-x-0 bottom-0 top-[57px] z-30 cursor-default bg-surface-900/20 dark:bg-black/50"
          />
          {/* Dropdown panel — positioned below the header. */}
          <div
            id="mobile-menu"
            className="absolute inset-x-0 top-full z-40 border-b border-surface-200 bg-white shadow-lg dark:border-surface-700 dark:bg-surface-800"
          >
            <nav
              aria-label="Mobile navigation"
              className="mx-auto max-w-7xl px-4 py-3"
            >
              <ul className="flex flex-col gap-1">
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
                        className={linkClass(active)}
                      >
                        {label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-3 border-t border-surface-200 pt-3 dark:border-surface-700">
                <p className="px-3 pb-1 text-sm text-surface-500 dark:text-surface-400">
                  {displayName}
                </p>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className={cn(
                    "block w-full rounded-lg px-3 py-2.5 text-left text-base font-medium transition-colors",
                    "text-surface-700 hover:bg-surface-100 hover:text-surface-900",
                    "dark:text-surface-300 dark:hover:bg-surface-700 dark:hover:text-surface-50",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
                  )}
                >
                  Sign out
                </button>
              </div>
            </nav>
          </div>
        </>
      )}
    </div>
  );
}
