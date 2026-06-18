/**
 * Workouts API — typed wrappers around the FitTrack FastAPI workout endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from "@/lib/api-client";
import type {
  AddExercisePayload,
  CompleteWorkoutPayload,
  CreateTemplatePayload,
  LogSetPayload,
  StartWorkoutPayload,
  TemplateListResponse,
  UpdateTemplatePayload,
  Workout,
  WorkoutListResponse,
  WorkoutSet,
  WorkoutTemplate,
} from "@/types/workouts";

// ── Templates ──────────────────────────────────────────────────────────────────

export const templatesApi = {
  list(params: { page?: number; page_size?: number } = {}): Promise<TemplateListResponse> {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return apiClient.get<TemplateListResponse>(
      `/api/v1/templates${query ? `?${query}` : ""}`
    );
  },

  get(id: string): Promise<WorkoutTemplate> {
    return apiClient.get<WorkoutTemplate>(`/api/v1/templates/${id}`);
  },

  create(body: CreateTemplatePayload): Promise<WorkoutTemplate> {
    return apiClient.post<WorkoutTemplate>("/api/v1/templates", body);
  },

  update(id: string, body: UpdateTemplatePayload): Promise<WorkoutTemplate> {
    return apiClient.patch<WorkoutTemplate>(`/api/v1/templates/${id}`, body);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/templates/${id}`);
  },
};

// ── Workouts ───────────────────────────────────────────────────────────────────

export interface ListWorkoutsParams {
  page?: number;
  page_size?: number;
  status?: "in_progress" | "completed";
}

export const workoutsApi = {
  list(params: ListWorkoutsParams = {}): Promise<WorkoutListResponse> {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.status) qs.set("status", params.status);
    const query = qs.toString();
    return apiClient.get<WorkoutListResponse>(
      `/api/v1/workouts${query ? `?${query}` : ""}`
    );
  },

  get(id: string): Promise<Workout> {
    return apiClient.get<Workout>(`/api/v1/workouts/${id}`);
  },

  start(body: StartWorkoutPayload): Promise<Workout> {
    return apiClient.post<Workout>("/api/v1/workouts", body);
  },

  complete(id: string, body: CompleteWorkoutPayload = {}): Promise<Workout> {
    return apiClient.post<Workout>(`/api/v1/workouts/${id}/complete`, body);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/workouts/${id}`);
  },

  addExercise(workoutId: string, body: AddExercisePayload): Promise<Workout> {
    return apiClient.post<Workout>(
      `/api/v1/workouts/${workoutId}/exercises`,
      body
    );
  },

  removeExercise(workoutExerciseId: string): Promise<void> {
    return apiClient.delete<void>(
      `/api/v1/workouts/exercises/${workoutExerciseId}`
    );
  },

  logSet(workoutExerciseId: string, body: LogSetPayload): Promise<WorkoutSet> {
    return apiClient.post<WorkoutSet>(
      `/api/v1/workouts/exercises/${workoutExerciseId}/sets`,
      body
    );
  },

  deleteSet(setId: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/workouts/sets/${setId}`);
  },
};
