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
  Table,
  proportional,
  pixel,
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

  const attributes: { id: string; name: string; value: string; uom: string }[] = [];
  const features: { id: string; feature: string }[] = [];

  if (productData?.delivery_row) {
    for (let i = 1; i <= 50; i++) {
      const label = productData.delivery_row[`ATTRIBUTE_LABEL ${i}`];
      const value = productData.delivery_row[`ATTRIBUTE_VALUE ${i}`];
      const uom = productData.delivery_row[`ATTRIBUTE_UOM ${i}`];
      if (label || value || uom) {
        attributes.push({
          id: `attr-${i}`,
          name: label || "-",
          value: String(value || "-"),
          uom: uom || "-",
        });
      }
    }

    for (let i = 1; i <= 20; i++) {
      const feat = productData.delivery_row[`ITEM_FEATURES_${i}`];
      if (feat) {
        features.push({
          id: `feat-${i}`,
          feature: String(feat),
        });
      }
    }
  }

  const attrColumns: any[] = [
    { key: "name", header: "Name", width: proportional(2) },
    { key: "value", header: "Value", width: proportional(3) },
    { key: "uom", header: "UOM", width: pixel(100) },
  ];

  const featureColumns: any[] = [
    { key: "feature", header: "Feature", width: proportional(1) },
  ];

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
                
                {productData.error && (
                  <Card padding={3} style={{ backgroundColor: "var(--astryx-bg-error-subtle, #fee2e2)" }}>
                    <VStack gap={1} hAlign="stretch">
                      <Text type="body" weight="semibold" style={{ color: "var(--astryx-bg-error-strong, red)" }}>Pipeline Error</Text>
                      <Text type="code" style={{ color: "var(--astryx-bg-error-strong, red)", wordBreak: "break-word", whiteSpace: "pre-wrap" }}>
                        {productData.error}
                      </Text>
                    </VStack>
                  </Card>
                )}

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

            {attributes.length > 0 && (
              <Card variant="muted" padding={3} width="100%">
                <VStack gap={3} hAlign="stretch">
                  <Text type="body" weight="semibold">Attributes</Text>
                  <Card width="100%">
                    <Table data={attributes} columns={attrColumns} idKey="id" density="compact" />
                  </Card>
                </VStack>
              </Card>
            )}

            {features.length > 0 && (
              <Card variant="muted" padding={3} width="100%">
                <VStack gap={3} hAlign="stretch">
                  <Text type="body" weight="semibold">Features</Text>
                  <Card width="100%">
                    <Table data={features} columns={featureColumns} idKey="id" density="compact" />
                  </Card>
                </VStack>
              </Card>
            )}

            {productData.delivery_row && (
              <Card variant="muted" padding={3} width="100%">
                <VStack gap={2} hAlign="stretch">
                  <Text type="body" weight="semibold">Enriched Delivery Fields (Raw)</Text>
                  {Object.entries(productData.delivery_row)
                    .filter(([key, value]) => {
                      if (value === null || value === "" || value === undefined) return false;
                      if (key.startsWith("ATTRIBUTE_") || key.startsWith("ITEM_FEATURES_")) return false;
                      return true;
                    })
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
