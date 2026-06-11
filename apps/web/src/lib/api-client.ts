/**
 * Minimal API client for communicating with the FitTrack FastAPI backend.
 *
 * Design principles:
 * - All requests go through a single fetch wrapper so error handling,
 *   authentication headers, and base URL are managed in one place.
 * - Credentials (cookies) are always included so HTTP-only auth cookies
 *   are sent automatically.
 * - Never expose auth tokens in JavaScript variables or localStorage.
 * - Structured error objects (ApiError) are thrown on non-2xx responses
 *   so callers can distinguish auth failures from validation errors.
 */

export interface ApiErrorDetail {
  field?: string;
  message: string;
  code?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly errorCode: string,
    message: string,
    public readonly details: ApiErrorDetail[] = []
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.statusCode === 401;
  }

  get isNotFound(): boolean {
    return this.statusCode === 404;
  }

  get isValidationError(): boolean {
    return this.statusCode === 422;
  }
}

const API_BASE =
  typeof window === "undefined"
    ? (process.env["INTERNAL_API_URL"] ?? "http://localhost:8000")
    : ""; // In the browser, Next.js rewrites /api/* to the backend.

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith("/api") ? `${API_BASE}${path}` : `${API_BASE}/api/v1${path}`;

  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(
      response.status,
      "PARSE_ERROR",
      `Unexpected response from server (status ${response.status})`
    );
  }

  if (!response.ok) {
    const err = body as {
      message?: string;
      error_code?: string;
      details?: ApiErrorDetail[];
    };
    throw new ApiError(
      response.status,
      err.error_code ?? "API_ERROR",
      err.message ?? "An error occurred",
      err.details ?? []
    );
  }

  return (body as { data?: T }).data ?? (body as T);
}

export const apiClient = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
