import React from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';

export const Library: React.FC = () => {
  return (
    <div className="flex-1">
      <Header
        title="Yoto Library"
        subtitle="Browse your Yoto cards and collections"
      />

      <div className="p-6">
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold mb-2">Yoto Library</h3>
            <p className="text-gray-600">
              View and manage your Yoto cards and collections
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
