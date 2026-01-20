import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';
import { healthApi, authApi } from '@/api/client';

interface SystemInfo {
  version: string;
  environment: string;
  mqtt_enabled: boolean;
  audio_files: number;
}

export const Admin: React.FC = () => {
  const { authStatus } = useAuth();
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSystemInfo();
  }, []);

  const loadSystemInfo = async () => {
    try {
      const response = await healthApi.check();
      setSystemInfo(response.data);
    } catch (error) {
      console.error('Failed to load system info:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
      window.location.href = '/';
    } catch (error) {
      console.error('Failed to logout:', error);
      window.location.href = '/';
    }
  };

  return (
    <div className="flex-1">
      <Header
        title="Admin"
        subtitle="System settings and configuration"
      />

      <div className="p-6 space-y-6">
        {/* System Information */}
        <Card title="System Information">
          {loading ? (
            <p className="text-gray-600">Loading...</p>
          ) : systemInfo ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-gray-200">
                <span className="text-gray-600">Version:</span>
                <span className="font-medium">{systemInfo.version}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-200">
                <span className="text-gray-600">Environment:</span>
                <span className="font-medium">{systemInfo.environment}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-200">
                <span className="text-gray-600">MQTT Status:</span>
                <span className={`font-medium ${systemInfo.mqtt_enabled ? 'text-green-600' : 'text-red-600'}`}>
                  {systemInfo.mqtt_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Audio Files:</span>
                <span className="font-medium">{systemInfo.audio_files}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-600">Failed to load system information</p>
          )}
        </Card>

        {/* User Management */}
        <Card title="User Management">
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2">Yoto Account Authentication</h4>
              <div className="space-y-2 text-sm text-blue-800">
                <div className="flex justify-between py-1">
                  <span>Status:</span>
                  <span className={`font-medium ${authStatus?.authenticated ? 'text-green-700' : 'text-gray-600'}`}>
                    {authStatus?.authenticated ? '✓ Authenticated' : 'Not authenticated'}
                  </span>
                </div>
                {systemInfo && (
                  <div className="flex justify-between py-1">
                    <span>Environment:</span>
                    <span className="font-medium">{systemInfo.environment}</span>
                  </div>
                )}
              </div>
            </div>

            {authStatus?.authenticated && (
              <div className="flex gap-3">
                <Button
                  variant="danger"
                  onClick={handleLogout}
                  className="flex items-center gap-2"
                >
                  <span>🚪</span>
                  <span>Logout</span>
                </Button>
              </div>
            )}

            {!authStatus?.authenticated && (
              <div className="text-center py-6">
                <p className="text-gray-600 mb-4">No user is currently authenticated.</p>
                <Button onClick={() => window.location.href = '/'}>
                  Go to Dashboard to Login
                </Button>
              </div>
            )}
          </div>
        </Card>

        {/* Authentication */}
        <Card title="Yoto Account Details">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Account Status</p>
                <p className="text-sm text-gray-600 mt-1">
                  {authStatus?.authenticated ? (
                    <span className="text-green-600">✓ Connected to Yoto</span>
                  ) : (
                    <span className="text-gray-500">Not connected</span>
                  )}
                </p>
              </div>
              {authStatus?.authenticated && (
                <Button variant="danger" onClick={handleLogout}>
                  Disconnect Account
                </Button>
              )}
            </div>
            {authStatus?.authenticated && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> Disconnecting will revoke access to your Yoto devices and library.
                  You'll need to re-authenticate to use the system.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* MQTT Settings */}
        <Card title="MQTT Configuration">
          <div className="space-y-3">
            <p className="text-gray-600">
              MQTT event monitoring provides real-time updates from your Yoto devices.
            </p>
            <div className="flex items-center justify-between py-2">
              <span className="font-medium">Status:</span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                systemInfo?.mqtt_enabled
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {systemInfo?.mqtt_enabled ? 'Active' : 'Inactive'}
              </span>
            </div>
            {systemInfo?.mqtt_enabled && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-green-800">
                  ✓ MQTT events are being monitored. View recent events on the Dashboard.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Actions */}
        <Card title="System Actions">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button
              variant="secondary"
              onClick={loadSystemInfo}
              className="flex items-center justify-center gap-2"
            >
              <span>🔄</span>
              <span>Refresh System Info</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => window.location.href = '/'}
              className="flex items-center justify-center gap-2"
            >
              <span>🏠</span>
              <span>Return to Dashboard</span>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
