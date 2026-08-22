import { useState } from "react";
import {
  ProgressBar,
  Card,
  HStack,
  VStack,
  Text,
  Heading,
  Button,
  Badge,
} from "@astryxdesign/core";
import { Loader2, CheckCircle2, AlertTriangle, XCircle, Square, RotateCcw } from "lucide-react";
import { useJobStore } from "../stores/job.store";
import { cancelJob } from "../api/jobs";

export function JobProgress() {
  const {
    jobId,
    filename,
    status,
    total,
    completed,
    successful,
    warnings,
    failed,
    currentProduct,
    reset,
  } = useJobStore();

  const [isCancelling, setIsCancelling] = useState(false);
  const isProcessing = status === "running" || status === "queued";

  const handleCancel = async () => {
    if (!jobId) return;
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
    } catch (err) {
      console.error("Failed to stop job", err);
    } finally {
      setIsCancelling(false);
    }
  };

  if (!isProcessing) return null;

  return (
    <Card padding={4} width="100%">
      <VStack gap={4} hAlign="stretch">
        <HStack align="center" justify="between">
          <HStack gap={3} align="center">
            <Loader2 />
            <VStack gap={0.5} hAlign="stretch">
              <HStack gap={2} align="center">
                <Heading level={3}>Enriching CSV Products</Heading>
                <Badge variant="neutral" label={status.toUpperCase()} />
              </HStack>
              <Text type="supporting">{filename}</Text>
            </VStack>
          </HStack>

          <HStack gap={2} align="center">
            <Button
              label={isCancelling ? "Stopping..." : "Stop Job"}
              onClick={handleCancel}
              isDisabled={isCancelling}
              variant="destructive"
              size="sm"
              icon={<Square />}
            />
            <Button
              label="New Job"
              onClick={reset}
              variant="secondary"
              size="sm"
              icon={<RotateCcw />}
            />
          </HStack>
        </HStack>

        <ProgressBar
          label={`Processed ${completed} / ${total || 1}`}
          value={completed}
          max={total || 1}
          hasValueLabel
          formatValueLabel={(value, max) =>
            `${value} / ${max} (${Math.round((value / max) * 100)}%)`
          }
        />

        {currentProduct && (
          <Card variant="muted" padding={3}>
            <VStack gap={1} hAlign="stretch">
              <Text type="supporting">Currently processing</Text>
              <Text type="code" weight="semibold">{currentProduct.mpn}</Text>
              {currentProduct.manufacturer && (
                <Text type="supporting">Manufacturer: {currentProduct.manufacturer}</Text>
              )}
            </VStack>
          </Card>
        )}

        <HStack gap={3} align="stretch">
          <Card variant="green" padding={3}>
            <HStack gap={2} align="center">
              <CheckCircle2 />
              <Text weight="semibold">{successful}</Text>
              <Text type="supporting">successful</Text>
            </HStack>
          </Card>
          <Card variant="orange" padding={3}>
            <HStack gap={2} align="center">
              <AlertTriangle />
              <Text weight="semibold">{warnings}</Text>
              <Text type="supporting">warnings</Text>
            </HStack>
          </Card>
          <Card variant="red" padding={3}>
            <HStack gap={2} align="center">
              <XCircle />
              <Text weight="semibold">{failed}</Text>
              <Text type="supporting">failed</Text>
            </HStack>
          </Card>
        </HStack>
      </VStack>
    </Card>
  );
}
