import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';
import { cardsApi } from '@/api/client';
import type { Card as YotoCard } from '@/types';

export const Library: React.FC = () => {
  const { authStatus } = useAuth();
  const [cards, setCards] = useState<YotoCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authStatus?.authenticated) {
      loadLibrary();
    } else {
      setLoading(false);
    }
  }, [authStatus?.authenticated]);

  const loadLibrary = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await cardsApi.getAll();
      // API returns { cards: [...] } format
      setCards(response.data?.cards || []);
    } catch (err: any) {
      console.error('Failed to load library:', err);
      setError(err.response?.data?.detail || 'Failed to load your Yoto library');
    } finally {
      setLoading(false);
    }
  };

  if (!authStatus?.authenticated) {
    return (
      <div className="flex-1">
        <Header
          title="Yoto Library"
          subtitle="Browse your Yoto cards and collections"
        />
        <div className="p-6">
          <Card>
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🔒</div>
              <h3 className="text-xl font-semibold mb-2">Authentication Required</h3>
              <p className="text-gray-600 mb-6">
                Please connect your Yoto account from the Dashboard to view your library.
              </p>
              <Button onClick={() => window.location.href = '/'}>
                Go to Dashboard
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <Header
        title="Yoto Library"
        subtitle="Browse your Yoto cards and collections"
      />

      <div className="p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">📚</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">{cards.length}</h3>
                <p className="text-gray-600">Total Cards</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">🎵</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">
                  {cards.filter(c => c.audioFiles && c.audioFiles.length > 0).length}
                </h3>
                <p className="text-gray-600">With Audio</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">✨</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">
                  {cards.filter(c => c.title?.toLowerCase().includes('playlist')).length}
                </h3>
                <p className="text-gray-600">Playlists</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Cards Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold">Your Cards</h3>
            <Button variant="secondary" onClick={loadLibrary}>
              🔄 Refresh
            </Button>
          </div>

          {loading ? (
            <Card>
              <p className="text-center text-gray-600 py-8">Loading your Yoto library...</p>
            </Card>
          ) : error ? (
            <Card>
              <div className="text-center py-8">
                <div className="text-5xl mb-4">⚠️</div>
                <h3 className="text-lg font-semibold mb-2">Failed to Load Library</h3>
                <p className="text-gray-600 mb-4">{error}</p>
                <Button onClick={loadLibrary}>Try Again</Button>
              </div>
            </Card>
          ) : cards.length === 0 ? (
            <Card>
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📚</div>
                <h3 className="text-xl font-semibold mb-2">No Cards Found</h3>
                <p className="text-gray-600">
                  Your Yoto library appears to be empty. Add some cards from the Yoto app!
                </p>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {cards.map((card) => (
                <Card key={card.id}>
                  <div className="space-y-3">
                    {card.coverImageUrl && (
                      <img
                        src={card.coverImageUrl}
                        alt={card.title}
                        className="w-full h-48 object-cover rounded-lg"
                      />
                    )}
                    <div>
                      <h4 className="font-semibold text-gray-900 line-clamp-2">
                        {card.title}
                      </h4>
                      {card.description && (
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {card.description}
                        </p>
                      )}
                    </div>
                    {card.audioFiles && card.audioFiles.length > 0 && (
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span>🎵</span>
                        <span>{card.audioFiles.length} track{card.audioFiles.length !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
