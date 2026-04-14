/* Life Manager — Web Push + notification actions (scope: site root via /sw.js). */

self.addEventListener("push", (event) => {
  let payload = {};
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload = { body: event.data.text() };
    }
  }
  const tag = payload.tag || "life-manager";
  const options = {
    body: payload.body || "",
    tag,
    data: {
      tag,
      url: payload.url || "/cards",
      week_key: payload.week_key,
      area_key: payload.area_key,
      task: payload.task,
      day: payload.day,
      list: payload.list || "tasks",
    },
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    actions: [
      { action: "open", title: "Open" },
      { action: "done", title: "Done" },
    ],
  };
  event.waitUntil(
    self.registration.showNotification(payload.title || "Life Manager", options)
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const d = event.notification.data || {};
  const origin = self.location.origin;
  const tag = d.tag || event.notification.tag;

  if (event.action === "done") {
    const { week_key, area_key, task, day, list } = d;
    if (week_key && area_key != null && task != null && day != null) {
      event.waitUntil(
        fetch(
          `${origin}/api/routine-cards/${encodeURIComponent(week_key)}/${encodeURIComponent(area_key)}/complete-scheduled-day`,
          {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              task,
              day,
              list: list || "tasks",
            }),
          }
        )
          .then(() =>
            self.registration.getNotifications({ tag }).then((ns) => {
              ns.forEach((n) => n.close());
            })
          )
          .catch(() => {})
      );
    }
    return;
  }

  const path = d.url && d.url.startsWith("/") ? d.url : "/cards";
  const abs = origin + path;
  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const c of clientList) {
          if (c.url.startsWith(origin) && "focus" in c) {
            if (typeof c.navigate === "function") {
              return c
                .navigate(abs)
                .then(() => c.focus())
                .catch(() => clients.openWindow(abs));
            }
            return c.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(abs);
        }
      })
  );
});
