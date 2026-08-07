/* Life Manager — Web Push + notification actions (scope: site root via /sw.js). */

/* No caching happens here, so take over immediately on update — otherwise a
   long-lived PWA tab keeps running the previous push handler indefinitely. */
self.addEventListener("install", () => {
  self.skipWaiting();
});
self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

/* Browsers rotate/expire push subscriptions from time to time. Without this
   handler the server keeps pushing to the dead endpoint, gets a 410, and
   silently drops the device — reminders stop until the user re-enables.
   Re-subscribe and tell the server about the new endpoint. */
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil(
    (async () => {
      try {
        const res = await fetch("/api/push/vapid-public-key", { credentials: "include" });
        const { publicKey } = await res.json();
        if (!publicKey) return;
        const sub = await self.registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        });
        await fetch("/api/push/subscribe", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(sub.toJSON()),
        });
        const old = event.oldSubscription;
        if (old && old.endpoint && old.endpoint !== sub.endpoint) {
          await fetch("/api/push/subscribe", {
            method: "DELETE",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ endpoint: old.endpoint }),
          });
        }
      } catch (e) {
        /* next page load re-syncs the subscription anyway */
      }
    })()
  );
});

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
    // Tags repeat (per-task tags span the week; the nudge tag is constant),
    // and without renotify Chrome treats a same-tag push as a silent
    // in-place update — the reminder never buzzes again. Re-alert always.
    renotify: true,
    // Reminders should stick around until acted on (desktop Chrome honors
    // this; Android shows them in the tray as usual).
    requireInteraction: !!payload.requireInteraction,
    data: {
      tag,
      url: payload.url || "/cards",
      week_key: payload.week_key,
      area_key: payload.area_key,
      task: payload.task,
      task_name: payload.task_name,
      day: payload.day,
      day_iso: payload.day_iso,
      dot: payload.dot,
      list: payload.list || "tasks",
      flex_key: payload.flex_key || "",
    },
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    actions: [
      { action: "open", title: "Open" },
      { action: "done", title: "Done ✓" },
      { action: "skip", title: "Skip" },
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

  if (event.action === "skip") {
    const { area_key, list, task_name, day_iso, flex_key } = d;
    const dayIso = day_iso || new Date().toISOString().slice(0, 10);
    if (area_key && task_name) {
      const body = {
        area_key,
        task_name,
        list: list || "tasks",
      };
      if (flex_key) body.flex_key = flex_key;
      event.waitUntil(
        fetch(`${origin}/api/routine-day/${encodeURIComponent(dayIso)}/skip`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
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
