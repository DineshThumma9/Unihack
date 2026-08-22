import { useEffect, useState } from "react";
import {
  Dialog,
  Card,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Badge,
  Skeleton,
} from "@astryxdesign/core";
import { useJobStore } from "../stores/job.store";
import { getProduct } from "../api/jobs";
import type { ProductRunResult } from "../types/product";

export function ProductDetailsModal() {
  const { jobId, selectedProductIndex, selectProduct } = useJobStore();
  const [productData, setProductData] = useState<ProductRunResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (jobId === null || selectedProductIndex === null) {
      setProductData(null);
      return;
    }

    setLoading(true);
    getProduct(jobId, selectedProductIndex)
      .then(setProductData)
      .catch((err) => console.error("Failed to fetch product details", err))
      .finally(() => setLoading(false));
  }, [jobId, selectedProductIndex]);

  if (selectedProductIndex === null) return null;

  const statusVariant =
    productData?.status === "success"
      ? "success"
      : productData?.status === "warning"
        ? "warning"
        : "error";

  return (
    <Dialog
      isOpen
      onOpenChange={(isOpen) => {
        if (!isOpen) selectProduct(null);
      }}
      width={680}
    >
      <VStack gap={4} width="100%">
        <HStack justify="between" align="center" width="100%">
          <HStack gap={3} align="center">
            <Heading level={2}>Product #{selectedProductIndex + 1}</Heading>
            {productData && (
              <Badge variant={statusVariant} label={productData.status.toUpperCase()} />
            )}
          </HStack>
          <Button
            label="Close"
            variant="secondary"
            size="sm"
            onClick={() => selectProduct(null)}
          />
        </HStack>

        {loading ? (
          <VStack gap={2} width="100%">
            <Skeleton width="100%" height={20} />
            <Skeleton width="80%" height={20} />
          </VStack>
        ) : productData ? (
          <VStack gap={3} width="100%">
            <Card variant="muted" padding={3} width="100%">
              <VStack gap={2}>
                <Text type="body" weight="semibold">Identity</Text>
                <VStack gap={1} hAlign="stretch">
                  <Text type="supporting">
                    MPN: <Text as="span" weight="semibold">{productData.mpn}</Text>
                  </Text>
                  <Text type="supporting">
                    Manufacturer: <Text as="span" weight="semibold">{productData.manufacturer || "-"}</Text>
                  </Text>
                  <Text type="supporting">
                    Brand: <Text as="span" weight="semibold">{productData.brand || "-"}</Text>
                  </Text>
                </VStack>
              </VStack>
            </Card>

            <Card variant="muted" padding={3} width="100%">
              <VStack gap={2}>
                <Text type="body" weight="semibold">Validation & Execution</Text>
                <VStack gap={1} hAlign="stretch">
                  <Text type="supporting">Status: {productData.status}</Text>
                  <Text type="supporting">Score: {productData.validation_score.toFixed(0)}%</Text>
                  <Text type="supporting">Time: {productData.processing_time.toFixed(2)}s</Text>
                </VStack>
                <VStack gap={1} hAlign="stretch">
                  {Object.entries(productData.validation).map(([rule, passed]) => (
                    <HStack key={rule} justify="between" align="center">
                      <Text type="supporting" weight="semibold">{rule}</Text>
                      <Badge variant={passed ? "success" : "error"} label={passed ? "Passed" : "Failed"} />
                    </HStack>
                  ))}
                </VStack>
              </VStack>
            </Card>

            {productData.delivery_row && (
              <Card variant="muted" padding={3} width="100%">
                <VStack gap={2} hAlign="stretch">
                  <Text type="body" weight="semibold">Enriched Delivery Fields</Text>
                  {Object.entries(productData.delivery_row)
                    .filter(([, value]) => value !== null && value !== "" && value !== undefined)
                    .map(([key, value]) => (
                      <HStack key={key} justify="between" align="start">
                        <Text type="code" color="secondary">{key}</Text>
                        <Text type="supporting" weight="semibold">{String(value)}</Text>
                      </HStack>
                    ))}
                </VStack>
              </Card>
            )}
          </VStack>
        ) : null}
      </VStack>
    </Dialog>
  );
}
