import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge', () => {
  it('renders CRITICAL badge correctly', () => {
    render(<StatusBadge status="CRITICAL" />);
    expect(screen.getByText(/critical/i)).toBeInTheDocument();
  });

  it('renders WARNING badge correctly', () => {
    render(<StatusBadge status="WARNING" />);
    expect(screen.getByText(/warning/i)).toBeInTheDocument();
  });

  it('renders ONLINE connectivity badge correctly', () => {
    render(<StatusBadge status="ONLINE" type="connectivity" />);
    expect(screen.getByText(/online/i)).toBeInTheDocument();
  });

  it('renders OFFLINE connectivity badge correctly', () => {
    render(<StatusBadge status="OFFLINE" type="connectivity" />);
    expect(screen.getByText(/offline/i)).toBeInTheDocument();
  });
});
