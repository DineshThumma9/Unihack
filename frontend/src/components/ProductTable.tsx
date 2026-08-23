import {
  Card,
  VStack,
  Heading,
  Text,
  Table,
  Badge,
  Button,
  EmptyState,
  type TableColumn,
} from "@astryxdesign/core";
import { FileSearch } from "lucide-react";
import { useJobStore } from "../stores/job.store";
import type { ProductProgress } from "../types/job";

export function ProductTable() {
  const { status, products, selectProduct } = useJobStore();

  const productsList = Object.values(products).sort((a, b) => a.index - b.index);
  const isProcessing = status === "running" || status === "queued";

  const tableColumns: TableColumn<ProductProgress>[] = [
    {
      key: "index",
      header: "#",
      renderCell: (item) => <Text type="supporting">#{item.index + 1}</Text>,
    },
    {
      key: "mpn",
      header: "Mfg Part Num",
      renderCell: (item) => (
        <Text type="body" weight="semibold">
          {item.mpn}
        </Text>
      ),
    },
    {
      key: "status",
      header: "Status",
      renderCell: (item) => {
        if (item.status === "success") return <Badge variant="success" label="Success" />;
        if (item.status === "warning") return <Badge variant="warning" label="Warning" />;
        if (item.status === "failed") return <Badge variant="error" label="Failed" />;
        return <Badge variant="neutral" label="Processing" />;
      },
    },
    {
      key: "manufacturer",
      header: "Manufacturer",
      renderCell: (item) => <Text type="body">{item.manufacturer || "-"}</Text>,
    },
    {
      key: "brand",
      header: "Brand",
      renderCell: (item) => <Text type="body">{item.brand || "-"}</Text>,
    },
    {
      key: "attributes_found",
      header: "Attributes",
      renderCell: (item) => (
        <Text type="body">
          {item.attributes_found !== undefined && item.attributes_found > 0
            ? `${item.attributes_found} found`
            : item.attributes_found === 0
              ? <Text type="supporting" color="secondary">0 found</Text>
              : "-"}
        </Text>
      ),
    },
    {
      key: "confidence",
      header: "Confidence",
      renderCell: (item) => {
        if (item.status === "processing" || item.status === "queued") return null;
        if (item.status === "failed") return <Badge variant="error" label="Failed" />;
        if (item.validation_passed) return <Badge variant="success" label="Verified" />;
        return <Badge variant="info" label="Inferred" />;
      },
    },
    {
      key: "processing_time",
      header: "Time",
      renderCell: (item) => (
        <Text type="supporting">
          {item.processing_time ? `${item.processing_time.toFixed(1)}s` : "-"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "Inspect",
      renderCell: (item) => (
        <Button
          label="Inspect"
          variant="secondary"
          size="sm"
          onClick={() => selectProduct(item.index)}
        />
      ),
    },
  ];

  return (
    <Card padding={4} width="100%">
      <VStack gap={4} width="100%">
        {productsList.length > 0 ? (
          <VStack gap={3} width="100%">
            <Heading level={2}>Processed Products ({productsList.length})</Heading>
            <Table<ProductProgress>
              data={productsList}
              columns={tableColumns}
              idKey="index"
              hasHover
            />
          </VStack>
        ) : (
          <VStack hAlign="center" justify="center" width="100%" paddingBlock={8}>
            <EmptyState
              title={isProcessing ? "Processing Data..." : "No CSV Data Loaded"}
              description={
                isProcessing
                  ? "Products will appear here as they are processed."
                  : "Upload a CSV file to start enrichment."
              }
              icon={<FileSearch />}
            />
          </VStack>
        )}
      </VStack>
    </Card>
  );
}
