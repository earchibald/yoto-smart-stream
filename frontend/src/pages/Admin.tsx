import React from 'react';
import { Header } from '@/components/Header';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';

export const Admin: React.FC = () => {
  const { authStatus, logout } = useAuth();

  return (
    <div className="flex-1">
      <Header
        title="Admin"
        subtitle="System settings and configuration"
      />

      <div className="p-6 space-y-6">
        {/* Authentication */}
        <Card title="Authentication">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Yoto Account Status</p>
                <p className="text-sm text-gray-600">
                  {authStatus?.authenticated ? 'Connected' : 'Not connected'}
                </p>
              </div>
              {authStatus?.authenticated && (
                <Button variant="danger" onClick={logout}>
                  Disconnect
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* System Info */}
        <Card title="System Information">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Version:</span>
              <span className="font-medium">0.1.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Environment:</span>
              <span className="font-medium">Production</span>
            </div>
          </div>
        </Card>

        {/* MQTT Settings */}
        <Card title="MQTT Settings">
          <p className="text-gray-600">MQTT event monitoring is active</p>
        </Card>
      </div>
    </div>
  );
};
