import { useState, useEffect, useRef } from 'react';
import {
  FileInput,
  Table,
  ProgressBar,
  Skeleton,
  Text,
  Button,
  Card,
  VStack,
  HStack,
  StackItem,
  EmptyState
} from '@astryxdesign/core';
import type { TableColumn } from '@astryxdesign/core';

interface ProductRow {
  id: string;
  name: string;
  category: string;
  price: string;
  status: string;
  [key: string]: string; // Fallback for dynamic fields
}

const DEMO_CSV_TEXT = `id,name,category,price,status
101,UltraWidget,Electronics,$29.99,In Stock
102,SuperGizmo,Electronics,$49.99,Low Stock
103,EcoBottle,Home,$15.49,In Stock
104,FlexMat,Fitness,$35.00,Out of Stock
105,SmartLight,IoT,$19.99,In Stock
106,SoundBar,Audio,$89.99,In Stock
107,KeyTracker,Accessories,$24.99,In Stock
108,PowerBank,Electronics,$39.99,Low Stock
109,AirPurifier,Home,$129.99,In Stock
110,YogaBlock,Fitness,$12.00,In Stock`;

export function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<ProductRow[]>([]);
  
  // Simulation State
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const timerRef = useRef<any>(null);

  // Parse CSV helper
  const parseCSV = (text: string) => {
    const lines = text.split(/\r?\n/).map(line => line.trim()).filter(line => line !== '');
    if (lines.length === 0) return { headers: [], rows: [] };
    
    const headers = lines[0].split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
    const rows = lines.slice(1).map((line, idx) => {
      const values = line.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
      const row: any = { id: values[0] || String(idx + 1) };
      headers.forEach((header, i) => {
        row[header] = values[i] || '';
      });
      return row as ProductRow;
    });
    
    return { headers, rows };
  };

  // Handle selected file
  const handleFileChange = (files: File | File[] | null) => {
    const selectedFile = Array.isArray(files) ? files[0] : files;
    setFile(selectedFile);
    setIsComplete(false);
    setIsProcessing(false);
    setProgress(0);
    
    if (!selectedFile) {
      setCsvHeaders([]);
      setCsvRows([]);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const { headers, rows } = parseCSV(text);
      if (headers.length === 0 || rows.length === 0) {
        setError('Invalid CSV format or empty file.');
        setFile(null);
        return;
      }
      setCsvHeaders(headers);
      setCsvRows(rows);
      setError(null);
    };
    reader.onerror = () => {
      setError('Error reading file.');
      setFile(null);
    };
    reader.readAsText(selectedFile);
  };

  // Load demo CSV
  const loadDemoCSV = () => {
    const blob = new Blob([DEMO_CSV_TEXT], { type: 'text/csv' });
    const mockFile = new File([blob], 'demo_products.csv', { type: 'text/csv' });
    handleFileChange(mockFile);
  };

  // Start row-by-row simulation
  const startProcessing = () => {
    if (csvRows.length === 0) return;
    setIsProcessing(true);
    setIsComplete(false);
    setProgress(0);
    
    const delayPerItem = 600; // ms per row
    const total = csvRows.length;
    setEstimatedTime(Math.ceil((total * delayPerItem) / 1000));

    let current = 0;
    timerRef.current = setInterval(() => {
      current += 1;
      setProgress(current);
      setEstimatedTime(Math.ceil(((total - current) * delayPerItem) / 1000));
      
      if (current >= total) {
        if (timerRef.current) clearInterval(timerRef.current);
        setIsProcessing(false);
        setIsComplete(true);
      }
    }, delayPerItem);
  };

  // Listen for Enter key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && file && !isProcessing && !isComplete) {
      startProcessing();
    }
  };

  const resetAll = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setFile(null);
    setCsvHeaders([]);
    setCsvRows([]);
    setIsProcessing(false);
    setIsComplete(false);
    setProgress(0);
    setEstimatedTime(0);
    setError(null);
  };

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Build columns for Astryx Table
  const tableColumns: TableColumn<ProductRow>[] = csvHeaders.map((header) => ({
    key: header,
    header: header.charAt(0).toUpperCase() + header.slice(1),
    renderCell: (item: ProductRow) => (
      <Text type="body">
        {item[header] || ''}
      </Text>
    ),
  }));

  // Total products in CSV
  const totalProducts = csvRows.length;

  return (
    <VStack
      gap={10}
      width="100%"
      height="100%"
      align="center"
      justify="center"
      style={{
        minHeight: '100svh',
        padding: 'var(--spacing-10) var(--spacing-6)',
        boxSizing: 'border-box',
      }}
      onKeyDown={handleKeyDown}
    >
      {/* Top Section - upload and progress */}
      <StackItem style={{ width: '100%', maxWidth: '800px' }}>
        <Card padding={4} height="100%" style={{ boxSizing: 'border-box' }}>
          <VStack gap={3} height="100%" justify="center" align="stretch">
            {isProcessing ? (
              // Processing View: Progress Bar + Skeleton + Stats
              <VStack gap={4} width="100%">
                <ProgressBar
                  label="Importing CSV Products"
                  value={progress}
                  max={totalProducts}
                  hasValueLabel
                  formatValueLabel={(val, max) => `${val} / ${max} products processed (${Math.round((val / max) * 100)}%)`}
                />
                
                {/* Product Detail Skeleton Shimmer representing current item */}
                <Card padding={3} style={{ background: 'var(--color-background-secondary)' }}>
                  <VStack gap={2}>
                    <HStack gap={2} vAlign="center">
                      <Text type="supporting" color="secondary" weight="semibold">Currently processing:</Text>
                      {csvRows[progress - 1] ? (
                        <Text type="body" weight="semibold" color="accent">
                          {csvRows[progress - 1].name || 'Unnamed product'}
                        </Text>
                      ) : (
                        <Skeleton width={150} height={20} />
                      )}
                    </HStack>
                    <HStack gap={4}>
                      <HStack gap={1} vAlign="center">
                        <Text type="supporting" color="secondary">Category:</Text>
                        {csvRows[progress - 1] ? (
                          <Text type="body">{csvRows[progress - 1].category || 'N/A'}</Text>
                        ) : (
                          <Skeleton width={80} height={16} />
                        )}
                      </HStack>
                      <HStack gap={1} vAlign="center">
                        <Text type="supporting" color="secondary">Price:</Text>
                        {csvRows[progress - 1] ? (
                          <Text type="body">{csvRows[progress - 1].price || 'N/A'}</Text>
                        ) : (
                          <Skeleton width={60} height={16} />
                        )}
                      </HStack>
                    </HStack>
                  </VStack>
                </Card>
                
                {/* Stats at bottom */}
                <HStack hAlign="between" width="100%">
                  <Text type="supporting" color="secondary">
                    Total: {totalProducts} Products
                  </Text>
                  <Text type="supporting" color="secondary">
                    Estimated Time: {estimatedTime} seconds remaining
                  </Text>
                </HStack>
              </VStack>
            ) : isComplete ? (
              // Complete State
              <VStack gap={4} hAlign="center" justify="center">
                <Text type="large" weight="semibold" color="accent">
                  ✓ Import Complete
                </Text>
                <Text type="body" color="secondary">
                  Successfully parsed and loaded {totalProducts} products into the table below.
                </Text>
                <Button label="Upload New File" variant="primary" onClick={resetAll} />
              </VStack>
            ) : (
              // Upload State: FileInput + Actions
              <VStack gap={4} width="100%">
                <FileInput
                  label="CSV File Upload"
                  value={file}
                  onChange={handleFileChange}
                  accept=".csv"
                  mode="dropzone"
                  width="100%"
                  description="Upload product CSV files to populate table. Press Enter to process."
                  status={error ? { type: 'error', message: error } : undefined}
                />
                
                {file ? (
                  <HStack gap={2} hAlign="center">
                    <Button
                      label="Process CSV (Enter)"
                      variant="primary"
                      onClick={startProcessing}
                    />
                    <Button
                      label="Clear"
                      variant="secondary"
                      onClick={resetAll}
                    />
                  </HStack>
                ) : (
                  <HStack gap={2} hAlign="center">
                    <Button
                      label="Load Demo CSV"
                      variant="secondary"
                      onClick={loadDemoCSV}
                    />
                  </HStack>
                )}
              </VStack>
            )}
          </VStack>
        </Card>
      </StackItem>

      {/* Bottom Section - table list */}
      <StackItem style={{ width: '100%', maxWidth: '1000px', maxHeight: '50svh' }} isScrollable>
        <Card padding={4} height="100%" style={{ boxSizing: 'border-box', minHeight: '300px' }}>
          <VStack gap={3} height="100%">
            {isComplete ? (
              // Display complete table
              <VStack gap={3} width="100%">
                <Text type="large" weight="semibold">
                  Parsed CSV Data ({totalProducts} items)
                </Text>
                <Table<ProductRow>
                  data={csvRows}
                  columns={tableColumns}
                  idKey="id"
                  hasHover
                />
              </VStack>
            ) : (
              // Empty/Placeholder view
              <VStack hAlign="center" justify="center" height="100%">
                <EmptyState
                  title={isProcessing ? "Processing Data..." : "No CSV Data Loaded"}
                  description={
                    isProcessing
                      ? "Please wait while we simulate processing each item in your CSV file."
                      : "Once you upload a CSV file and complete processing, the table contents will be populated here."
                  }
                />
              </VStack>
            )}
          </VStack>
        </Card>
      </StackItem>
    </VStack>
  );
}

export default HomePage;