import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: '🏠' },
  { path: '/streams', label: 'Smart Streams', icon: '✨' },
  { path: '/library', label: 'Yoto Library', icon: '📚' },
  { path: '/audio', label: 'Audio Library', icon: '🎙️' },
  { path: '/admin', label: 'Admin', icon: '⚙️' },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <nav className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold">🎵 Yoto Stream</h1>
      </div>

      <ul className="flex-1">
        {navItems.map((item) => (
          <li key={item.path}>
            <Link
              to={item.path}
              className={`flex items-center px-6 py-3 hover:bg-gray-800 transition-colors ${
                location.pathname === item.path
                  ? 'bg-gray-800 border-l-4 border-primary-500'
                  : ''
              }`}
            >
              <span className="mr-3 text-xl">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>

      <div className="p-6 border-t border-gray-800">
        <p className="text-sm text-gray-400">Version 0.1.0</p>
      </div>
    </nav>
  );
};
