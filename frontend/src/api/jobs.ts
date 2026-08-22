import { api } from "./axios";
import type { CreateJobResponse, Job } from "../types/job";
import type { ProductRunResult } from "../types/product";

export async function createJob(file: File): Promise<CreateJobResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<CreateJobResponse>("/api/jobs", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await api.get<Job>(`/api/jobs/${jobId}`);
  return response.data;
}

export async function cancelJob(jobId: string): Promise<void> {
  await api.post(`/api/jobs/${jobId}/cancel`);
}

export async function listProducts(jobId: string): Promise<ProductRunResult[]> {
  const response = await api.get<ProductRunResult[]>(`/api/jobs/${jobId}/products`);
  return response.data;
}

export async function getProduct(jobId: string, index: number): Promise<ProductRunResult> {
  const response = await api.get<ProductRunResult>(`/api/jobs/${jobId}/products/${index}`);
  return response.data;
}

export function getDownloadUrl(jobId: string): string {
  const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";
  return `${baseURL}/api/jobs/${jobId}/download`;
}

export async function downloadCsv(jobId: string, filename: string): Promise<void> {
  const response = await api.get(`/api/jobs/${jobId}/download`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `enriched_${filename}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
