import { useEffect, useState } from "react";
import {
  Dialog,
  DialogHeader,
  Layout,
  LayoutContent,
  Card,
  VStack,
  HStack,
  Text,
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
      <Layout
        header={
          <DialogHeader
            title={`Product #${selectedProductIndex + 1}`}
            onOpenChange={(isOpen) => {
              if (!isOpen) selectProduct(null);
            }}
          />
        }
        content={
          <LayoutContent>
            <VStack gap={4} width="100%" padding={4}>
              {productData && (
                <HStack align="center" justify="start">
                  <Badge variant={statusVariant} label={productData.status.toUpperCase()} />
                </HStack>
              )}

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
                      <VStack key={key} gap={1} hAlign="stretch">
                        <Text type="code" color="secondary">{key}</Text>
                        <Text type="supporting" weight="semibold" style={{ wordBreak: "break-word" }}>
                          {String(value)}
                        </Text>
                      </VStack>
                    ))}
                </VStack>
              </Card>
            )}
          </VStack>
        ) : null}
      </VStack>
    </LayoutContent>
  }
      />
    </Dialog>
  );
}
