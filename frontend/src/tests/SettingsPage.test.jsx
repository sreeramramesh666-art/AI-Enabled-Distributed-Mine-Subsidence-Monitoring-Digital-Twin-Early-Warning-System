import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SettingsPage } from '../pages/SettingsPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    getHealth: vi.fn(),
    getAuditEvents: vi.fn(),
  },
}));

describe('SettingsPage Workflow', () => {
  const initialSettings = {
    tilt_warning_deg: 2.0,
    tilt_critical_deg: 5.0,
    displacement_warning_mm: 15.0,
    displacement_critical_mm: 30.0,
    rate_warning_mm_hr: 2.0,
    rate_critical_mm_hr: 5.0,
    accel_warning_mm_hr2: 0.5,
    vibration_warning_ms2: 3.0,
    vibration_critical_ms2: 8.0,
    battery_low_pct: 20.0,
    stale_data_timeout_sec: 120,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.getSettings.mockResolvedValue(initialSettings);
    api.getHealth.mockResolvedValue({
      status: 'healthy',
      app: 'MineGuard-AI',
      version: '1.0.0',
      database: 'connected',
      mqtt_status: 'disabled',
      simulator_running: false,
    });
    api.getAuditEvents.mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          category: 'SETTINGS',
          actor: 'SystemAdmin',
          timestamp: '2026-10-28T05:00:00Z',
          description: 'Initial geotechnical threshold baseline established',
        },
      ],
    });
  });

  it('renders health probes and configurable thresholds', async () => {
    render(<SettingsPage />);

    expect(screen.getByText(/Configuration & System Diagnostics/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/SQLite Engine Connected/i)).toBeInTheDocument();
      expect(screen.getByText(/Initial geotechnical threshold baseline/i)).toBeInTheDocument();
    });
  });

  it('rejects invalid threshold hierarchy before submitting to backend', async () => {
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('15')).toBeInTheDocument();
    });

    // Set displacement warning to 40 (greater than critical 30)
    const warnInput = screen.getByDisplayValue('15');
    fireEvent.change(warnInput, { target: { value: '40.0' } });

    // Click Save
    fireEvent.click(screen.getByText('Save Configuration'));

    // Should display validation error
    await waitFor(() => {
      expect(screen.getByText(/Displacement Warning threshold must be strictly less than Critical threshold/i)).toBeInTheDocument();
    });

    // updateSettings should NOT have been called
    expect(api.updateSettings).not.toHaveBeenCalled();
  });
});

