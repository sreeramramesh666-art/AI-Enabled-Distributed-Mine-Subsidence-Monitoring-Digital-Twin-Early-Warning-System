import React from 'react';
import { AlertTriangle, AlertCircle, Eye, CheckCircle2, HelpCircle, Wifi, WifiOff, Clock, Sparkles, Cpu } from 'lucide-react';

export function StatusBadge({ status, type = 'severity' }) {
  if (!status) return null;
  const s = String(status).toUpperCase();

  if (type === 'source') {
    if (s.includes('SIMULAT')) {
      return (
        <span
          className="badge"
          style={{
            backgroundColor: 'rgba(217, 119, 6, 0.2)',
            color: '#fbbf24',
            border: '1px solid #d97706',
            fontSize: '0.72rem',
            letterSpacing: '0.04em',
            fontWeight: 700
          }}
        >
          <Sparkles size={11} /> SYNTHETIC SIMULATOR
        </span>
      );
    }
    return (
      <span
        className="badge"
        style={{
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          color: '#38bdf8',
          border: '1px solid #0284c7',
          fontSize: '0.72rem',
          letterSpacing: '0.04em',
          fontWeight: 700
        }}
      >
        <Cpu size={11} /> PHYSICAL SENSOR ({s})
      </span>
    );
  }

  if (type === 'connectivity') {
    if (s === 'ONLINE') {
      return (
        <span className="badge badge-normal" style={{ fontSize: '0.72rem' }}>
          <Wifi size={12} /> Online
        </span>
      );
    }
    if (s === 'STALE') {
      return (
        <span className="badge badge-warning" style={{ fontSize: '0.72rem' }}>
          <Clock size={12} /> Stale
        </span>
      );
    }
    return (
      <span className="badge badge-unreliable" style={{ fontSize: '0.72rem' }}>
        <WifiOff size={12} /> Offline
      </span>
    );
  }

  // Severity type
  switch (s) {
    case 'CRITICAL':
      return (
        <span className="badge badge-critical">
          <AlertCircle size={13} /> Critical
        </span>
      );
    case 'WARNING':
      return (
        <span className="badge badge-warning">
          <AlertTriangle size={13} /> Warning
        </span>
      );
    case 'WATCH':
      return (
        <span className="badge badge-watch">
          <Eye size={13} /> Watch
        </span>
      );
    case 'DATA_UNRELIABLE':
      return (
        <span className="badge badge-unreliable">
          <HelpCircle size={13} /> Data Unreliable
        </span>
      );
    case 'NORMAL':
    default:
      return (
        <span className="badge badge-normal">
          <CheckCircle2 size={13} /> Normal
        </span>
      );
  }
}

