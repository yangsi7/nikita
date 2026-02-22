// Service Worker for Nikita push notifications
// Registered by providers.tsx, receives push events from VAPID server

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {
    title: "Nikita",
    body: "New notification",
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/nikita-icon-192.png",
      badge: "/nikita-badge-72.png",
      tag: data.tag || "nikita-default",
      data: { url: data.url || "/dashboard" },
    })
  )
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing tab if open
        for (const client of clientList) {
          if (client.url.includes("/dashboard") && "focus" in client) {
            return client.focus()
          }
        }
        // Otherwise open new tab
        return clients.openWindow(event.notification.data.url)
      })
  )
})
