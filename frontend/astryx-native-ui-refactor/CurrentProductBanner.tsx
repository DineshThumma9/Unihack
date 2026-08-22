import { Card, VStack, HStack, Text } from "@astryxdesign/core";
import { useJobStore } from "../stores/job.store";

export function CurrentProductBanner() {
  const { currentProduct } = useJobStore();

  if (!currentProduct) return null;

  return (
    <Card variant="muted" padding={3} width="100%">
      <VStack gap={1} hAlign="stretch">
        <HStack gap={2} align="center">
          <Text type="supporting" weight="semibold">Currently processing</Text>
          <Text type="code" weight="semibold">{currentProduct.mpn}</Text>
        </HStack>
        {currentProduct.manufacturer && (
          <Text type="supporting">Manufacturer: {currentProduct.manufacturer}</Text>
        )}
      </VStack>
    </Card>
  );
}
