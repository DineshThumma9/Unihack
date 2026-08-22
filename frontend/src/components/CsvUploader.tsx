import { useState } from "react";
import { FileInput, Card, VStack, HStack, Heading, Text, Button } from "@astryxdesign/core";
import { UploadCloud, FileText, ArrowRight, X } from "lucide-react";
import { createJob } from "../api/jobs";
import { useJobStore } from "../stores/job.store";

export function CsvUploader() {
  const { setJobId, setJob } = useJobStore();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (files: File | File[] | null) => {
    if (!files) {
      setFile(null);
      return;
    }

    const selected = Array.isArray(files) ? files[0] : files;
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    setFile(selected);
    setError(null);
  };

  const handleStart = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const res = await createJob(file);
      setJobId(res.job_id);
      setJob({
        id: res.job_id,
        filename: file.name,
        status: res.status,
        total: res.total,
        completed: 0,
        successful: 0,
        warnings: 0,
        failed: 0,
        created_at: new Date().toISOString(),
        started_at: null,
        completed_at: null,
        output_path: null,
        error: null,
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not start the job.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setError(null);
  };

  return (
    <Card padding={4} width="100%">
      <VStack gap={4} hAlign="stretch">
        <VStack gap={1} hAlign="center">
          <UploadCloud />
          <Heading level={2}>Upload CSV Dataset</Heading>
          <Text type="supporting" justify="center">
            Enrich product catalog items with search, LLM enrichment, and validation.
          </Text>
        </VStack>

        {!file ? (
          <FileInput
            label="CSV File Upload"
            isLabelHidden
            value={file}
            onChange={handleFileChange}
            accept=".csv"
            mode="dropzone"
            width="100%"
            description="Choose a CSV file or drag it here."
            status={error ? { type: "error", message: error } : undefined}
          />
        ) : (
          <Card variant="muted" padding={3}>
            <HStack align="center" justify="between">
              <HStack gap={3} align="center">
                <FileText />
                <VStack gap={0.5} hAlign="stretch">
                  <Text type="body" weight="medium">{file.name}</Text>
                  <Text type="supporting">{(file.size / 1024).toFixed(1)} KB</Text>
                </VStack>
              </HStack>

              <HStack gap={2} align="center">
                <Button
                  label={isUploading ? "Starting..." : "Start Enrichment"}
                  onClick={handleStart}
                  isDisabled={isUploading}
                  variant="primary"
                  size="sm"
                  endContent={<ArrowRight />}
                />
                <Button
                  label="Clear file"
                  onClick={handleClear}
                  variant="ghost"
                  size="sm"
                  isIconOnly
                  icon={<X />}
                />
              </HStack>
            </HStack>
          </Card>
        )}

        {error && <Text type="supporting">{error}</Text>}
      </VStack>
    </Card>
  );
}
