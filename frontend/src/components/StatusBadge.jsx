import React from 'react';
import { AlertTriangle, AlertCircle, Eye, CheckCircle2, HelpCircle, Wifi, WifiOff, Clock } from 'lucide-react';

export function StatusBadge({ status, type = 'severity' }) {
  if (!status) return null;
  const s = String(status).toUpperCase();

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
