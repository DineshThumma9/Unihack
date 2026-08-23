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
  Heading,
  Badge,
  Skeleton,
  Table,
  proportional,
} from "@astryxdesign/core";
import { useJobStore } from "../stores/job.store";
import { getProduct } from "../api/jobs";
import type { ProductRunResult } from "../types/product";

function formatKeyName(key: string): string {
  if (key.includes(" ") && !key.includes("_")) return key;
  return key
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

const SourceBadge = ({ source }: { source?: "Regex" | "LLM" | string }) => {
  if (!source) return null;
  if (source === "Regex") {
    return <Badge variant="success" label="Verified" />;
  }
  return <Badge variant="info" label="Inferred" />;
};

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

  const attributes: { id: string; name: string; value: string; uom: string; source?: string }[] = [];
  const features: { id: string; feature: string }[] = [];

  const rawFields: { id: string; key: string; value: string; source?: string }[] = [];
  const descriptions: { key: string; value: string }[] = [];
  const urls: { key: string; value: string }[] = [];
  const commerce: { id: string; key: string; value: string }[] = [];
  const dimensions: { id: string; key: string; value: string; uom: string; source?: string }[] = [];

  const sourceMap = productData?.source_map || {};

  if (productData?.delivery_row) {
    for (let i = 1; i <= 50; i++) {
      const label = productData.delivery_row[`ATTRIBUTE_LABEL ${i}`];
      const value = productData.delivery_row[`ATTRIBUTE_VALUE ${i}`];
      const uom = productData.delivery_row[`ATTRIBUTE_UOM ${i}`];
      if (label || value || uom) {
        attributes.push({
          id: `attr-${i}`,
          name: String(label || "-"),
          value: String(value || "-"),
          uom: String(uom || "-"),
          source: sourceMap[`ATTRIBUTE_VALUE ${i}`],
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

    const commerceKeys = ["Selling Qty", "Selling UOM", "Package Qty", "UPC", "EAN", "GTIN", "UNSPSC", "Country Of Origin"];
    const dimKeys = ["LENGTH", "WIDTH", "HEIGHT", "WEIGHT", "VOLUME"];

    Object.entries(productData.delivery_row).forEach(([key, value]) => {
      if (value === null || value === "" || value === undefined) return;
      if (key.startsWith("ATTRIBUTE_") || key.startsWith("ITEM_FEATURES_")) return;
      if (key.endsWith("_UOM")) return; // Handled alongside dimensions

      const strValue = String(value);
      const formattedKey = formatKeyName(key);

      if (key.includes("DESC") || key.includes("Desc") || key.includes("Description")) {
        descriptions.push({ key: formattedKey, value: strValue });
      } else if (key.includes("URL") || key.includes("Link") || strValue.startsWith("http")) {
        urls.push({ key, value: strValue }); // keep original key for URLs since they are usually specific like "MFR URL"
      } else if (commerceKeys.includes(key)) {
        commerce.push({ id: key, key: formattedKey, value: strValue });
      } else if (dimKeys.includes(key)) {
        const uomVal = productData.delivery_row![`${key}_UOM`];
        dimensions.push({ 
          id: key, 
          key: formattedKey, 
          value: strValue, 
          uom: uomVal ? String(uomVal) : "-",
          source: sourceMap[key]
        });
      } else {
        rawFields.push({ id: key, key: formattedKey, value: strValue, source: sourceMap[key] });
      }
    });
  }

  const attrColumns: any[] = [
    { key: "name", header: "Name", width: proportional(2) },
    { key: "value", header: "Value", width: proportional(3), render: (row: any) => (
      <HStack align="center" gap={2}>
        <Text>{row.value}</Text>
        <SourceBadge source={row.source} />
      </HStack>
    )},
    { key: "uom", header: "UOM", width: proportional(1) },
  ];

  const featureColumns: any[] = [
    { key: "feature", header: "Feature", width: proportional(1) },
  ];

  const rawColumns: any[] = [
    { key: "key", header: "Field", width: proportional(2) },
    { key: "value", header: "Value", width: proportional(3), render: (row: any) => (
      <HStack align="center" gap={2}>
        <Text>{row.value}</Text>
        <SourceBadge source={row.source} />
      </HStack>
    ) },
  ];

  return (
    <Dialog
      isOpen
      onOpenChange={(isOpen) => {
        if (!isOpen) selectProduct(null);
      }}
      width={800}
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
            <VStack gap={4} width="100%" padding={5}>
              {productData && (
                <HStack align="center" justify="between" style={{ paddingBottom: 8, borderBottom: '1px solid var(--astryx-border-muted, #333)' }}>
                  <VStack gap={1}>
                    <Heading level={3}>{productData.mpn || "Unknown MPN"}</Heading>
                    <Text type="supporting">
                      <Text as="span" weight="semibold" color="primary">{productData.brand || "Unknown Brand"}</Text> • {productData.manufacturer || "Unknown Manufacturer"}
                    </Text>
                  </VStack>
                  <Badge variant={statusVariant} label={productData.status.toUpperCase()} />
                </HStack>
              )}

              {loading ? (
                <VStack gap={3} width="100%">
                  <Skeleton width="100%" height={100} />
                  <Skeleton width="100%" height={150} />
                </VStack>
              ) : productData ? (
                <VStack gap={4} width="100%">
                  
                  {/* Validation Card */}
                  <Card variant="muted" padding={4} width="100%">
                    <VStack gap={3} hAlign="stretch">
                      <Heading level={4}>Validation & Execution</Heading>
                      
                      <HStack gap={6} align="center">
                        <VStack gap={0.5}>
                          <Text type="supporting">Score</Text>
                          <Text type="body" weight="semibold">{productData.validation_score.toFixed(0)}%</Text>
                        </VStack>
                        <VStack gap={0.5}>
                          <Text type="supporting">Time</Text>
                          <Text type="body" weight="semibold">{productData.processing_time.toFixed(2)}s</Text>
                        </VStack>
                      </HStack>
                      
                      {productData.error && (
                        <Card padding={3} style={{ backgroundColor: "var(--astryx-bg-error-subtle, #451a1a)", borderColor: "var(--astryx-border-error, #7f1d1d)" }}>
                          <VStack gap={1} hAlign="stretch">
                            <Text type="body" weight="semibold" style={{ color: "#fca5a5" }}>Pipeline Error</Text>
                            <Text type="code" style={{ color: "#fecaca", wordBreak: "break-word", whiteSpace: "pre-wrap" }}>
                              {productData.error}
                            </Text>
                          </VStack>
                        </Card>
                      )}

                      <VStack gap={2} hAlign="stretch" style={{ marginTop: 8 }}>
                        {Object.entries(productData.validation).map(([rule, passed]) => (
                          <HStack key={rule} justify="between" align="center" style={{ paddingBottom: 8, borderBottom: '1px solid var(--astryx-border-muted, #333)' }}>
                            <Text type="code" color="secondary">{rule}</Text>
                            <Badge variant={passed ? "success" : "error"} label={passed ? "Passed" : "Failed"} />
                          </HStack>
                        ))}
                      </VStack>
                    </VStack>
                  </Card>

                  {/* Descriptions Card */}
                  {descriptions.length > 0 && (
                    <Card variant="muted" padding={4} width="100%">
                      <VStack gap={4} hAlign="stretch">
                        <Heading level={4}>Descriptions</Heading>
                        <VStack gap={4} hAlign="stretch">
                          {descriptions.map((desc) => (
                            <VStack key={desc.key} gap={1.5} hAlign="stretch">
                              <Text type="body" weight="semibold" color="secondary">{desc.key}</Text>
                              <Text type="body" style={{ lineHeight: 1.6, wordBreak: "break-word", color: 'var(--astryx-text-primary)' }}>{desc.value}</Text>
                            </VStack>
                          ))}
                        </VStack>
                      </VStack>
                    </Card>
                  )}

                  {/* Attributes and Features */}
                  <VStack gap={4} hAlign="stretch">
                    {attributes.length > 0 && (
                      <Card variant="muted" padding={4} width="100%">
                        <VStack gap={3} hAlign="stretch">
                          <Heading level={4}>Extracted Attributes</Heading>
                          <Card width="100%">
                            <Table data={attributes} columns={attrColumns} idKey="id" density="compact" />
                          </Card>
                        </VStack>
                      </Card>
                    )}

                    {features.length > 0 && (
                      <Card variant="muted" padding={4} width="100%">
                        <VStack gap={3} hAlign="stretch">
                          <Heading level={4}>Features</Heading>
                          <Card width="100%">
                            <Table data={features} columns={featureColumns} idKey="id" density="compact" />
                          </Card>
                        </VStack>
                      </Card>
                    )}
                  </VStack>

                  {/* Commerce & Dimensions */}
                  <VStack gap={4} hAlign="stretch">
                    {dimensions.length > 0 && (
                      <Card variant="muted" padding={4} width="100%">
                        <VStack gap={3} hAlign="stretch">
                          <Heading level={4}>Dimensions & Weight</Heading>
                          <Card width="100%">
                            <Table data={dimensions} columns={attrColumns.map(c => c.key === 'name' ? {...c, key: 'key'} : c)} idKey="id" density="compact" />
                          </Card>
                        </VStack>
                      </Card>
                    )}

                    {commerce.length > 0 && (
                      <Card variant="muted" padding={4} width="100%">
                        <VStack gap={3} hAlign="stretch">
                          <Heading level={4}>Commerce & Packaging</Heading>
                          <Card width="100%">
                            <Table data={commerce} columns={rawColumns} idKey="id" density="compact" />
                          </Card>
                        </VStack>
                      </Card>
                    )}
                  </VStack>

                  {/* General Delivery Fields Table */}
                  {rawFields.length > 0 && (
                    <Card variant="muted" padding={4} width="100%">
                      <VStack gap={3} hAlign="stretch">
                        <Heading level={4}>General Properties</Heading>
                        <Card width="100%">
                          <Table data={rawFields} columns={rawColumns} idKey="id" density="compact" />
                        </Card>
                      </VStack>
                    </Card>
                  )}

                  {/* Reference URLs */}
                  {urls.length > 0 && (
                    <Card variant="muted" padding={4} width="100%">
                      <VStack gap={3} hAlign="stretch">
                        <Heading level={4}>Reference Links</Heading>
                        <VStack gap={3} hAlign="stretch">
                          {urls.map((urlItem) => (
                            <VStack key={urlItem.key} gap={1} hAlign="stretch">
                              <Text type="code" color="secondary" style={{ fontSize: "0.8rem" }}>{urlItem.key}</Text>
                              <a href={urlItem.value} target="_blank" rel="noopener noreferrer" style={{ color: "var(--astryx-accent, #60a5fa)", textDecoration: "underline", wordBreak: "break-all", fontSize: "0.875rem" }}>
                                {urlItem.value}
                              </a>
                            </VStack>
                          ))}
                        </VStack>
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
