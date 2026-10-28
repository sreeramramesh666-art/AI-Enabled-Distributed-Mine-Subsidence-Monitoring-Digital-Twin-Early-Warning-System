import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AlertsPage } from '../pages/AlertsPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getAlerts: vi.fn(),
    acknowledgeAlert: vi.fn(),
    resolveAlert: vi.fn(),
  },
}));

describe('AlertsPage Workflow', () => {
  const sampleAlert = {
    alert_id: 'ALERT-TEST-01',
    node_id: 'NODE-PIT-01',
    category: 'DISPLACEMENT',
    severity: 'CRITICAL',
    title: 'Highwall bench displacement exceeded 30mm threshold',
    description: 'Measured 32.500 mm cumulative displacement',
    triggering_rule: 'RULE_CRITICAL_DISPLACEMENT',
    status: 'ACTIVE',
    evidence: { displacement_mm: 32.5 },
    created_at: '2026-10-28T05:30:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.getAlerts.mockResolvedValue({
      total: 1,
      items: [sampleAlert],
    });
  });

  it('renders alerts table with regulatory notice and active hazard', async () => {
    render(<AlertsPage />);

    expect(screen.getByText(/Alerts & Geohazard Lifecycle Centre/i)).toBeInTheDocument();
    expect(screen.getByText(/Operational Notice:/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('NODE-PIT-01')).toBeInTheDocument();
      expect(screen.getByText(/Highwall bench displacement/i)).toBeInTheDocument();
    });
  });

  it('opens acknowledgement modal and submits operator confirmation', async () => {
    api.acknowledgeAlert.mockResolvedValue({
      ...sampleAlert,
      status: 'ACKNOWLEDGED',
      acknowledged_by: 'Safety Officer Singh',
    });

    render(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByTitle('Acknowledge Alert')).toBeInTheDocument();
    });

    // Click Acknowledge button
    fireEvent.click(screen.getByTitle('Acknowledge Alert'));

    // Modal title should appear
    expect(screen.getByText('Acknowledge Geohazard Alert')).toBeInTheDocument();

    // Fill note
    const noteInput = screen.getByPlaceholderText(/e\.g\. Dispatched geotechnical surveyor/i);
    fireEvent.change(noteInput, { target: { value: 'Visual inspection underway' } });

    // Confirm acknowledgement
    fireEvent.click(screen.getByText('Confirm Acknowledgement'));

    await waitFor(() => {
      expect(api.acknowledgeAlert).toHaveBeenCalledWith('ALERT-TEST-01', {
        acknowledged_by: 'Safety Officer Singh',
        note: 'Visual inspection underway',
      });
    });
  });
});

