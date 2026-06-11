/**
 * Re-export useAuth for cleaner import paths.
 *
 * Usage:
 *   import { useAuth } from "@/features/auth/use-auth";
 *   const { user, login, logout } = useAuth();
 */
export { useAuth } from "./auth-context";
