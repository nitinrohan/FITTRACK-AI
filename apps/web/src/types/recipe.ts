/**
 * TypeScript types for the FitTrack AI recipes domain.
 *
 * Mirrors the Pydantic schemas in apps/api/app/schemas/recipe.py
 */

import type { FoodLogEntry, MacroTotals, MealType } from "@/types/nutrition";

export interface RecipeItem {
  food_id: string;
  food_name: string;
  food_brand: string | null;
  quantity_g: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
}

export interface Recipe {
  id: string;
  name: string;
  description: string | null;
  items: RecipeItem[];
  totals: MacroTotals;
  created_at: string;
  updated_at: string;
}

export interface RecipeListResponse {
  recipes: Recipe[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecipeItemInput {
  food_id: string;
  quantity_g: number;
}

export interface CreateRecipePayload {
  name: string;
  description?: string;
  items: RecipeItemInput[];
}

export interface UpdateRecipePayload {
  name?: string;
  description?: string;
  items?: RecipeItemInput[];
}

export interface LogRecipePayload {
  logged_date: string; // YYYY-MM-DD
  meal_type?: MealType;
  scale_factor?: number; // 1.0 = log exactly as saved
}

export interface LogRecipeResult {
  entries: FoodLogEntry[];
  totals: MacroTotals;
}
