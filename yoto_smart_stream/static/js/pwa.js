// PWA Installation and Service Worker Registration
// Handles PWA features like installation prompt and offline support

let deferredPrompt;
let isInstalled = false;

// Check if app is already installed
function checkIfInstalled() {
  // Check if running in standalone mode (installed as PWA)
  if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
    isInstalled = true;
    console.log('[PWA] App is running in standalone mode');
    return true;
  }
  return false;
}

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((registration) => {
        console.log('[PWA] Service Worker registered:', registration.scope);

        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          console.log('[PWA] New service worker found');

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker available
              showUpdateNotification();
            }
          });
        });
      })
      .catch((error) => {
        console.error('[PWA] Service Worker registration failed:', error);
      });
  });
}

// Listen for beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] beforeinstallprompt event fired');
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  // Show install button
  showInstallButton();
});

// Listen for app installed event
window.addEventListener('appinstalled', () => {
  console.log('[PWA] App installed successfully');
  isInstalled = true;
  hideInstallButton();
  showInstalledNotification();
  deferredPrompt = null;
});

// Show install button in UI
function showInstallButton() {
  if (isInstalled || checkIfInstalled()) {
    return;
  }

  const installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.style.display = 'inline-block';
  } else {
    // Create install button if it doesn't exist
    createInstallButton();
  }
}

// Hide install button
function hideInstallButton() {
  const installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.style.display = 'none';
  }
}

// Create install button dynamically
function createInstallButton() {
  const button = document.createElement('button');
  button.id = 'pwa-install-button';
  button.className = 'action-button primary pwa-install-btn';
  button.innerHTML = '📱 Install App';
  button.onclick = installApp;

  // Add to actions grid if available
  const actionsGrid = document.querySelector('.actions-grid');
  if (actionsGrid) {
    actionsGrid.appendChild(button);
  }
}

// Install app function
async function installApp() {
  if (!deferredPrompt) {
    console.log('[PWA] No install prompt available');
    return;
  }

  // Show the install prompt
  deferredPrompt.prompt();

  // Wait for the user's response
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`[PWA] User response to install prompt: ${outcome}`);

  if (outcome === 'accepted') {
    console.log('[PWA] User accepted the install prompt');
  } else {
    console.log('[PWA] User dismissed the install prompt');
  }

  // Clear the deferred prompt
  deferredPrompt = null;
  hideInstallButton();
}

// Show update notification
function showUpdateNotification() {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = 'pwa-update-notification';
  notification.innerHTML = `
    <div class="pwa-notification-content">
      <span>🔄 New version available!</span>
      <button onclick="refreshApp()" class="btn-small">Update</button>
      <button onclick="this.parentElement.parentElement.remove()" class="btn-small">Later</button>
    </div>
  `;

  // Add to body
  document.body.appendChild(notification);
}

// Show installed notification
function showInstalledNotification() {
  const notification = document.createElement('div');
  notification.className = 'pwa-success-notification';
  notification.innerHTML = `
    <div class="pwa-notification-content">
      <span>✅ App installed successfully!</span>
      <button onclick="this.parentElement.parentElement.remove()" class="btn-small">OK</button>
    </div>
  `;

  document.body.appendChild(notification);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    notification.remove();
  }, 5000);
}

// Refresh app to activate new service worker
function refreshApp() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistration().then((registration) => {
      if (registration && registration.waiting) {
        // Tell the waiting service worker to skip waiting
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        // Reload page to activate new service worker
        window.location.reload();
      }
    });
  }
}

// Check online/offline status
window.addEventListener('online', () => {
  console.log('[PWA] App is online');
  updateOnlineStatus(true);
});

window.addEventListener('offline', () => {
  console.log('[PWA] App is offline');
  updateOnlineStatus(false);
});

// Update online status in UI
function updateOnlineStatus(isOnline) {
  const statusIndicator = document.getElementById('status');
  if (statusIndicator) {
    if (isOnline) {
      statusIndicator.classList.remove('offline');
      statusIndicator.classList.add('online');
    } else {
      statusIndicator.classList.remove('online');
      statusIndicator.classList.add('offline');
    }
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  checkIfInstalled();

  // Check initial online status
  if (!navigator.onLine) {
    updateOnlineStatus(false);
  }

  // Show install button if not installed and prompt available
  if (!isInstalled && !checkIfInstalled()) {
    // Button will be shown when beforeinstallprompt fires
    console.log('[PWA] Waiting for install prompt...');
  }
});

// Export for use in other scripts
window.PWA = {
  install: installApp,
  refresh: refreshApp,
  isInstalled: () => isInstalled || checkIfInstalled()
};
