import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ExperimentsPage } from '../pages/ExperimentsPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getTestRuns: vi.fn(),
    startTestRun: vi.fn(),
    recordReferenceMovement: vi.fn(),
    completeTestRun: vi.fn(),
    getTestRunCsvUrl: vi.fn((id) => `/api/v1/test-runs/${id}/export/csv`),
    getTestRunPdfUrl: vi.fn((id) => `/api/v1/test-runs/${id}/export/pdf`),
  },
}));

describe('ExperimentsPage Workflow (Table 12 Evaluation)', () => {
  const sampleTestRun = {
    id: 1,
    test_run_id: 'TR-20261028-TEST',
    name: 'Laboratory Benchmark Test #1',
    scenario: 'testrig_gradual',
    test_conditions: 'Controlled granular testbed with micrometer lead screw',
    target_node_id: 'NODE-PIT-NORTH-01',
    status: 'COMPLETED',
    start_time: '2026-10-28T06:00:00Z',
    end_time: '2026-10-28T06:05:00Z',
    intended_movement_mm: 5.0,
    reference_movement_mm: 5.0,
    sensor_reported_movement_mm: 4.96,
    measurement_error_mm: 0.04,
    detection_latency_sec: 4.2,
    metrics: {
      packet_delivery_ratio_pct: 98.5,
      false_alerts_count: 0,
      false_alerts_denominator: '0 false alerts / 60 samples',
      precision: 1.0,
      recall: 1.0,
      f1_score: 1.0,
      relative_error_pct: 0.8,
    },
    notes: 'Dial indicator reading confirmed',
    created_at: '2026-10-28T06:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.getTestRuns.mockResolvedValue({
      total: 1,
      items: [sampleTestRun],
    });
  });

  it('renders benchmark header and Table 12 evaluation metrics', async () => {
    render(<ExperimentsPage />);

    expect(screen.getByText(/Laboratory Test-Rig Benchmark & Evaluation/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Table 12: Laboratory Benchmark Metrics Summary/i)).toBeInTheDocument();
      expect(screen.getAllByText('Laboratory Benchmark Test #1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/4.960 mm/i)).toBeInTheDocument();
      expect(screen.getByText(/0.040 mm/i)).toBeInTheDocument();
      expect(screen.getByText(/98.5%/i)).toBeInTheDocument();
    });
  });

  it('renders start test run button and launches modal', async () => {
    render(<ExperimentsPage />);

    const startBtn = screen.getByText(/Start New Test Run/i);
    expect(startBtn).toBeInTheDocument();
    fireEvent.click(startBtn);

    expect(screen.getByText(/Initialize Laboratory Test-Rig Experiment/i)).toBeInTheDocument();
  });
});
