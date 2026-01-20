# Yoto Smart Stream Frontend

React + TypeScript frontend for Yoto Smart Stream application.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Vitest** - Unit testing
- **Testing Library** - Component testing

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The dev server will run on http://localhost:3000 and proxy API requests to the FastAPI backend on port 8000.

### Build

```bash
npm run build
```

This builds the production bundle to `../yoto_smart_stream/static/dist/`.

### Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

### Linting

```bash
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API client and endpoints
│   ├── components/    # Reusable UI components
│   ├── contexts/      # React contexts (Auth, etc.)
│   ├── hooks/         # Custom React hooks
│   ├── pages/         # Page components
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions
│   ├── test/          # Test setup and utilities
│   ├── App.tsx        # Main app component
│   ├── main.tsx       # Entry point
│   └── index.css      # Global styles
├── public/            # Static assets
├── index.html         # HTML template
├── vite.config.ts     # Vite configuration
├── tsconfig.json      # TypeScript configuration
├── vitest.config.ts   # Vitest configuration
└── tailwind.config.js # Tailwind CSS configuration
```

## Components

### Layout Components
- **Sidebar** - Navigation sidebar with menu items
- **Header** - Page header with title and actions
- **Layout** - Main layout wrapper

### UI Components
- **Button** - Customizable button with variants
- **Card** - Container card with optional header
- **Modal** - Modal dialog with ESC key support
- **DeviceCard** - Display Yoto player status and controls
- **AudioFileCard** - Display audio file information
- **MQTTEventLog** - Display MQTT events in real-time

### Pages
- **Dashboard** - Main dashboard with player overview
- **Streams** - Manage smart streams
- **Library** - Browse Yoto library
- **AudioLibrary** - Manage audio files
- **Admin** - System administration

## Testing Strategy

- **Unit tests** for all components
- **Integration tests** for API calls
- **E2E tests** with Playwright (separate)
- Target coverage: >70%

## Design Principles

- **Modal dialogs close with ESC key**
- **Responsive design** for mobile and desktop
- **Accessible components** following WCAG guidelines
- **Type-safe** with TypeScript throughout

## API Integration

The frontend communicates with the FastAPI backend through the `/api` prefix:

- `/api/health` - Health checks
- `/api/auth/*` - Yoto OAuth authentication
- `/api/players/*` - Player management
- `/api/media/*` - Audio file management
- `/api/cards/*` - Card management
- `/api/streams/*` - Stream management

See `src/api/client.ts` for full API documentation.
