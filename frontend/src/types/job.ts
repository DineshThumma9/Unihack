export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  filename: string;
  status: JobStatus;
  total: number;
  completed: number;
  successful: number;
  warnings: number;
  failed: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  output_path: string | null;
  error: string | null;
}

export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
  total: number;
}

export type ProductStatus = "success" | "warning" | "failed" | "processing" | "queued";

export interface ProductProgress extends Record<string, unknown> {
  index: number;
  mpn: string;
  status: ProductStatus;
  manufacturer?: string | null;
  brand?: string | null;
  attributes_found?: number;
  validation_passed?: boolean;
  failed_rules?: string[];
  processing_time?: number;
  error?: string | null;
}

export interface JobStartedEvent {
  type: "job.started";
  job_id: string;
  total: number;
}

export interface ProductStartedEvent {
  type: "product.started";
  index: number;
  mpn: string;
}

export interface ProductCompletedEvent {
  type: "product.completed";
  index: number;
  mpn: string;
  status: "success" | "warning";
  manufacturer?: string | null;
  brand?: string | null;
  attributes_found?: number;
  validation_passed?: boolean;
  failed_rules?: string[];
  processing_time?: number;
}

export interface ProductFailedEvent {
  type: "product.failed";
  index: number;
  mpn: string;
  error: string;
}

export interface JobCompletedEvent {
  type: "job.completed";
  job_id: string;
  total: number;
  processed: number;
  successful: number;
  warnings: number;
  failed: number;
  output_ready: boolean;
}

export interface JobFailedEvent {
  type: "job.failed";
  job_id: string;
  error: string;
}

export type JobEvent =
  | JobStartedEvent
  | ProductStartedEvent
  | ProductCompletedEvent
  | ProductFailedEvent
  | JobCompletedEvent
  | JobFailedEvent;
