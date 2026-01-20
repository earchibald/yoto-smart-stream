import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AudioFileCard } from '@/components/AudioFileCard';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Modal } from '@/components/Modal';
import { audioApi } from '@/api/client';
import type { AudioFile } from '@/types';

interface TTSVoice {
  voice_id: string;
  name: string;
  description?: string;
}

export const AudioLibrary: React.FC = () => {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [loading, setLoading] = useState(true);

  // Upload Modal State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadFilename, setUploadFilename] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploading, setUploading] = useState(false);

  // TTS Modal State
  const [ttsModalOpen, setTtsModalOpen] = useState(false);
  const [ttsVoices, setTtsVoices] = useState<TTSVoice[]>([]);
  const [ttsFilename, setTtsFilename] = useState('');
  const [ttsVoice, setTtsVoice] = useState('');
  const [ttsText, setTtsText] = useState('');
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadAudioFiles();
    loadVoices();
  }, []);

  const loadAudioFiles = async () => {
    try {
      const response = await audioApi.getAll();
      setAudioFiles(response.data || []);
    } catch (error) {
      console.error('Failed to load audio files:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadVoices = async () => {
    try {
      const response = await audioApi.getVoices();
      setTtsVoices(response.data?.voices || []);
    } catch (error) {
      console.error('Failed to load TTS voices:', error);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (uploadFilename) formData.append('filename', uploadFilename);
      if (uploadDescription) formData.append('description', uploadDescription);

      await audioApi.upload(formData);
      setUploadModalOpen(false);
      setSelectedFile(null);
      setUploadFilename('');
      setUploadDescription('');
      await loadAudioFiles();
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateTTS = async () => {
    if (!ttsFilename || !ttsVoice || !ttsText) {
      alert('Please fill in all fields');
      return;
    }

    try {
      setGenerating(true);
      await audioApi.generateTTS({
        filename: ttsFilename,
        voice_id: ttsVoice,
        text: ttsText,
      });
      setTtsModalOpen(false);
      setTtsFilename('');
      setTtsVoice('');
      setTtsText('');
      await loadAudioFiles();
    } catch (error) {
      console.error('Failed to generate TTS:', error);
      alert('Failed to generate speech. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (filename: string) => {
    if (!confirm('Are you sure you want to delete this audio file?')) return;

    try {
      await audioApi.delete(filename);
      await loadAudioFiles();
    } catch (error) {
      console.error('Failed to delete file:', error);
      alert('Failed to delete file. Please try again.');
    }
  };

  return (
    <div className="flex-1">
      <Header
        title="Audio Library"
        subtitle="Manage your audio files and generate speech"
      />

      <div className="p-6 space-y-6">
        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setUploadModalOpen(true)}>
            📤 Upload Audio
          </Button>
          <Button variant="secondary" onClick={() => setTtsModalOpen(true)}>
            🎙️ Generate Speech (TTS)
          </Button>
          <Button variant="secondary" onClick={loadAudioFiles}>
            🔄 Refresh
          </Button>
        </div>

        {/* Audio Files Grid */}
        <div>
          <h3 className="text-xl font-semibold mb-4">Audio Files</h3>
          {loading ? (
            <p className="text-gray-600">Loading audio files...</p>
          ) : audioFiles.length === 0 ? (
            <Card>
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🎙️</div>
                <h3 className="text-xl font-semibold mb-2">No audio files yet</h3>
                <p className="text-gray-600 mb-6">
                  Upload audio files or generate speech to get started
                </p>
                <div className="flex gap-3 justify-center">
                  <Button onClick={() => setUploadModalOpen(true)}>
                    📤 Upload Audio
                  </Button>
                  <Button variant="secondary" onClick={() => setTtsModalOpen(true)}>
                    🎙️ Generate Speech
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {audioFiles.map((audio) => (
                <AudioFileCard
                  key={audio.id}
                  audio={audio}
                  onPlay={() => console.log('Play:', audio.id)}
                  onEdit={() => console.log('Edit:', audio.id)}
                  onDelete={() => handleDelete(audio.filename || audio.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      <Modal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Upload Audio File"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Audio File (MP3)
            </label>
            <input
              type="file"
              accept=".mp3,audio/mpeg"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-lg file:border-0
                file:text-sm file:font-semibold
                file:bg-primary-50 file:text-primary-700
                hover:file:bg-primary-100
                cursor-pointer"
            />
            <p className="text-sm text-gray-500 mt-1">
              Supported format: MP3 (other formats will be converted)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filename (without extension)
            </label>
            <input
              type="text"
              value={uploadFilename}
              onChange={(e) => setUploadFilename(e.target.value)}
              placeholder="e.g., my-audio"
              pattern="[a-zA-Z0-9\s_-]+"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-sm text-gray-500 mt-1">
              File will be saved as: <strong>{uploadFilename || 'my-audio'}.mp3</strong>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (optional)
            </label>
            <textarea
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              rows={3}
              placeholder="Add a description for this audio file..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {selectedFile && (
            <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
              <p>Selected: {selectedFile.name}</p>
              <p>Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={() => setUploadModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpload} isLoading={uploading} disabled={!selectedFile}>
              📤 Upload
            </Button>
          </div>
        </div>
      </Modal>

      {/* TTS Generation Modal */}
      <Modal
        isOpen={ttsModalOpen}
        onClose={() => setTtsModalOpen(false)}
        title="Generate Text-to-Speech Audio"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filename (without extension)
            </label>
            <input
              type="text"
              value={ttsFilename}
              onChange={(e) => setTtsFilename(e.target.value)}
              placeholder="e.g., my-story"
              pattern="[a-zA-Z0-9\s_-]+"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-sm text-gray-500 mt-1">
              File will be saved as: <strong>{ttsFilename || 'my-story'}.mp3</strong>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Voice
            </label>
            <select
              value={ttsVoice}
              onChange={(e) => setTtsVoice(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a voice...</option>
              {ttsVoices.map((voice) => (
                <option key={voice.voice_id} value={voice.voice_id}>
                  {voice.name}
                </option>
              ))}
            </select>
            {ttsVoice && ttsVoices.find(v => v.voice_id === ttsVoice)?.description && (
              <p className="text-sm text-gray-500 mt-1">
                {ttsVoices.find(v => v.voice_id === ttsVoice)?.description}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Text to convert to speech
            </label>
            <textarea
              value={ttsText}
              onChange={(e) => setTtsText(e.target.value)}
              rows={8}
              placeholder="Enter the text you want to convert to speech..."
              required
              minLength={1}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-sm text-gray-500 mt-1">
              {ttsText.length} characters
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={() => setTtsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleGenerateTTS}
              isLoading={generating}
              disabled={!ttsFilename || !ttsVoice || !ttsText}
            >
              🎙️ Generate Audio
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
