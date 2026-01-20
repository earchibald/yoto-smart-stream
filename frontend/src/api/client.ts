import axios from 'axios';
import type { Player, AudioFile, Card, Stream, AuthStatus, DeviceAuthFlow } from '@/types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth API
export const authApi = {
  getStatus: () => api.get<AuthStatus>('/auth/status'),
  startDeviceFlow: () => api.post<DeviceAuthFlow>('/auth/start'),
  pollToken: (deviceCode: string) => api.post('/auth/poll', { device_code: deviceCode }),
  logout: () => api.post('/auth/logout'),
};

// Players API
export const playersApi = {
  getAll: () => api.get<Player[]>('/players'),
  getById: (id: string) => api.get<Player>(`/players/${id}`),
  sendCommand: (id: string, command: string, params?: Record<string, any>) =>
    api.post(`/players/${id}/command`, { command, ...params }),
};

// Audio Library API
export const audioApi = {
  getAll: () => api.get<AudioFile[]>('/audio/list'),
  getById: (filename: string) => api.get<AudioFile>(`/audio/${filename}`),
  upload: (formData: FormData) => {
    return api.post<AudioFile>('/audio/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (filename: string) => api.delete(`/audio/${filename}`),
  getTranscript: (filename: string) => api.get(`/audio/${filename}/transcript`),
  transcribe: (filename: string) => api.post(`/audio/${filename}/transcribe`),

  // TTS
  getVoices: () => api.get<any>('/audio/tts/voices'),
  generateTTS: (data: { filename: string; voice_id: string; text: string }) =>
    api.post('/audio/generate-tts', data),

  // Audio stitching/editing
  stitchAudio: (data: any) => api.post('/audio/stitch', data),
  getStitchStatus: () => api.get('/audio/stitch/status'),
  cancelStitch: (taskId: string) => api.post(`/audio/stitch/${taskId}/cancel`),

  // Playlists
  createPlaylistFromAudio: (data: { audio_files: string[]; playlist_name: string }) =>
    api.post('/cards/create-playlist-from-audio', data),
};

// Cards API
export const cardsApi = {
  getAll: () => api.get<Card[]>('/cards'),
  getById: (id: string) => api.get<Card>(`/cards/${id}`),
  create: (card: Partial<Card>) => api.post<Card>('/cards', card),
  update: (id: string, card: Partial<Card>) => api.put<Card>(`/cards/${id}`, card),
  delete: (id: string) => api.delete(`/cards/${id}`),
};

// Streams API
export const streamsApi = {
  getAll: () => api.get<Stream[]>('/streams'),
  getById: (id: string) => api.get<Stream>(`/streams/${id}`),
  create: (stream: Partial<Stream>) => api.post<Stream>('/streams', stream),
  update: (id: string, stream: Partial<Stream>) => api.put<Stream>(`/streams/${id}`, stream),
  delete: (id: string) => api.delete(`/streams/${id}`),
  start: (id: string, playerId: string) => api.post(`/streams/${id}/start`, { player_id: playerId }),
  stop: (id: string) => api.post(`/streams/${id}/stop`),
};

// Health API
export const healthApi = {
  check: () => api.get('/health'),
  getMqttStatus: () => api.get<{ status: string; connected: boolean }>('/mqtt/status'),
};

// MQTT Events API
export const mqttApi = {
  getRecentEvents: (limit: number = 50) => api.get(`/mqtt/events?limit=${limit}`),
};

// System API
export const systemApi = {
  getVersion: () => api.get<{ version: string }>('/health'),
};

export default api;
