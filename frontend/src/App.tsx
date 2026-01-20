import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { Layout } from '@/components/Layout';
import { Dashboard } from '@/pages/Dashboard';
import { Streams } from '@/pages/Streams';
import { Library } from '@/pages/Library';
import { AudioLibrary } from '@/pages/AudioLibrary';
import { Admin } from '@/pages/Admin';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/streams" element={<Streams />} />
            <Route path="/library" element={<Library />} />
            <Route path="/audio" element={<AudioLibrary />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
