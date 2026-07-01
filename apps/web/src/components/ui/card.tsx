/**
 * Card - minimal surface container for dashboard sections and form groups.
 */

import { cn } from "@/lib/utils";

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

interface CardHeaderProps {
  className?: string;
  children: React.ReactNode;
}

interface CardTitleProps {
  className?: string;
  children: React.ReactNode;
  as?: "h2" | "h3" | "h4";
}

interface CardBodyProps {
  className?: string;
  children: React.ReactNode;
}

export function Card({ className, children }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-surface-200 bg-white shadow-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children }: CardHeaderProps) {
  return (
    <div className={cn("border-b border-surface-100 px-5 py-4", className)}>
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
  as: Tag = "h2",
}: CardTitleProps) {
  return (
    <Tag className={cn("text-base font-semibold text-surface-900", className)}>
      {children}
    </Tag>
  );
}

export function CardBody({ className, children }: CardBodyProps) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}
