/**
 * Input component — accessible, supports unit labels and error states.
 *
 * Usage:
 *   <Input label="Email" type="email" error={errors.email?.message} />
 *   <Input label="Weight" type="number" unit="kg" />
 */

import type { InputHTMLAttributes } from "react";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
  /** Unit displayed as a right-side adornment (e.g. "kg", "ml") */
  unit?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, unit, id: idProp, className, ...props }, ref) => {
    // Generate an id from the label when none is provided.
    const id = idProp ?? label.toLowerCase().replace(/\s+/g, "-");
    const errorId = `${id}-error`;
    const hintId = `${id}-hint`;

    const describedBy = [
      error ? errorId : undefined,
      hint ? hintId : undefined,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div className="space-y-1">
        <label
          htmlFor={id}
          className="block text-sm font-medium text-surface-700"
        >
          {label}
          {props.required && (
            <span className="ml-1 text-red-500" aria-hidden="true">
              *
            </span>
          )}
        </label>

        <div className="relative">
          <input
            id={id}
            ref={ref}
            aria-describedby={describedBy || undefined}
            aria-invalid={error ? true : undefined}
            className={cn(
              "block w-full min-h-touch rounded-lg border bg-white px-3 py-2.5 text-sm",
              "text-surface-900 placeholder:text-surface-400",
              "transition-colors duration-150",
              "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500",
              error
                ? "border-red-500 focus:ring-red-500 focus:border-red-500"
                : "border-surface-200 hover:border-surface-300",
              unit && "pr-14",
              "disabled:cursor-not-allowed disabled:bg-surface-100 disabled:text-surface-500",
              className
            )}
            {...props}
          />
          {unit && (
            <div
              className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
              aria-hidden="true"
            >
              <span className="text-sm text-surface-400">{unit}</span>
            </div>
          )}
        </div>

        {hint && !error && (
          <p id={hintId} className="text-xs text-surface-500">
            {hint}
          </p>
        )}
        {error && (
          <p id={errorId} role="alert" className="text-xs text-red-600">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
