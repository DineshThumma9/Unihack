import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Job, JobEvent, JobStatus, ProductProgress } from "../types/job";
import type { ProductRunResult } from "../types/product";

interface JobState {
  jobId: string | null;
  filename: string | null;
  status: JobStatus | null;

  total: number;
  completed: number;
  successful: number;
  warnings: number;
  failed: number;

  currentProduct: ProductProgress | null;
  products: Record<number, ProductProgress>;
  selectedProductIndex: number | null;
  error: string | null;

  setJob: (job: Job) => void;
  setJobId: (jobId: string) => void;
  setProductsList: (productsList: ProductRunResult[]) => void;
  handleEvent: (event: JobEvent) => void;
  selectProduct: (index: number | null) => void;
  reset: () => void;
}

export const useJobStore = create<JobState>()(
  persist(
    (set, get) => ({
      jobId: null,
      filename: null,
      status: null,

      total: 0,
      completed: 0,
      successful: 0,
      warnings: 0,
      failed: 0,

      currentProduct: null,
      products: {},
      selectedProductIndex: null,
      error: null,

      setJob: (job: Job) => {
        set({
          jobId: job.id,
          filename: job.filename,
          status: job.status,
          total: job.total,
          completed: job.completed,
          successful: job.successful,
          warnings: job.warnings,
          failed: job.failed,
          error: job.error,
        });
      },

      setJobId: (jobId: string) => {
        set({ jobId });
      },

      setProductsList: (productsList: ProductRunResult[]) => {
        const prodMap: Record<number, ProductProgress> = {};
        for (const p of productsList) {
          prodMap[p.index] = {
            index: p.index,
            mpn: p.mpn,
            status: p.status,
            manufacturer: p.manufacturer,
            brand: p.brand,
            attributes_found: p.attributes_found,
            validation_passed: !p.needs_review,
            processing_time: p.processing_time,
            error: p.error,
          };
        }
        set((state) => ({
          products: {
            ...state.products,
            ...prodMap,
          },
        }));
      },

      handleEvent: (event: JobEvent) => {
        const state = get();
        switch (event.type) {
          case "job.started":
            set({
              status: "running",
              total: event.total,
            });
            break;

          case "product.started": {
            const prog: ProductProgress = {
              index: event.index,
              mpn: event.mpn,
              status: "processing",
            };
            set({
              currentProduct: prog,
              products: {
                ...state.products,
                [event.index]: prog,
              },
            });
            break;
          }

          case "product.completed": {
            const prog: ProductProgress = {
              index: event.index,
              mpn: event.mpn,
              status: event.status,
              manufacturer: event.manufacturer,
              brand: event.brand,
              attributes_found: event.attributes_found,
              validation_passed: event.validation_passed,
              failed_rules: event.failed_rules,
              processing_time: event.processing_time,
            };

            const isWarning = event.status === "warning";
            const newSuccessful = isWarning ? state.successful : state.successful + 1;
            const newWarnings = isWarning ? state.warnings + 1 : state.warnings;
            const newCompleted = state.completed + 1;

            set({
              completed: newCompleted,
              successful: newSuccessful,
              warnings: newWarnings,
              products: {
                ...state.products,
                [event.index]: prog,
              },
            });
            break;
          }

          case "product.failed": {
            const prog: ProductProgress = {
              index: event.index,
              mpn: event.mpn,
              status: "failed",
              error: event.error,
            };

            set({
              completed: state.completed + 1,
              failed: state.failed + 1,
              products: {
                ...state.products,
                [event.index]: prog,
              },
            });
            break;
          }

          case "job.completed":
            set({
              status: "completed",
              total: event.total,
              completed: event.processed,
              successful: event.successful,
              warnings: event.warnings,
              failed: event.failed,
              currentProduct: null,
            });
            break;

          case "job.failed":
            set({
              status: "failed",
              error: event.error,
              currentProduct: null,
            });
            break;
        }
      },

      selectProduct: (index: number | null) => {
        set({ selectedProductIndex: index });
      },

      reset: () => {
        set({
          jobId: null,
          filename: null,
          status: null,
          total: 0,
          completed: 0,
          successful: 0,
          warnings: 0,
          failed: 0,
          currentProduct: null,
          products: {},
          selectedProductIndex: null,
          error: null,
        });
      },
    }),
    {
      name: "enrichment-job-storage",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        jobId: state.jobId,
        selectedProductIndex: state.selectedProductIndex,
      }),
    }
  )
);
