import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SimulatorPage } from '../pages/SimulatorPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getSimulatorStatus: vi.fn(),
    startSimulator: vi.fn(),
    stopSimulator: vi.fn(),
    resetSimulator: vi.fn(),
  },
}));

describe('SimulatorPage Control Workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSimulatorStatus.mockResolvedValue({
      is_running: false,
      scenario: 'baseline',
      ticks_generated: 42,
    });
  });

  it('renders scenarios and starts synthetic generation', async () => {
    api.startSimulator.mockResolvedValue({
      is_running: true,
      scenario: 'accelerating_subsidence',
      ticks_generated: 43,
    });

    render(<SimulatorPage latestTelemetry={null} />);

    expect(screen.getByText(/DETERMINISTIC SENSOR SIMULATOR ACTIVE/i)).toBeInTheDocument();
    expect(screen.getByText(/Accelerating Subsidence \(Tertiary Creep\)/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Start Scenario/i })).toBeInTheDocument();
    });

    // Select Accelerating Subsidence radio
    fireEvent.click(screen.getByDisplayValue('accelerating_subsidence'));

    fireEvent.click(screen.getByRole('button', { name: /Start Scenario/i }));

    await waitFor(() => {
      expect(api.startSimulator).toHaveBeenCalledWith(
        expect.objectContaining({
          scenario: 'accelerating_subsidence',
          interval_sec: 2.0,
        })
      );
    });
  });
});
