import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { audioApi } from '@/api/client';
import type { AudioFile } from '@/types';

interface StreamQueue {
  name: string;
  files: string[];
  created_at: string;
}

export const Streams: React.FC = () => {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [queues] = useState<StreamQueue[]>([]);
  const [loading, setLoading] = useState(true);
  const [publicUrl, setPublicUrl] = useState('');

  useEffect(() => {
    loadData();
    // Get public URL from current location
    const url = window.location.origin;
    setPublicUrl(url);
  }, []);

  const loadData = async () => {
    try {
      const response = await audioApi.getAll();
      setAudioFiles(response.data || []);
    } catch (error) {
      console.error('Failed to load audio files:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1">
      <Header
        title="Smart Streams"
        subtitle="Create and manage dynamic audio streams"
      />

      <div className="p-6 space-y-6">
        {/* Public URL */}
        <Card title="Public Stream URL">
          <div className="space-y-3">
            <p className="text-gray-600">
              Access your streams from any Yoto device using this URL:
            </p>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-center justify-between">
              <code className="text-sm font-mono text-gray-800">
                {publicUrl}/streams/&#123;stream_name&#125;/stream.mp3
              </code>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(`${publicUrl}/streams/default/stream.mp3`);
                  alert('URL copied to clipboard!');
                }}
              >
                📋 Copy
              </Button>
            </div>
            <p className="text-sm text-gray-500">
              Replace &#123;stream_name&#125; with your stream name (e.g., "default", "bedtime", etc.)
            </p>
          </div>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">🎙️</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">{audioFiles.length}</h3>
                <p className="text-gray-600">Audio Files</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">📋</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">{queues.length}</h3>
                <p className="text-gray-600">Active Streams</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">✨</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">0</h3>
                <p className="text-gray-600">CYOA Stories</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Available Audio Files */}
        <div>
          <h3 className="text-xl font-semibold mb-4">Available Audio Files</h3>
          {loading ? (
            <Card>
              <p className="text-center text-gray-600 py-8">Loading audio files...</p>
            </Card>
          ) : audioFiles.length === 0 ? (
            <Card>
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🎙️</div>
                <h3 className="text-xl font-semibold mb-2">No Audio Files</h3>
                <p className="text-gray-600 mb-6">
                  Upload some audio files in the Audio Library to create streams.
                </p>
                <Button onClick={() => window.location.href = '/audio-library'}>
                  Go to Audio Library
                </Button>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {audioFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🎵</span>
                      <div>
                        <p className="font-medium">{file.title || file.filename}</p>
                        <p className="text-sm text-gray-500">
                          {file.duration ? `${Math.floor(file.duration / 60)}:${String(file.duration % 60).padStart(2, '0')}` : 'Unknown duration'}
                        </p>
                      </div>
                    </div>
                    <Button variant="secondary" size="sm">
                      Add to Stream
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Stream Scripter (Coming Soon) */}
        <Card title="Stream Scripter">
          <div className="text-center py-8">
            <div className="text-5xl mb-4">✨</div>
            <h3 className="text-lg font-semibold mb-2">Create Interactive Streams</h3>
            <p className="text-gray-600 mb-4">
              Build playlists and Choose Your Own Adventure stories with our Stream Scripter.
            </p>
            <p className="text-sm text-gray-500">
              This feature is coming soon! For now, you can create simple streams via the API.
            </p>
          </div>
        </Card>

        {/* Quick Actions */}
        <Card title="Quick Actions">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button
              variant="secondary"
              onClick={() => window.location.href = '/audio-library'}
              className="flex flex-col items-center justify-center p-4 h-auto"
            >
              <span className="text-3xl mb-2">🎙️</span>
              <span className="text-sm">Audio Library</span>
            </Button>
            <Button
              variant="secondary"
              onClick={loadData}
              className="flex flex-col items-center justify-center p-4 h-auto"
            >
              <span className="text-3xl mb-2">🔄</span>
              <span className="text-sm">Refresh</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => window.open('https://yoto.dev/docs', '_blank')}
              className="flex flex-col items-center justify-center p-4 h-auto"
            >
              <span className="text-3xl mb-2">📚</span>
              <span className="text-sm">API Docs</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => window.location.href = '/'}
              className="flex flex-col items-center justify-center p-4 h-auto"
            >
              <span className="text-3xl mb-2">🏠</span>
              <span className="text-sm">Dashboard</span>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
