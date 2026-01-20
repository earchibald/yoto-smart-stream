# Progressive Web App (PWA) - Mobile Installation Guide

Yoto Smart Stream is now available as a Progressive Web App (PWA), allowing you to install it on your mobile device for an app-like experience without going through an app store.

## What is a PWA?

A Progressive Web App combines the best of web and mobile apps:

- ✅ **No App Store Required**: Install directly from your web browser
- ✅ **Cross-Platform**: Works on iOS, Android, and Desktop
- ✅ **Automatic Updates**: Always get the latest version
- ✅ **Offline Support**: Core features work without internet
- ✅ **Native Feel**: Looks and behaves like a native app
- ✅ **Home Screen Icon**: Quick access from your home screen

## Installation Instructions

### iOS (iPhone/iPad)

1. **Open Safari** (PWAs require Safari on iOS)
2. Navigate to your Yoto Smart Stream URL (e.g., `https://your-server.com`)
3. Tap the **Share** button (square with arrow pointing up)
4. Scroll down and tap **"Add to Home Screen"**
5. Edit the name if desired (default: "Yoto Stream")
6. Tap **"Add"** in the top right corner
7. The Yoto Stream icon will appear on your home screen

#### iOS Screenshots

The app will launch in full-screen mode without Safari's browser chrome, giving you a native app experience.

**iOS Notes:**
- Requires iOS 11.3 or later
- Service workers have limited functionality on iOS but core features work
- Some background features may not work when the app is closed

### Android (Chrome)

1. **Open Chrome** browser
2. Navigate to your Yoto Smart Stream URL
3. You'll see an **"Install"** or **"Add to Home Screen"** prompt at the bottom
   - If you don't see it, tap the **⋮** menu and select **"Install app"** or **"Add to Home Screen"**
4. Tap **"Install"** in the confirmation dialog
5. The app will be installed and appear in your app drawer

#### Android Alternative Method

If the automatic prompt doesn't appear:
1. Tap the **⋮** menu (three dots) in Chrome
2. Select **"Add to Home Screen"**
3. Name the app and tap **"Add"**

**Android Notes:**
- Requires Android 5.0+ and Chrome 40+
- Full PWA features including background sync and push notifications
- Can be uninstalled like any regular app

### Desktop (Chrome, Edge, Safari)

Modern desktop browsers also support PWA installation:

#### Chrome/Edge:
1. Look for the **⊕** icon in the address bar
2. Click it and select **"Install Yoto Smart Stream"**
3. Or go to Menu → **"Install Yoto Smart Stream..."**

#### Safari (macOS):
1. Click **File** → **"Add to Dock"** (macOS Sonoma+)
2. Or use **File** → **"Add to Favorites"** for quick access

## Features

### Offline Capability

The PWA includes service worker caching for offline use:

- **Cached Assets**: CSS, JavaScript, and static files work offline
- **API Fallback**: Graceful degradation when network is unavailable
- **Automatic Updates**: New versions detected and loaded automatically

### Mobile-Optimized Interface

- **Touch-Friendly**: Minimum 44px touch targets for easy interaction
- **Responsive Design**: Adapts to all screen sizes
- **iOS Safe Areas**: Respects notches and home indicators
- **Landscape Support**: Works in both portrait and landscape modes

### Install Prompt

When you first visit the site on a compatible device, you may see an **"📱 Install App"** button in the Quick Actions section. Click it to install the PWA.

## Verifying Installation

After installation, you should see:

- ✅ App icon on your home screen/app drawer
- ✅ Splash screen when launching
- ✅ Full-screen display (no browser UI)
- ✅ Status bar themed to match the app
- ✅ Works offline (try enabling airplane mode)

## Updating the App

PWAs update automatically! When a new version is deployed:

1. You'll see a notification: **"🔄 New version available!"**
2. Click **"Update"** to apply the changes
3. The app will reload with the new version

## Uninstalling

### iOS
1. Long-press the Yoto Stream icon on your home screen
2. Tap **"Remove App"** → **"Delete App"**

### Android
1. Long-press the app icon
2. Select **"Uninstall"** or drag to the uninstall area
3. Or go to Settings → Apps → Yoto Smart Stream → Uninstall

### Desktop
1. Right-click the app icon or title bar
2. Select **"Uninstall"** or **"Remove from Chrome"**

## Troubleshooting

### "Add to Home Screen" option not available

**iOS:**
- Make sure you're using Safari (not Chrome or Firefox)
- Check that you're using iOS 11.3 or later
- Make sure the website uses HTTPS (required for PWAs)

**Android:**
- Make sure you're using Chrome
- Clear Chrome's cache and cookies
- Check that the website uses HTTPS

### App doesn't work offline

- Service worker needs time to cache assets on first visit
- Try using the app online first, then test offline
- Check your browser's developer tools (Service Workers tab)

### Install prompt doesn't appear

- You may have previously dismissed it
- Try Menu → "Install app" manually
- Check that you're not already in standalone mode
- Clear browser data and revisit the site

### App looks like a website

- Make sure you launched from the home screen icon, not the browser
- On iOS, ensure you added it through Safari's Share menu
- Try reinstalling the app

## Technical Details

### Browser Requirements

**Minimum versions for full PWA support:**
- iOS: Safari 11.3+ (iOS 11.3+)
- Android: Chrome 40+, Firefox 44+, Samsung Internet 4+
- Desktop: Chrome 67+, Edge 79+, Safari 14+ (macOS)

### PWA Features

- **Web App Manifest**: Defines app name, icons, and behavior
- **Service Worker**: Enables offline capability and caching
- **App Shell**: Core UI cached for instant loading
- **Responsive Design**: Mobile-first, works on all screens
- **Theme Color**: Status bar matches app theme (#4A90E2)

### Caching Strategy

- **Static Assets**: Cache-first (fast loading)
- **API Requests**: Network-first with cache fallback
- **Images**: Cache as they're viewed
- **Auto-cleanup**: Old cache versions removed automatically

## Security

PWAs require HTTPS (secure connection) to function. This ensures:
- Data transmitted is encrypted
- Service worker can't be hijacked
- User privacy is protected

## Feedback

Having issues with the PWA? Please report them:
- GitHub Issues: [github.com/earchibald/yoto-smart-stream/issues](https://github.com/earchibald/yoto-smart-stream/issues)
- Include: Device type, OS version, browser name and version, and description of the issue

## Additional Resources

- [MDN: Progressive Web Apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [Web.dev: PWA Checklist](https://web.dev/pwa-checklist/)
- [Can I Use: PWA Features](https://caniuse.com/serviceworkers)

---

## For Developers

### Testing the PWA

Run the automated test suite:

```bash
# Start the server
python -m uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port 8080

# In another terminal, run PWA tests
TEST_URL=http://localhost:8080 pytest tests/test_pwa.py -v
```

### Regenerating Icons

If you need to regenerate PWA icons:

```bash
python scripts/generate_pwa_icons.py
```

This creates all required icon sizes from the base design.

### Service Worker Development

During development, force service worker updates:
1. Open DevTools (F12)
2. Go to Application → Service Workers
3. Check "Update on reload"
4. Or click "Unregister" to completely remove

### Manifest Validation

Check your manifest at:
- Chrome DevTools: Application → Manifest
- [Manifest Validator](https://manifest-validator.appspot.com/)

---

Made with ❤️ for the Yoto community
