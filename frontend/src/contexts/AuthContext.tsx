import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '@/api/client';
import type { AuthStatus, DeviceAuthFlow } from '@/types';

interface AuthContextType {
  authStatus: AuthStatus | null;
  deviceFlow: DeviceAuthFlow | null;
  loading: boolean;
  error: string | null;
  startAuth: () => Promise<void>;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [deviceFlow, setDeviceFlow] = useState<DeviceAuthFlow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = async () => {
    try {
      setLoading(true);
      const response = await authApi.getStatus();
      setAuthStatus(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to check authentication status');
      console.error('Auth check error:', err);
    } finally {
      setLoading(false);
    }
  };

  const startAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await authApi.startDeviceFlow();
      setDeviceFlow(response.data);

      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          await authApi.pollToken(response.data.device_code);
          // If successful, clear interval and refresh auth status
          clearInterval(pollInterval);
          setDeviceFlow(null);
          await checkAuth();
        } catch (err: any) {
          // Expected error while waiting for user authorization
          if (err.response?.status !== 400) {
            clearInterval(pollInterval);
            setError('Authentication failed');
            setDeviceFlow(null);
          }
        }
      }, response.data.interval * 1000);

      // Clear interval after expiration
      setTimeout(() => {
        clearInterval(pollInterval);
        if (deviceFlow) {
          setDeviceFlow(null);
          setError('Authentication timeout');
        }
      }, response.data.expires_in * 1000);
    } catch (err) {
      setError('Failed to start authentication flow');
      console.error('Auth start error:', err);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
      setAuthStatus({ authenticated: false, needsAuth: true });
      setDeviceFlow(null);
    } catch (err) {
      setError('Failed to logout');
      console.error('Logout error:', err);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        authStatus,
        deviceFlow,
        loading,
        error,
        startAuth,
        checkAuth,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
