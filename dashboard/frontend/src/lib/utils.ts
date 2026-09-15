import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRiskScore(score: number | null | undefined): string {
  if (score === null || score === undefined || isNaN(score)) {
    return "N/A";
  }
  return (score * 100).toFixed(1) + "%";
}

export function getRiskColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-slate-500";
  if (score >= 0.5) return "text-amber-600";
  return "text-teal-600";
}
