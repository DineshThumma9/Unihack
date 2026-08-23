import { useState } from "react";
import { Card, VStack, HStack, Heading, Text, Button, Badge } from "@astryxdesign/core";
import { CheckCircle2, Download, RotateCcw, AlertOctagon } from "lucide-react";
import { useJobStore } from "../stores/job.store";
import { downloadCsv } from "../api/jobs";

export function JobSummary() {
  const { jobId, filename, status, total, successful, warnings, failed, error, products, reset } = useJobStore();
  const [downloadingType, setDownloadingType] = useState<string | null>(null);

  const isComplete = status === "completed";
  const isStopped = status === "cancelled" || status === "failed";

  if (!isComplete && !isStopped) return null;

  const handleDownload = async (type?: "warning" | "failed") => {
    if (!jobId || !filename) return;
    setDownloadingType(type || "main");
    try {
      await downloadCsv(jobId, filename, type);
    } catch (err) {
      console.error("Download failed", err);
    } finally {
      setDownloadingType(null);
    }
  };

  const productList = Object.values(products);
  const warnedProducts = productList.filter((p) => p.status === "warning");
  const failedProducts = productList.filter((p) => p.status === "failed");

  // Aggregate warning reasons
  const warningReasons: Record<string, number> = {};
  warnedProducts.forEach((p) => {
    if (p.failed_rules && p.failed_rules.length > 0) {
      p.failed_rules.forEach((rule) => {
        warningReasons[rule] = (warningReasons[rule] || 0) + 1;
      });
    } else {
      warningReasons["Unknown validation failure"] = (warningReasons["Unknown validation failure"] || 0) + 1;
    }
  });

  // Aggregate failure reasons
  const failureReasons: Record<string, number> = {};
  failedProducts.forEach((p) => {
    const err = p.error || "Unknown Error";
    failureReasons[err] = (failureReasons[err] || 0) + 1;
  });

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
                label={downloadingType === "main" ? "Downloading..." : "Download Enriched CSV"}
                onClick={() => handleDownload()}
                isDisabled={downloadingType !== null}
                variant="primary"
                size="md"
                icon={<Download />}
              />
              {warnings > 0 && (
                <Button
                  label={downloadingType === "warning" ? "Downloading..." : "Download Warnings"}
                  onClick={() => handleDownload("warning")}
                  isDisabled={downloadingType !== null}
                  variant="secondary"
                  size="md"
                  icon={<Download />}
                />
              )}
              {failed > 0 && (
                <Button
                  label={downloadingType === "failed" ? "Downloading..." : "Download Failed"}
                  onClick={() => handleDownload("failed")}
                  isDisabled={downloadingType !== null}
                  variant="secondary"
                  size="md"
                  icon={<Download />}
                />
              )}
              <Button
                label="Upload New File"
                onClick={reset}
                variant="secondary"
                size="md"
                icon={<RotateCcw />}
              />
            </HStack>

            {/* Error & Warning Breakdowns */}
            {(warnings > 0 || failed > 0) && (
              <VStack gap={4} width="100%" hAlign="stretch" style={{ marginTop: 16 }}>
                {warnings > 0 && (
                  <Card variant="muted" padding={4} width="100%">
                    <VStack gap={3} hAlign="stretch">
                      <Heading level={4} style={{ color: "var(--astryx-warning, #eab308)" }}>Warning Breakdown</Heading>
                      {Object.entries(warningReasons).sort((a, b) => b[1] - a[1]).map(([reason, count]) => (
                        <HStack key={reason} justify="between" align="center" style={{ borderBottom: "1px solid var(--astryx-border-muted, #333)", paddingBottom: 8 }}>
                          <Text type="code" color="secondary" style={{ fontSize: "0.85rem" }}>{reason}</Text>
                          <Badge label={`${count} products`} variant="warning" />
                        </HStack>
                      ))}
                    </VStack>
                  </Card>
                )}
                
                {failed > 0 && (
                  <Card variant="muted" padding={4} width="100%">
                    <VStack gap={3} hAlign="stretch">
                      <Heading level={4} style={{ color: "var(--astryx-danger, #ef4444)" }}>Failure Breakdown</Heading>
                      {Object.entries(failureReasons).sort((a, b) => b[1] - a[1]).map(([reason, count]) => (
                        <HStack key={reason} justify="between" align="center" style={{ borderBottom: "1px solid var(--astryx-border-muted, #333)", paddingBottom: 8 }}>
                          <Text color="secondary" style={{ fontSize: "0.85rem", maxWidth: "80%", wordBreak: "break-all" }}>{reason}</Text>
                          <Badge label={`${count} products`} variant="error" />
                        </HStack>
                      ))}
                    </VStack>
                  </Card>
                )}
              </VStack>
            )}
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
