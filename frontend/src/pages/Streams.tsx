import React from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';

export const Streams: React.FC = () => {
  return (
    <div className="flex-1">
      <Header
        title="Smart Streams"
        subtitle="Create and manage dynamic audio streams"
      />

      <div className="p-6">
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">✨</div>
            <h3 className="text-xl font-semibold mb-2">Smart Streams</h3>
            <p className="text-gray-600">
              Coming soon - create dynamic playlists and interactive Choose Your Own Adventure experiences
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
