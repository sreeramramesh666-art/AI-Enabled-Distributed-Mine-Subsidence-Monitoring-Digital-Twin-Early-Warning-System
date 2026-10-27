import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  Cpu,
  LineChart,
  Bell,
  TrendingUp,
  Sliders,
  FileText,
  Settings,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/map', label: 'GIS Map', icon: MapPin },
  { path: '/nodes', label: 'Nodes', icon: Cpu },
  { path: '/telemetry', label: 'Telemetry Explorer', icon: LineChart },
  { path: '/alerts', label: 'Alerts Centre', icon: Bell },
  { path: '/analytics', label: 'Analytics & Risk', icon: TrendingUp },
  { path: '/simulator', label: 'Simulator Control', icon: Sliders },
  { path: '/reports', label: 'Export & Reports', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ alertCount = 0 }) {
  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#0b0f19',
      borderRight: '1px solid #1e293b',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      height: 'calc(100vh - 60px)',
      position: 'sticky',
      top: '60px'
    }}>
      <nav style={{ padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.6rem 0.85rem',
                borderRadius: '6px',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: isActive ? '#38bdf8' : '#94a3b8',
                backgroundColor: isActive ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                borderLeft: isActive ? '3px solid #38bdf8' : '3px solid transparent',
                transition: 'all 0.15s ease'
              })}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Icon size={17} />
                <span>{item.label}</span>
              </div>
              {item.path === '/alerts' && alertCount > 0 && (
                <span style={{
                  backgroundColor: '#ef4444',
                  color: '#ffffff',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '0.1rem 0.45rem',
                  borderRadius: '9999px'
                }}>
                  {alertCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid #1e293b', fontSize: '0.72rem', color: '#64748b' }}>
        <div>SIH26025 Prototype</div>
        <div style={{ marginTop: '0.2rem' }}>Local-First Geotechnical Sentinel</div>
      </div>
    </aside>
  );
}
