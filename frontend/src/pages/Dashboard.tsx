import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { DeviceCard } from '@/components/DeviceCard';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';
import { playersApi, healthApi, authApi } from '@/api/client';
import type { Player } from '@/types';

export const Dashboard: React.FC = () => {
  const { authStatus, deviceFlow, startAuth } = useAuth();
  const [players, setPlayers] = useState<Player[]>([]);
  const [mqttStatus, setMqttStatus] = useState<string>('Unknown');
  const [mqttConnected, setMqttConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [environment, setEnvironment] = useState('Live');
  const [showMqttLog, setShowMqttLog] = useState(false);

  useEffect(() => {
    loadEnvironment();
  }, []);

  useEffect(() => {
    if (authStatus?.authenticated) {
      loadPlayers();
      checkMqttStatus();
      loadMqttEvents();

      // Poll for updates every 10 seconds
      const interval = setInterval(() => {
        loadPlayers();
        checkMqttStatus();
        loadMqttEvents();
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [authStatus?.authenticated]);

  const loadEnvironment = async () => {
    try {
      const response = await healthApi.check();
      setEnvironment(response.data.environment || 'unknown');
      // Also set MQTT status from health check
      setMqttConnected(response.data.mqtt_enabled || false);
      setMqttStatus(response.data.mqtt_enabled ? 'Connected' : 'Disconnected');
    } catch (error) {
      console.error('Failed to load environment:', error);
      setEnvironment('unknown');
      setMqttConnected(false);
      setMqttStatus('Disconnected');
    }
  };

  const loadPlayers = async () => {
    try {
      const response = await playersApi.getAll();
      setPlayers(response.data);
    } catch (error) {
      console.error('Failed to load players:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkMqttStatus = async () => {
    try {
      const response = await healthApi.check();
      setMqttConnected(response.data.mqtt_enabled || false);
      setMqttStatus(response.data.mqtt_enabled ? 'Connected' : 'Disconnected');
    } catch (error) {
      setMqttStatus('Disconnected');
      setMqttConnected(false);
    }
  };

  const loadMqttEvents = async () => {
    // MQTT events endpoint not yet implemented in backend
    // Placeholder for future implementation
    // Will be used when MQTT events API is available
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
      window.location.href = '/';
    } catch (error) {
      console.error('Failed to logout:', error);
      // Force logout on frontend even if API fails
      window.location.href = '/';
    }
  };

  const handlePlayerCommand = async (playerId: string, command: string) => {
    try {
      await playersApi.sendCommand(playerId, command);
      // Refresh players after command
      setTimeout(loadPlayers, 1000);
    } catch (error) {
      console.error('Failed to send command:', error);
    }
  };

  // Show auth prompt if not authenticated
  if (!authStatus?.authenticated) {
    return (
      <div className="flex-1">
        <Header title="Dashboard" subtitle="Connect your Yoto account to get started" />
        <div className="p-6">
          <Card>
            <div className="text-center space-y-6 py-8">
              <div className="text-6xl">🔐</div>
              <h3 className="text-2xl font-semibold">Connect Your Yoto Account</h3>
              <p className="text-gray-600 max-w-md mx-auto">
                To access your Yoto players, please authenticate with your Yoto account using device flow.
              </p>

              {deviceFlow ? (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
                    <p className="font-medium mb-2">1. Go to:</p>
                    <a
                      href={deviceFlow.verification_uri}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-700 underline text-lg"
                    >
                      {deviceFlow.verification_uri}
                    </a>
                    <p className="font-medium mt-4 mb-2">2. Enter this code:</p>
                    <div className="text-3xl font-bold text-primary-600 tracking-wider">
                      {deviceFlow.user_code}
                    </div>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-gray-600">
                    <div className="animate-spin w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full" />
                    <span>Waiting for authorization...</span>
                  </div>
                </div>
              ) : (
                <Button onClick={startAuth} size="lg">
                  🔑 Connect Yoto Account
                </Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <Header title="Dashboard" subtitle="Overview of your Yoto Smart Stream system" />

      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">📱</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">{players.length}</h3>
                <p className="text-gray-600">Connected Players</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className={`text-4xl ${mqttConnected ? 'animate-pulse' : 'opacity-50'}`}>
                🔌
              </div>
              <div>
                <h3 className={`text-3xl font-bold ${mqttConnected ? 'text-green-600' : 'text-red-600'}`}>
                  {mqttStatus}
                </h3>
                <p className="text-gray-600">MQTT Status</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className="text-4xl">🌍</div>
              <div>
                <h3 className="text-3xl font-bold text-gray-900">{environment}</h3>
                <p className="text-gray-600">Environment</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Players List */}
        <div>
          <h3 className="text-xl font-semibold mb-4">Connected Players</h3>
          {loading ? (
            <p className="text-gray-600">Loading players...</p>
          ) : players.length === 0 ? (
            <Card>
              <p className="text-center text-gray-600 py-8">
                No players found. Make sure your Yoto devices are online and connected to your account.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {players.map((player) => (
                <DeviceCard
                  key={player.id}
                  player={player}
                  onCommand={(cmd) => handlePlayerCommand(player.id, cmd)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        {authStatus?.authenticated && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Quick Actions</h3>
            <Card>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Button
                  variant="secondary"
                  onClick={() => window.location.href = '/streams'}
                  className="flex flex-col items-center justify-center p-4 h-auto"
                >
                  <span className="text-3xl mb-2">✨</span>
                  <span className="text-sm">Manage Streams</span>
                </Button>
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
                  onClick={() => window.location.href = '/library'}
                  className="flex flex-col items-center justify-center p-4 h-auto"
                >
                  <span className="text-3xl mb-2">📚</span>
                  <span className="text-sm">Yoto Library</span>
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setShowMqttLog(!showMqttLog)}
                  className="flex flex-col items-center justify-center p-4 h-auto"
                >
                  <span className="text-3xl mb-2">📡</span>
                  <span className="text-sm">{showMqttLog ? 'Hide' : 'Show'} Events</span>
                </Button>
                <Button
                  variant="danger"
                  onClick={handleLogout}
                  className="flex flex-col items-center justify-center p-4 h-auto"
                >
                  <span className="text-3xl mb-2">🚪</span>
                  <span className="text-sm">Logout</span>
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* MQTT Event Log */}
        {showMqttLog && authStatus?.authenticated && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Recent MQTT Events</h3>
            </div>
            <Card>
              <div className="text-center py-8">
                <div className="text-5xl mb-4">📡</div>
                <h3 className="text-lg font-semibold mb-2">MQTT Events</h3>
                <p className="text-gray-600">
                  MQTT event logging is coming soon. Events will be displayed here in real-time.
                </p>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};
