self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const windows = await clients.matchAll({ type: "window", includeUncontrolled: true });
    if (windows.length) {
      await windows[0].focus();
      return;
    }
    await clients.openWindow("/");
  })());
});
