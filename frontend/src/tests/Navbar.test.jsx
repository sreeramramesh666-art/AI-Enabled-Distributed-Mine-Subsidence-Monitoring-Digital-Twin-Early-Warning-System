import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Navbar } from '../components/Navbar';

describe('Navbar', () => {
  it('renders title and live indicator when connected', () => {
    render(<Navbar isConnected={true} simulatorRunning={false} onToggleSimulator={() => {}} />);
    expect(screen.getByText(/mineguard/i)).toBeInTheDocument();
    expect(screen.getByText(/sih26025/i)).toBeInTheDocument();
    expect(screen.getByText(/live/i)).toBeInTheDocument();
    expect(screen.getByText(/simulator idle/i)).toBeInTheDocument();
  });

  it('renders disconnected and simulated pill when active', () => {
    render(<Navbar isConnected={false} simulatorRunning={true} onToggleSimulator={() => {}} />);
    expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    expect(screen.getByText(/simulating data/i)).toBeInTheDocument();
  });
});
