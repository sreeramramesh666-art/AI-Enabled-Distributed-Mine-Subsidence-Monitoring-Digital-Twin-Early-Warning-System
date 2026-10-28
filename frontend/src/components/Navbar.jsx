import React from 'react';
import { ShieldAlert, Activity, Cpu, Radio, Sparkles } from 'lucide-react';

export function Navbar({ isConnected, simulatorRunning, onToggleSimulator }) {
  return (
    <header style={{
      height: '60px',
      backgroundColor: '#0f172a',
      borderBottom: '1px solid #1e293b',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 1.5rem',
      position: 'sticky',
      top: 0,
      zIndex: 1000
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '6px',
          background: 'linear-gradient(135deg, #0284c7, #0f766e)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff'
        }}>
          <ShieldAlert size={18} />
        </div>
        <div>
          <span style={{ fontWeight: 700, fontSize: '1.05rem', letterSpacing: '-0.02em', color: '#f8fafc' }}>
            MineGuard<span style={{ color: '#38bdf8' }}>-AI</span>
          </span>
          <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            SIH26025
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Simulator status pill */}
        {simulatorRunning ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            backgroundColor: 'rgba(234, 179, 8, 0.12)',
            border: '1px solid #ca8a04',
            borderRadius: '9999px',
            padding: '0.2rem 0.75rem',
            fontSize: '0.75rem',
            color: '#facc15'
          }}>
            <Sparkles size={13} className="animate-pulse" />
            <span style={{ fontWeight: 600 }}>SIMULATING DATA</span>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            backgroundColor: 'rgba(51, 65, 85, 0.3)',
            border: '1px solid #334155',
            borderRadius: '9999px',
            padding: '0.2rem 0.75rem',
            fontSize: '0.75rem',
            color: '#94a3b8'
          }}>
            <Cpu size={13} />
            <span>Simulator Idle</span>
          </div>
        )}

        {/* Live WebSocket connection indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.75rem',
          color: isConnected ? '#4ade80' : '#f87171'
        }}>
          <Radio size={14} />
          <span>{isConnected ? 'LIVE' : 'DISCONNECTED'}</span>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#22c55e' : '#ef4444',
            display: 'inline-block'
          }} />
        </div>
      </div>
    </header>
  );
}

