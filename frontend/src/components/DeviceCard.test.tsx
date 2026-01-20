import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DeviceCard } from '@/components/DeviceCard';
import type { Player } from '@/types';

describe('DeviceCard Component', () => {
  const mockPlayer: Player = {
    id: 'player-1',
    name: 'Living Room Yoto',
    status: 'online',
    online: true,
    battery: 75,
    charging: false,
    currentTrack: 'Story Time Vol 1',
    playbackState: 'playing',
  };

  it('renders player information', () => {
    render(<DeviceCard player={mockPlayer} />);
    expect(screen.getByText('Living Room Yoto')).toBeInTheDocument();
    expect(screen.getByText('Playing')).toBeInTheDocument();
    expect(screen.getByText('Story Time Vol 1')).toBeInTheDocument();
  });

  it('displays battery status', () => {
    render(<DeviceCard player={mockPlayer} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('shows charging indicator when charging', () => {
    const chargingPlayer = { ...mockPlayer, charging: true };
    render(<DeviceCard player={chargingPlayer} />);
    expect(screen.getByText('⚡')).toBeInTheDocument();
  });

  it('shows offline status for offline player', () => {
    const offlinePlayer = { ...mockPlayer, online: false, status: 'offline' as const };
    render(<DeviceCard player={offlinePlayer} />);
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });

  it('renders control buttons when online and onCommand is provided', () => {
    const onCommand = vi.fn();
    render(<DeviceCard player={mockPlayer} onCommand={onCommand} />);
    expect(screen.getByText('⏸️ Pause')).toBeInTheDocument();
    expect(screen.getByText('▶️ Play')).toBeInTheDocument();
    expect(screen.getByText('⏭️ Skip')).toBeInTheDocument();
  });

  it('does not render controls when offline', () => {
    const offlinePlayer = { ...mockPlayer, online: false, status: 'offline' as const };
    const onCommand = vi.fn();
    render(<DeviceCard player={offlinePlayer} onCommand={onCommand} />);
    expect(screen.queryByText('⏸️ Pause')).not.toBeInTheDocument();
  });

  it('disables pause button when not playing', () => {
    const pausedPlayer = { ...mockPlayer, playbackState: 'paused' as const };
    const onCommand = vi.fn();
    render(<DeviceCard player={pausedPlayer} onCommand={onCommand} />);
    const pauseButton = screen.getByText('⏸️ Pause').closest('button');
    expect(pauseButton).toBeDisabled();
  });

  it('disables play button when already playing', () => {
    const onCommand = vi.fn();
    render(<DeviceCard player={mockPlayer} onCommand={onCommand} />);
    const playButton = screen.getByText('▶️ Play').closest('button');
    expect(playButton).toBeDisabled();
  });
});
