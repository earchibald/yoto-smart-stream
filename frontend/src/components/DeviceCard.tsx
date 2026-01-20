import React from 'react';
import type { Player } from '@/types';
import { Card } from './Card';

interface DeviceCardProps {
  player: Player;
  onCommand?: (command: string) => void;
}

export const DeviceCard: React.FC<DeviceCardProps> = ({ player, onCommand }) => {
  const getStatusColor = () => {
    if (!player.online) return 'bg-red-500';
    if (player.playbackState === 'playing') return 'bg-green-500';
    return 'bg-yellow-500';
  };

  const getStatusText = () => {
    if (!player.online) return 'Offline';
    if (player.playbackState === 'playing') return 'Playing';
    if (player.playbackState === 'paused') return 'Paused';
    return 'Idle';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
            <h3 className="text-lg font-semibold text-gray-900">{player.name}</h3>
          </div>
          <span className="text-sm text-gray-500">{getStatusText()}</span>
        </div>

        {/* Current Track */}
        {player.currentTrack && (
          <div className="text-sm text-gray-700">
            <p className="font-medium">Now Playing:</p>
            <p className="text-gray-600">{player.currentTrack}</p>
          </div>
        )}

        {/* Battery Status */}
        {player.battery !== undefined && (
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  player.battery > 20 ? 'bg-green-500' : 'bg-red-500'
                }`}
                style={{ width: `${player.battery}%` }}
              />
            </div>
            <span className="text-sm text-gray-600">{player.battery}%</span>
            {player.charging && <span className="text-sm">⚡</span>}
          </div>
        )}

        {/* Controls */}
        {player.online && onCommand && (
          <div className="flex gap-2 pt-2">
            <button
              onClick={() => onCommand('pause')}
              className="flex-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm font-medium"
              disabled={player.playbackState !== 'playing'}
            >
              ⏸️ Pause
            </button>
            <button
              onClick={() => onCommand('play')}
              className="flex-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm font-medium"
              disabled={player.playbackState === 'playing'}
            >
              ▶️ Play
            </button>
            <button
              onClick={() => onCommand('skip')}
              className="flex-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm font-medium"
            >
              ⏭️ Skip
            </button>
          </div>
        )}
      </div>
    </Card>
  );
};
