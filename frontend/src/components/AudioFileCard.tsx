import React from 'react';
import type { AudioFile } from '@/types';
import { Card } from './Card';

interface AudioFileCardProps {
  audio: AudioFile;
  onPlay?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export const AudioFileCard: React.FC<AudioFileCardProps> = ({
  audio,
  onPlay,
  onEdit,
  onDelete,
}) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds || seconds <= 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes <= 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <div className="space-y-4">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center text-4xl">
            🎵
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 truncate">{audio.title}</h3>
          <p className="text-sm text-gray-500 mt-1">{audio.filename}</p>
        </div>

        {/* Metadata */}
        <div className="flex justify-between text-sm text-gray-600 border-t pt-3">
          <span>{audio.duration ? formatDuration(audio.duration) : 'Unknown'}</span>
          <span>{audio.fileSize ? formatFileSize(audio.fileSize) : 'Unknown'}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {onPlay && (
            <button
              onClick={onPlay}
              className="flex-1 px-3 py-2 bg-primary-600 text-white hover:bg-primary-700 rounded-lg transition-colors text-sm font-medium"
            >
              ▶️ Play
            </button>
          )}
          {onEdit && (
            <button
              onClick={onEdit}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
            >
              ✏️
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="px-3 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors text-sm"
            >
              🗑️
            </button>
          )}
        </div>

        {/* Transcription */}
        {audio.transcription && (
          <div className="text-xs text-gray-500 border-t pt-3">
            <p className="font-medium mb-1">Transcription:</p>
            <p className="line-clamp-3">{audio.transcription}</p>
          </div>
        )}
      </div>
    </Card>
  );
};
