export interface Player {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'unknown';
  online: boolean;
  battery?: number;
  charging?: boolean;
  currentTrack?: string;
  playbackState?: 'playing' | 'paused' | 'stopped';
}

export interface AudioFile {
  id: string;
  title: string;
  filename: string;
  duration?: number;
  fileSize?: number;
  uploadedAt?: string;
  transcription?: string;
}

export interface Card {
  id: string;
  title: string;
  description?: string;
  coverImageUrl?: string;
  audioFiles: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Stream {
  id: string;
  title: string;
  description?: string;
  tracks: AudioFile[];
  isActive: boolean;
  currentTrack?: number;
}

export interface MQTTEvent {
  id: string;
  timestamp: string;
  deviceId: string;
  eventType: string;
  payload: Record<string, any>;
}

export interface AuthStatus {
  authenticated: boolean;
  needsAuth: boolean;
  message?: string;
}

export interface DeviceAuthFlow {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}
