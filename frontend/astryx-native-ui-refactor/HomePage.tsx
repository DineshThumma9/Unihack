import { useEffect } from "react";
import { VStack } from "@astryxdesign/core";
import { useJobStore } from "./stores/job.store";
import { useJobEvents } from "./hooks/useJobEvents";
import { getJob, listProducts } from "./api/jobs";

import { CsvUploader } from "./components/CsvUploader";
import { JobProgress } from "./components/JobProgress";
import { JobSummary } from "./components/JobSummary";
import { ProductTable } from "./components/ProductTable";
import { ProductDetailsModal } from "./components/ProductDetailsModal";

export function HomePage() {
  const { jobId, status, setJob, setProductsList } = useJobStore();

  useJobEvents(jobId);

  useEffect(() => {
    if (!jobId) return;

    getJob(jobId)
      .then((job) => setJob(job))
      .catch((err) => console.warn("Could not fetch job status", err));

    listProducts(jobId)
      .then((products) => {
        if (products && products.length > 0) {
          setProductsList(products);
        }
      })
      .catch((err) => console.warn("Could not fetch products list", err));
  }, [jobId, setJob, setProductsList]);

  const isIdle = !status;
  const isProcessing = status === "running" || status === "queued";

  return (
    <VStack gap={6} hAlign="stretch" width="100%" maxWidth="1000px">
      {isIdle && <CsvUploader />}
      {isProcessing && <JobProgress />}
      {!isIdle && !isProcessing && <JobSummary />}

      <ProductTable />
      <ProductDetailsModal />
    </VStack>
  );
}

export default HomePage;
