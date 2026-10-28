import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NodesPage } from '../pages/NodesPage';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getNodes: vi.fn(),
    createNode: vi.fn(),
    updateNode: vi.fn(),
    deleteNode: vi.fn(),
  },
}));

describe('NodesPage Inventory Workflow', () => {
  const sampleNodes = [
    {
      node_id: 'NODE-01',
      name: 'North Highwall Bench Extensometer',
      latitude: 23.7541,
      longitude: 86.4215,
      elevation_m: 182.5,
      node_type: 'highwall_extensometer',
      installation_location: 'Bench 4 Section B',
      connectivity_status: 'ONLINE',
      battery_pct: 88.0,
      last_seen: '2026-10-28T05:30:00Z',
      is_enabled: true,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    api.getNodes.mockResolvedValue({
      total: 1,
      items: sampleNodes,
    });
  });

  it('renders sensor node inventory table', async () => {
    render(
      <BrowserRouter>
        <NodesPage />
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Sensor Node Inventory/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('NODE-01')).toBeInTheDocument();
      expect(screen.getByText('North Highwall Bench Extensometer')).toBeInTheDocument();
      expect(screen.getByText(/88%/i)).toBeInTheDocument();
    });
  });

  it('opens register node modal when Register button clicked', async () => {
    render(
      <BrowserRouter>
        <NodesPage />
      </BrowserRouter>
    );

    const regBtn = screen.getByText(/Register New Node/i);
    fireEvent.click(regBtn);

    expect(screen.getByText('Register Geotechnical Node')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. NODE-PIT-EAST-07')).toBeInTheDocument();
  });

  it('opens decommission modal and allows soft and hard delete', async () => {
    api.deleteNode.mockResolvedValue({ success: true });

    render(
      <BrowserRouter>
        <NodesPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByTitle('Decommission / Remove Node')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle('Decommission / Remove Node'));

    expect(screen.getByText(/Decommission Node NODE-01/i)).toBeInTheDocument();

    // Check hard delete checkbox
    const hardCheck = screen.getByLabelText(/Permanently purge all associated telemetry/i);
    fireEvent.click(hardCheck);

    // Submit
    fireEvent.click(screen.getByText('Permanently Delete'));

    await waitFor(() => {
      expect(api.deleteNode).toHaveBeenCalledWith('NODE-01', true);
    });
  });
});
