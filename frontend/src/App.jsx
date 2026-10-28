import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './api/client';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';

// Pages
import { DashboardPage } from './pages/DashboardPage';
import { MapPage } from './pages/MapPage';
import { NodesPage } from './pages/NodesPage';
import { TelemetryPage } from './pages/TelemetryPage';
import { AlertsPage } from './pages/AlertsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';

export function App() {
  const [latestTelemetry, setLatestTelemetry] = useState(null);
  const [latestAlert, setLatestAlert] = useState(null);
  const [latestNodeStatus, setLatestNodeStatus] = useState(null);
  const [activeAlertCount, setActiveAlertCount] = useState(0);
  const [simulatorRunning, setSimulatorRunning] = useState(false);

  // Poll simulator and alert counts initially and periodically
  const refreshStatus = useCallback(async () => {
    try {
      const [alerts, sim] = await Promise.all([
        api.getAlerts({ status: 'ACTIVE' }),
        api.getSimulatorStatus(),
      ]);
      setActiveAlertCount(alerts.total || 0);
      setSimulatorRunning(sim.is_running || false);
    } catch (e) {
      // offline / backend initializing
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 8000);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  // Handle incoming live WebSocket events
  const handleWebSocketEvent = useCallback((event) => {
    if (!event) return;
    const { type, data } = event;

    if (type === 'telemetry') {
      setLatestTelemetry(data);
    } else if (type === 'node_status') {
      setLatestNodeStatus(data);
    } else if (type === 'alert') {
      setLatestAlert(data);
      setActiveAlertCount((prev) => prev + 1);
    } else if (type === 'simulator_status') {
      setSimulatorRunning(data.is_running);
    }
  }, []);

  const { isConnected } = useWebSocket(handleWebSocketEvent);

  return (
    <BrowserRouter>
      <div className="container-full">
        <Sidebar alertCount={activeAlertCount} />
        <div className="main-content">
          <Navbar
            isConnected={isConnected}
            simulatorRunning={simulatorRunning}
            onToggleSimulator={refreshStatus}
          />
          <main style={{ flex: 1, paddingBottom: '2rem' }}>
            <Routes>
              <Route
                path="/"
                element={
                  <DashboardPage
                    latestTelemetry={latestTelemetry}
                    latestAlert={latestAlert}
                  />
                }
              />
              <Route
                path="/map"
                element={<MapPage latestTelemetry={latestTelemetry} latestNodeStatus={latestNodeStatus} />}
              />
              <Route path="/nodes" element={<NodesPage latestNodeStatus={latestNodeStatus} />} />
              <Route path="/telemetry" element={<TelemetryPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/experiments" element={<ExperimentsPage />} />
              <Route
                path="/simulator"
                element={<SimulatorPage latestTelemetry={latestTelemetry} />}
              />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;

