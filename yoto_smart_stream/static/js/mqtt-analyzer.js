/**
 * MQTT Analyzer Dashboard
 * Displays real-time device state, MQTT events, and stream request correlation
 */

let mqttAutoRefreshInterval = null;

async function openMQTTAnalyzer() {
    document.getElementById('mqttAnalyzerModal').style.display = 'block';
    await refreshMQTTData();
}

function closeMQTTAnalyzer() {
    document.getElementById('mqttAnalyzerModal').style.display = 'none';
    if (mqttAutoRefreshInterval) {
        clearInterval(mqttAutoRefreshInterval);
        mqttAutoRefreshInterval = null;
    }
}

async function refreshMQTTData() {
    try {
        // Fetch MQTT analyzer data
        const response = await fetch('/api/mqtt/analyzer');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        // Update device state
        updateDeviceState(result.data);

        // Update recent events
        updateRecentEvents(result.recent_events);

        // Update stream requests
        updateStreamRequests(result.recent_stream_requests);
    } catch (error) {
        console.error('Failed to refresh MQTT data:', error);
        updateErrorState('Failed to load MQTT data: ' + error.message);
    }
}

function updateDeviceState(data) {
    const stateBox = document.getElementById('deviceStateSummary');

    if (!data.current_device_state) {
        stateBox.innerHTML = '<p class="info">No device state available yet. Waiting for MQTT events...</p>';
        return;
    }

    const state = data.current_device_state;
    const timestamp = new Date(state.timestamp).toLocaleTimeString();

    let html = `
        <div class="device-state-grid">
            <div class="state-item">
                <span class="label">Last Update</span>
                <span class="value">${timestamp}</span>
            </div>
            <div class="state-item">
                <span class="label">Playback Status</span>
                <span class="value status-${state.playback_status}">${state.playback_status || 'unknown'}</span>
            </div>
            <div class="state-item">
                <span class="label">Volume</span>
                <span class="value">${state.volume}/${state.volume_max}</span>
            </div>
            <div class="state-item">
                <span class="label">Streaming</span>
                <span class="value">${state.streaming ? '✓ Yes' : '✗ No'}</span>
            </div>
            <div class="state-item">
                <span class="label">Card ID</span>
                <span class="value">${state.card_id || 'none'}</span>
            </div>
            <div class="state-item">
                <span class="label">Playback Wait</span>
                <span class="value">${state.playback_wait ? '✓ Waiting' : '✗ No'}</span>
            </div>
            <div class="state-item">
                <span class="label">Sleep Timer</span>
                <span class="value">${state.sleep_timer_active ? '✓ Active' : '✗ Off'}</span>
            </div>
            <div class="state-item">
                <span class="label">Repeat All</span>
                <span class="value">${state.repeat_all ? '✓ On' : '✗ Off'}</span>
            </div>
        </div>
    `;

    stateBox.innerHTML = html;
}

function updateRecentEvents(events) {
    const eventsList = document.getElementById('recentEventsList');

    if (!events || events.length === 0) {
        eventsList.innerHTML = '<p class="info">No MQTT events yet</p>';
        return;
    }

    let html = '<div class="events-timeline">';

    events.reverse().forEach((event, index) => {
        const timestamp = new Date(event.timestamp).toLocaleTimeString();
        const icon = getEventIcon(event);

        html += `
            <div class="timeline-event">
                <div class="event-time">${timestamp}</div>
                <div class="event-content">
                    <div class="event-icon">${icon}</div>
                    <div class="event-details">
                        <p><strong>Status:</strong> ${event.playback_status || 'unknown'}</p>
                        <p><strong>Volume:</strong> ${event.volume}/${event.volume_max}</p>
                        <p><strong>Card:</strong> ${event.card_id || 'none'}</p>
                        ${event.button_left_clicked ? '<p class="button-event">⬅️ Left button clicked</p>' : ''}
                        ${event.button_right_clicked ? '<p class="button-event">➡️ Right button clicked</p>' : ''}
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    eventsList.innerHTML = html;
}

function updateStreamRequests(requests) {
    const requestsList = document.getElementById('streamRequestsList');

    if (!requests || requests.length === 0) {
        requestsList.innerHTML = '<p class="info">No stream requests yet</p>';
        return;
    }

    let html = '<div class="requests-timeline">';

    requests.reverse().forEach((request) => {
        const timestamp = new Date(request.timestamp).toLocaleTimeString();
        const mqttContext = request.preceding_mqtt_events && request.preceding_mqtt_events.length > 0
            ? `<p><strong>Device was:</strong> ${request.preceding_mqtt_events[request.preceding_mqtt_events.length - 1].playback_status}</p>`
            : '<p><em>No MQTT context</em></p>';

        html += `
            <div class="timeline-request">
                <div class="request-time">${timestamp}</div>
                <div class="request-content">
                    <p><strong>Stream:</strong> ${request.stream_name}</p>
                    <p><strong>From IP:</strong> ${request.device_ip || 'unknown'}</p>
                    ${mqttContext}
                </div>
            </div>
        `;
    });

    html += '</div>';
    requestsList.innerHTML = html;
}

function updateErrorState(message) {
    const stateBox = document.getElementById('deviceStateSummary');
    stateBox.innerHTML = `<p class="error-message">${message}</p>`;
}

function getEventIcon(event) {
    if (event.button_left_clicked) return '⬅️';
    if (event.button_right_clicked) return '➡️';
    if (event.streaming) return '🎵';
    if (event.playback_status === 'playing') return '▶️';
    if (event.playback_status === 'paused') return '⏸️';
    if (event.playback_status === 'stopped') return '⏹️';
    return '📱';
}

async function sendTrackNavigation(direction) {
    try {
        const response = await fetch('/api/mqtt/track-nav', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                direction: direction,
            }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        if (result.success) {
            alert(`✓ ${direction === 'next' ? 'Next' : 'Previous'} track signal sent`);
            // Refresh to see updated state
            await refreshMQTTData();
        } else {
            alert('✗ Failed to send track navigation signal');
        }
    } catch (error) {
        console.error('Track navigation error:', error);
        alert('Error: ' + error.message);
    }
}

function toggleAutoRefresh(enabled) {
    if (enabled) {
        // Refresh immediately
        refreshMQTTData();

        // Then refresh every 2 seconds
        mqttAutoRefreshInterval = setInterval(() => {
            refreshMQTTData();
        }, 2000);
    } else {
        if (mqttAutoRefreshInterval) {
            clearInterval(mqttAutoRefreshInterval);
            mqttAutoRefreshInterval = null;
        }
    }
}

// Close modal when clicking outside
window.addEventListener('click', function (event) {
    const modal = document.getElementById('mqttAnalyzerModal');
    if (event.target === modal) {
        closeMQTTAnalyzer();
    }
});
