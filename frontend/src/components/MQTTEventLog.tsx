import React from 'react';
import type { MQTTEvent } from '@/types';
import { Card } from './Card';

interface MQTTEventLogProps {
  events: MQTTEvent[];
  maxEvents?: number;
  title?: string;
}

export const MQTTEventLog: React.FC<MQTTEventLogProps> = ({
  events,
  maxEvents = 50,
  title = 'MQTT Event Log',
}) => {
  const displayEvents = events.slice(0, maxEvents);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const getEventTypeColor = (eventType: string) => {
    const colors: Record<string, string> = {
      connected: 'text-green-600 bg-green-50',
      disconnected: 'text-red-600 bg-red-50',
      button: 'text-blue-600 bg-blue-50',
      playback: 'text-purple-600 bg-purple-50',
      battery: 'text-yellow-600 bg-yellow-50',
      default: 'text-gray-600 bg-gray-50',
    };

    return colors[eventType] || colors.default;
  };

  return (
    <Card title={title}>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {displayEvents.length === 0 ? (
          <p className="text-center text-gray-500 py-8">No events yet</p>
        ) : (
          displayEvents.map((event) => (
            <div
              key={event.id}
              className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <span className="text-xs text-gray-500 w-20 flex-shrink-0">
                {formatTimestamp(event.timestamp)}
              </span>
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${getEventTypeColor(
                  event.eventType
                )}`}
              >
                {event.eventType}
              </span>
              <div className="flex-1 text-sm text-gray-700">
                <p className="font-medium">{event.deviceId}</p>
                <pre className="text-xs text-gray-600 mt-1 overflow-x-auto">
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
