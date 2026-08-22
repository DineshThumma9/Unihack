import { useState } from "react";
import { Card, VStack, HStack, Heading, Text, Button } from "@astryxdesign/core";
import { CheckCircle2, Download, RotateCcw, AlertOctagon } from "lucide-react";
import { useJobStore } from "../stores/job.store";
import { downloadCsv } from "../api/jobs";

export function JobSummary() {
  const { jobId, filename, status, total, successful, warnings, failed, error, reset } = useJobStore();
  const [isDownloading, setIsDownloading] = useState(false);

  const isComplete = status === "completed";
  const isStopped = status === "cancelled" || status === "failed";

  if (!isComplete && !isStopped) return null;

  const handleDownload = async () => {
    if (!jobId || !filename) return;
    setIsDownloading(true);
    try {
      await downloadCsv(jobId, filename);
    } catch (err) {
      console.error("Download failed", err);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Card padding={4} width="100%">
      <VStack gap={4} hAlign="center">
        {isComplete ? (
          <>
            <CheckCircle2 />
            <VStack gap={1} hAlign="center">
              <Heading level={2}>Enrichment Complete</Heading>
              <Text type="supporting" justify="center">
                {total} products processed: {successful} successful, {warnings} warnings, {failed} failed.
              </Text>
            </VStack>

            <HStack gap={3} align="center">
              <Button
                label={isDownloading ? "Downloading..." : "Download Enriched CSV"}
                onClick={handleDownload}
                isDisabled={isDownloading}
                variant="primary"
                size="md"
                icon={<Download />}
              />
              <Button
                label="Upload New File"
                onClick={reset}
                variant="secondary"
                size="md"
                icon={<RotateCcw />}
              />
            </HStack>
          </>
        ) : (
          <>
            <AlertOctagon />
            <VStack gap={1} hAlign="center">
              <Heading level={2}>Job Stopped</Heading>
              <Text type="supporting" justify="center">
                {error || "The job did not complete."}
              </Text>
            </VStack>
            <Button
              label="Upload New File"
              onClick={reset}
              variant="secondary"
              size="md"
              icon={<RotateCcw />}
            />
          </>
        )}
      </VStack>
    </Card>
  );
}
