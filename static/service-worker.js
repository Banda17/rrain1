// Service Worker for Push Notifications

self.addEventListener('push', function(event) {
  console.log('[Service Worker] Push Received.');
  
  let notificationData = {};
  
  // Try to parse notification data from the push event
  try {
    if (event.data) {
      notificationData = event.data.json();
    }
  } catch (e) {
    console.error('Error parsing push notification data', e);
  }
  
  // Set default values if not provided in the push payload
  const title = notificationData.title || 'SCR Vijayawada Division';
  const options = {
    body: notificationData.body || 'New train update available!',
    icon: notificationData.icon || '/static/notification-icon.png',
    badge: notificationData.badge || '/static/notification-badge.png',
    data: {
      url: notificationData.url || '/',
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: notificationData.actions || [
      {
        action: 'view',
        title: 'View Details'
      }
    ]
  };

  // Display the notification
  const notificationPromise = self.registration.showNotification(title, options);
  
  // Wait until notification is shown
  event.waitUntil(notificationPromise);
});

// Handle notification click
self.addEventListener('notificationclick', function(event) {
  console.log('[Service Worker] Notification click received.');

  event.notification.close();

  // Get the notification data
  const notificationData = event.notification.data;
  
  // Navigate to the URL from the notification data or to the root
  const urlToOpen = notificationData?.url || '/';
  
  // This looks to see if the current is already open and focuses if it is
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    })
    .then(function(clientList) {
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// Service worker installation
self.addEventListener('install', function(event) {
  console.log('[Service Worker] Installing Service Worker...', event);
  // Skip waiting to make the service worker activate immediately
  self.skipWaiting();
});

// Service worker activation
self.addEventListener('activate', function(event) {
  console.log('[Service Worker] Activating Service Worker...', event);
  // Claim clients to ensure the service worker controls all clients
  event.waitUntil(self.clients.claim());
  return self.clients.claim();
});