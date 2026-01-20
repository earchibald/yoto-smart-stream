import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AudioFileCard } from '@/components/AudioFileCard';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import { Modal } from '@/components/Modal';
import { audioApi } from '@/api/client';
import type { AudioFile } from '@/types';

export const AudioLibrary: React.FC = () => {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadAudioFiles();
  }, []);

  const loadAudioFiles = async () => {
    try {
      const response = await audioApi.getAll();
      setAudioFiles(response.data);
    } catch (error) {
      console.error('Failed to load audio files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      await audioApi.upload(selectedFile);
      setUploadModalOpen(false);
      setSelectedFile(null);
      await loadAudioFiles();
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this audio file?')) return;

    try {
      await audioApi.delete(id);
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
        subtitle="Manage your audio files"
        actions={
          <Button onClick={() => setUploadModalOpen(true)}>
            📤 Upload Audio
          </Button>
        }
      />

      <div className="p-6">
        {loading ? (
          <p className="text-gray-600">Loading audio files...</p>
        ) : audioFiles.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🎙️</div>
              <h3 className="text-xl font-semibold mb-2">No audio files yet</h3>
              <p className="text-gray-600 mb-6">
                Upload your first audio file to get started
              </p>
              <Button onClick={() => setUploadModalOpen(true)}>
                📤 Upload Audio
              </Button>
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
                onDelete={() => handleDelete(audio.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <Modal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Upload Audio File"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUploadModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpload} isLoading={uploading} disabled={!selectedFile}>
              Upload
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Audio File
            </label>
            <input
              type="file"
              accept="audio/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-lg file:border-0
                file:text-sm file:font-semibold
                file:bg-primary-50 file:text-primary-700
                hover:file:bg-primary-100
                cursor-pointer"
            />
          </div>
          {selectedFile && (
            <div className="text-sm text-gray-600">
              <p>Selected: {selectedFile.name}</p>
              <p>Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};
