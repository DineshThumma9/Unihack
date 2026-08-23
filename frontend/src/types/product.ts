export interface ProductRunResult {
  index: number;
  mpn: string;
  status: "success" | "warning" | "failed";
  validation: Record<string, boolean>;
  validation_score: number;
  manufacturer: string | null;
  brand: string | null;
  attributes_found: number;
  processing_time: number;
  needs_review: boolean;
  error: string | null;
  delivery_row: Record<string, any> | null;
  source_map?: Record<string, "Regex" | "LLM">;
}
