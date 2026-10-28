import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReportsPage } from '../pages/ReportsPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getNodes: vi.fn(),
    getAnalyticsSummary: vi.fn(),
  },
}));

describe('ReportsPage Export Workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getNodes.mockResolvedValue({
      total: 1,
      items: [{ node_id: 'NODE-01', name: 'Bench Sector A' }],
    });
    api.getAnalyticsSummary.mockResolvedValue({
      total_nodes: 6,
      online_nodes: 5,
      active_critical_alerts: 1,
      data_completeness_pct: 98.5,
    });
    // mock window.open
    window.open = vi.fn();
  });

  it('renders report cards and triggers PDF download', async () => {
    render(<ReportsPage />);

    expect(screen.getByText(/Geotechnical Export & Audit Reports/i)).toBeInTheDocument();
    expect(screen.getByText(/Formal Geotechnical Audit Dossier \(PDF\)/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Download Comprehensive PDF Report/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Download Comprehensive PDF Report/i));

    expect(window.open).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/reports/export?format=pdf'),
      '_blank'
    );
  });

  it('triggers CSV download with selected node scope', async () => {
    render(<ReportsPage />);

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'NODE-01' } });

    fireEvent.click(screen.getByText(/Export Raw Measurements \(CSV\)/i));

    expect(window.open).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/reports/export?format=csv&node_id=NODE-01'),
      '_blank'
    );
  });
});
