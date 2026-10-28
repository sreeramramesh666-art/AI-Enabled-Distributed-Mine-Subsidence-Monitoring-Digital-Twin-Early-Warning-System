import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardPage } from '../pages/DashboardPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getAnalyticsSummary: vi.fn(),
    getSimulatorStatus: vi.fn(),
    getAlerts: vi.fn(),
    startSimulator: vi.fn(),
    stopSimulator: vi.fn(),
  },
}));

describe('DashboardPage Command Center', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getAnalyticsSummary.mockResolvedValue({
      total_nodes: 6,
      online_nodes: 5,
      stale_nodes: 1,
      offline_nodes: 0,
      overall_risk_category: 'NORMAL',
      active_critical_alerts: 0,
      active_warning_alerts: 1,
      data_completeness_pct: 99.2,
    });
    api.getSimulatorStatus.mockResolvedValue({
      is_running: false,
      scenario: 'baseline',
    });
    api.getAlerts.mockResolvedValue({
      total: 1,
      items: [
        {
          alert_id: 'ALERT-01',
          node_id: 'NODE-01',
          category: 'VELOCITY',
          severity: 'WARNING',
          title: 'Velocity creeping above 2.0 mm/hr threshold',
          status: 'ACTIVE',
          created_at: '2026-10-28T05:30:00Z',
        },
      ],
    });
  });

  it('renders command center KPIs, live ticker, and alert feed', async () => {
    render(
      <BrowserRouter>
        <DashboardPage
          latestTelemetry={{
            node_id: 'NODE-01',
            displacement_mm: 12.45,
            velocity_mm_hr: 1.85,
            vector_tilt_deg: 1.2,
            vibration_rms_ms2: 0.45,
            data_source: 'simulator',
          }}
          latestAlert={null}
        />
      </BrowserRouter>
    );

    expect(screen.getByText(/Connecting to MineGuard-AI backend services/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Mine Geohazard Command Center/i)).toBeInTheDocument();
      expect(screen.getByText('MONITORED NODES')).toBeInTheDocument();
      expect(screen.getByText('6')).toBeInTheDocument();
      expect(screen.getByText('MINE RISK STATUS')).toBeInTheDocument();
      expect(screen.getByText('99.2%')).toBeInTheDocument();
      expect(screen.getByText('12.450 mm')).toBeInTheDocument();
      expect(screen.getByText(/Velocity creeping above 2.0 mm\/hr/i)).toBeInTheDocument();
    });
  });

  it('toggles simulation from the command center action bar', async () => {
    api.startSimulator.mockResolvedValue({ is_running: true });

    render(
      <BrowserRouter>
        <DashboardPage latestTelemetry={null} latestAlert={null} />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Start Simulation/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Start Simulation/i }));

    await waitFor(() => {
      expect(api.startSimulator).toHaveBeenCalledWith({
        scenario: 'accelerating_subsidence',
        interval_sec: 2.0,
      });
    });
  });
});
