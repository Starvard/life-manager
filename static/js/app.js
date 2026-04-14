/* ── API Helpers ───────────────────────────────────────────────── */

async function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    return res.json();
}

/* ── Alpine.js: Routine Card ──────────────────────────────────── */

document.addEventListener("alpine:init", () => {

    Alpine.data("routineCard", (weekKey, areaKey, initialCard) => ({
        card: initialCard,
        newExtraName: "",

        init() {
            if (!Array.isArray(this.card.extra_tasks)) {
                this.card.extra_tasks = [];
            }
        },

        get todayIdx() {
            const ws = new Date(this.card.week_start + "T00:00:00");
            const now = new Date();
            now.setHours(0, 0, 0, 0);
            const diff = Math.floor((now - ws) / 86400000);
            if (diff < 0) return -1;
            if (diff > 6) return 7;
            return diff;
        },

        _hasFill(task, day) {
            if (day < 0 || day > 6) return false;
            for (let i = 0; i < task.days[day].length; i++) {
                if (task.days[day][i]) return true;
            }
            return false;
        },

        _overdueWindowFreq(task) {
            let f = task.freq != null ? Number(task.freq) : 1;
            if (f > 0 && f < 1) {
                f = 1;
            }
            return f;
        },

        _overdueLevels(task) {
            const ti = this.todayIdx;
            if (ti < 0 || ti > 6) return {};

            if (this._hasFill(task, ti)) return {};

            const f = this._overdueWindowFreq(task);
            const gap = f > 0 ? 7 / f : 7;
            const win = f >= 7 ? 0 : Math.min(Math.max(1, Math.floor(gap / 2)), 3);

            const streak = [];
            for (let d = ti; d >= 0; d--) {
                const sched = task.scheduled ? task.scheduled[d] : 0;
                if (sched <= 0) continue;
                let covered = false;
                for (let off = -win; off <= win; off++) {
                    const nd = d + off;
                    if (nd < 0 || nd > 6 || nd > ti) continue;
                    if (this._hasFill(task, nd)) { covered = true; break; }
                }
                if (covered) break;
                streak.push(d);
            }

            if (streak.length === 0) return {};
            if (streak[0] !== ti) streak.unshift(ti);

            const levels = {};
            for (let i = 0; i < streak.length; i++) {
                levels[streak[i]] = Math.min(streak.length - i, 4);
            }
            return levels;
        },

        dotClass(task, di, doi) {
            const filled = task.days[di][doi];
            const sched = task.scheduled ? task.scheduled[di] : task.days[di].length;
            const isScheduled = doi < sched;
            const cls = {};

            if (filled) {
                cls.filled = true;
                if (!isScheduled) cls.unscheduled = true;
                return cls;
            }

            const ti = this.todayIdx;

            if (ti > 6 && isScheduled) {
                cls["overdue-4"] = true;
                return cls;
            }

            if (ti >= 0 && ti <= 6 && di <= ti) {
                const levels = this._overdueLevels(task);
                if (levels[di] !== undefined) {
                    cls["overdue-" + levels[di]] = true;
                    if (!isScheduled) cls.unscheduled = true;
                    return cls;
                }
            }

            if (!isScheduled) {
                cls.unscheduled = true;
            }

            return cls;
        },

        async toggleDot(taskIdx, dayIdx, dotIdx) {
            const dots = this.card.tasks[taskIdx].days[dayIdx];
            dots[dotIdx] = !dots[dotIdx];
            await api("PATCH",
                `/api/routine-cards/${weekKey}/${areaKey}/toggle`,
                { task: taskIdx, day: dayIdx, dot: dotIdx, list: "tasks" }
            );
        },

        async toggleDotExtra(taskIdx, dayIdx, dotIdx) {
            const dots = this.card.extra_tasks[taskIdx].days[dayIdx];
            dots[dotIdx] = !dots[dotIdx];
            await api("PATCH",
                `/api/routine-cards/${weekKey}/${areaKey}/toggle`,
                { task: taskIdx, day: dayIdx, dot: dotIdx, list: "extra_tasks" }
            );
        },

        async addExtraRow() {
            const name = (this.newExtraName || "").trim();
            if (!name) return;
            const res = await api("POST",
                `/api/routine-cards/${weekKey}/${areaKey}/extra-task`,
                { name }
            );
            if (res.ok && res.extra_tasks) {
                this.card.extra_tasks = res.extra_tasks;
                this.newExtraName = "";
            }
        },

        async removeExtraRow(taskIdx) {
            const res = await fetch(
                `/api/routine-cards/${weekKey}/${areaKey}/extra-task/${taskIdx}`,
                { method: "DELETE" }
            );
            const data = await res.json();
            if (data.ok) {
                this.card.extra_tasks.splice(taskIdx, 1);
            }
        },

        async saveNotes() {
            await api("PUT",
                `/api/routine-cards/${weekKey}/${areaKey}/notes`,
                { notes: this.card.notes }
            );
        },

        _taskWeight(task) {
            let w = Number(task.weight);
            if (!Number.isFinite(w) || w <= 0) return 1;
            return w;
        },

        /** Matches server score_helpers: full weight for scheduled, 0.4 for extra dots. */
        _progressForTaskList(taskList) {
            const BONUS = 0.4;
            let earned = 0, possible = 0;
            for (const task of taskList) {
                const w = this._taskWeight(task);
                const sched = task.scheduled || [];
                for (let di = 0; di < task.days.length; di++) {
                    let sc = sched[di];
                    sc = Number.isFinite(Number(sc)) ? Math.max(0, Math.floor(Number(sc))) : 0;
                    const row = task.days[di];
                    const nrow = row.length;
                    for (let doi = 0; doi < sc; doi++) {
                        possible += w;
                        if (doi < nrow && row[doi]) earned += w;
                    }
                    for (let doi = sc; doi < nrow; doi++) {
                        const bp = w * BONUS;
                        possible += bp;
                        if (row[doi]) earned += bp;
                    }
                }
            }
            return { earned, possible };
        },

        cardProgress() {
            const a = this._progressForTaskList(this.card.tasks);
            const b = this._progressForTaskList(this.card.extra_tasks || []);
            const earned = a.earned + b.earned;
            const possible = a.possible + b.possible;
            return possible > 0 ? Math.round((earned / possible) * 100) : 0;
        }
    }));

    /* ── Alpine.js: Budget Page ────────────────────────────────── */

    Alpine.data("budgetPage", (initialTxns, initialReport, initialPlan, initialCategories, currentMonth, months, initialOverview) => ({
        transactions: initialTxns || [],
        report: initialReport || { total_income: 0, total_expenses: 0, net: 0, transaction_count: 0, categories: [] },
        plan: initialPlan || { month: currentMonth, sections: {}, notes: "" },
        allCategories: initialCategories || [],
        overview: initialOverview || {},
        currentMonth: currentMonth,
        allMonths: months || [],
        view: "overview",
        searchQuery: "",
        filterCategory: "",
        filteredTxns: [],
        duplicates: [],
        editingCatId: null,
        editCatValue: "",
        importing: false,
        importMsg: "",
        importReplaceAll: false,

        init() {
            if (!this.report.snapshot) {
                this.report.snapshot = {
                    planned_income: 0,
                    actual_income: 0,
                    income_variance: 0,
                    planned_expenses: 0,
                    actual_expenses: 0,
                    expense_variance: 0,
                    planned_net: 0,
                    actual_net: 0,
                    net_variance: 0,
                    has_planned_expenses: false,
                    has_planned_income: false,
                };
            }
            this.filterTxns();
            this.loadDuplicates();
            if (!this.plan.sections || Object.keys(this.plan.sections).length === 0) {
                this.plan.sections = {
                    income: { label: "Income", items: [] },
                    bills: { label: "Bills", items: [] },
                    savings: { label: "Savings", items: [] },
                    food_gas: { label: "Food & Gas", items: [] },
                    subscriptions: { label: "Subscriptions", items: [] },
                    personal: { label: "Personal Care", items: [] },
                    misc: { label: "Misc", items: [] },
                };
            }
        },

        monthLabel(m) {
            if (!m) return "";
            const [y, mo] = m.split("-");
            const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            return names[parseInt(mo, 10) - 1] + " " + y;
        },

        switchMonth() {
            window.location.href = "/budget?month=" + this.currentMonth;
        },

        prevMonth() {
            const idx = this.allMonths.indexOf(this.currentMonth);
            if (idx > 0) {
                this.currentMonth = this.allMonths[idx - 1];
                this.switchMonth();
            }
        },

        nextMonth() {
            const idx = this.allMonths.indexOf(this.currentMonth);
            if (idx < this.allMonths.length - 1) {
                this.currentMonth = this.allMonths[idx + 1];
                this.switchMonth();
            }
        },

        formatMoney(v) {
            if (v == null) return "$0.00";
            const n = Number(v);
            const neg = n < 0;
            const abs = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            return neg ? "-$" + abs : "$" + abs;
        },

        formatMoneyDash(v) {
            if (v == null || v === "") return "—";
            if (typeof v === "number" && Number.isNaN(v)) return "—";
            return this.formatMoney(v);
        },

        overviewHasData() {
            const o = this.overview;
            return !!(o && o.month && Array.isArray(o.snapshot) && o.snapshot.length > 0);
        },

        /** Budget "battery": width = remaining / allocated (green → purple fill). */
        showRemainingMeter(row) {
            const a = Number(row?.allocated);
            const r = row?.remaining;
            if (!(a > 0) || r == null) return false;
            const rn = Number(r);
            return !Number.isNaN(a) && !Number.isNaN(rn);
        },

        remainingMeterWidth(row) {
            const a = Number(row?.allocated);
            const r = row?.remaining;
            if (!(a > 0) || r == null) return 0;
            const rn = Number(r);
            if (Number.isNaN(a) || Number.isNaN(rn)) return 0;
            if (rn < 0) return 100;
            return Math.max(0, Math.min(100, (rn / a) * 100));
        },

        remainingMeterClass(row) {
            const r = Number(row?.remaining);
            const a = Number(row?.allocated);
            if (a > 0 && !Number.isNaN(r) && r < 0) return "budget-ov-meter-fill over";
            return "budget-ov-meter-fill";
        },

        remainingMeterLabel(row) {
            if (!this.showRemainingMeter(row)) return "";
            const a = Number(row.allocated);
            const r = Number(row.remaining);
            if (r < 0) return "Over";
            return Math.round((r / a) * 100) + "% left";
        },

        /** Variance cells: show +$ / -$ for clarity */
        formatMoneySigned(v) {
            if (v == null || v === 0) return "$0.00";
            const n = Number(v);
            const abs = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            return (n > 0 ? "+$" : "-$") + abs;
        },

        snapshotIncomeVarClass(v) {
            const n = Number(v);
            if (!n) return "";
            return n <= 0 ? "snapshot-pos" : "snapshot-neg";
        },

        snapshotExpenseVarClass(v) {
            const n = Number(v);
            if (!n) return "";
            return n >= 0 ? "snapshot-pos" : "snapshot-neg";
        },

        snapshotNetVarClass(v) {
            const n = Number(v);
            if (!n) return "";
            /* Negative variance => actual net beat planned */
            return n <= 0 ? "snapshot-pos" : "snapshot-neg";
        },

        filterTxns() {
            let list = this.transactions.filter(t => !t.is_duplicate);
            if (this.searchQuery) {
                const q = this.searchQuery.toLowerCase();
                list = list.filter(t =>
                    (t.description || "").toLowerCase().includes(q) ||
                    (t.category_display || "").toLowerCase().includes(q) ||
                    (t.account || "").toLowerCase().includes(q)
                );
            }
            if (this.filterCategory) {
                list = list.filter(t => this.displayCat(t) === this.filterCategory);
            }
            list.sort((a, b) => b.date.localeCompare(a.date));
            this.filteredTxns = list;
        },

        displayCat(tx) {
            return tx.category_override || tx.category_display || tx.category || "Other";
        },

        startEditCategory(tx) {
            this.editingCatId = tx.id;
            this.editCatValue = this.displayCat(tx);
            this.$nextTick(() => {
                const sel = this.$refs.catSelect;
                if (sel) sel.focus();
            });
        },

        async saveCategory(tx) {
            const cat = this.editCatValue;
            this.editingCatId = null;
            if (!cat || cat === this.displayCat(tx)) return;
            tx.category_override = cat;
            await api("PATCH", `/api/budget/transactions/${tx.id}/category`, { category: cat });
        },

        async loadDuplicates() {
            const res = await api("GET", `/api/budget/transactions?month=${this.currentMonth}&show_duplicates=true`);
            if (res && res.transactions) {
                this.duplicates = res.transactions.filter(t => t.is_duplicate);
            }
        },

        get duplicateCount() {
            return this.duplicates.length;
        },

        async resolveDupe(tx, action) {
            await api("PATCH", `/api/budget/transactions/${tx.id}/duplicate`, { action });
            this.duplicates = this.duplicates.filter(d => d.id !== tx.id);
            if (action === "keep") {
                this.transactions.push(tx);
                tx.is_duplicate = false;
                this.filterTxns();
            }
        },

        async importData() {
            this.importing = true;
            this.importMsg = "";
            try {
                const res = await api("POST", "/api/budget/import", {
                    replace_all: !!this.importReplaceAll,
                });
                if (res.ok) {
                    const parts = [];
                    if (res.overview_months_saved)
                        parts.push(`${res.overview_months_saved} month budget view(s) updated`);
                    if (res.imported)
                        parts.push(
                            `${res.new} new txn · ${res.duplicates_marked} dupes · ${res.total} total`
                        );
                    this.importMsg = parts.length ? parts.join(" · ") : "Import complete.";
                    setTimeout(() => { this.importMsg = ""; }, 6000);
                    setTimeout(() => window.location.reload(), 1200);
                } else {
                    this.importMsg = res.error || "Import failed.";
                }
            } catch (e) {
                this.importMsg = "Import error.";
            }
            this.importing = false;
        },

        /* Plan helpers */

        addPlanItem(sectionKey) {
            this.plan.sections[sectionKey].items.push({ name: "", allocated: 0, actual: 0 });
        },

        removePlanItem(sectionKey, idx) {
            this.plan.sections[sectionKey].items.splice(idx, 1);
            this.savePlan();
        },

        async savePlan() {
            await api("PUT", `/api/budget/plan/${this.currentMonth}`, this.plan);
        },

        sectionTotal(section, field) {
            return (section.items || []).reduce((s, i) => s + (Number(i[field]) || 0), 0);
        },

        sectionRemaining(section) {
            return this.sectionTotal(section, "allocated") - this.sectionTotal(section, "actual");
        },

        /* Report helpers */

        barWidth(total) {
            if (!this.report.categories || this.report.categories.length === 0) return 0;
            const maxAbs = Math.max(...this.report.categories.map(c => Math.abs(c.total)), 1);
            return Math.round((Math.abs(total) / maxAbs) * 100);
        },
    }));

    /* ── Alpine.js: Baby Card ─────────────────────────────────── */

    Alpine.data("babyCard", (cardDate, initialCard) => ({
        card: initialCard,
        painting: false,
        paintMode: true,
        paintTrack: null,
        dirty: new Set(),

        startPaint(trackKey, idx) {
            this.painting = true;
            this.paintTrack = trackKey;
            this.dirty = new Set();
            const sq = this.card.tracks[trackKey].squares;
            this.paintMode = !sq[idx];
            sq[idx] = this.paintMode;
            this.dirty.add(idx);
        },

        continuePaint(trackKey, idx) {
            if (!this.painting || trackKey !== this.paintTrack) return;
            const sq = this.card.tracks[trackKey].squares;
            if (sq[idx] !== this.paintMode) {
                sq[idx] = this.paintMode;
                this.dirty.add(idx);
            }
        },

        onTouchMove(event) {
            if (!this.painting) return;
            const touch = event.touches[0];
            const el = document.elementFromPoint(touch.clientX, touch.clientY);
            if (!el || !el.classList.contains("blk")) return;
            const grid = el.closest(".block-grid");
            if (!grid) return;
            const trackKey = grid.dataset.track;
            const idx = parseInt(el.dataset.idx, 10);
            if (!isNaN(idx)) this.continuePaint(trackKey, idx);
        },

        async endPaint() {
            if (!this.painting) return;
            this.painting = false;
            const trackKey = this.paintTrack;
            const sq = [...this.card.tracks[trackKey].squares];
            await api("PATCH", `/api/baby-cards/${cardDate}/track`, {
                track: trackKey, squares: sq
            });
            this.dirty = new Set();
        },

        async updateTally(trackKey, delta) {
            const t = this.card.tracks[trackKey];
            t.count = Math.max(0, t.count + delta);
            await api("PATCH", `/api/baby-cards/${cardDate}/track`, {
                track: trackKey, count: t.count
            });
        },

        async updateNotes(trackKey) {
            const val = this.card.tracks[trackKey].text;
            await api("PATCH", `/api/baby-cards/${cardDate}/track`, {
                track: trackKey, text: val
            });
        }
    }));
});

/* ── Flash auto-dismiss ───────────────────────────────────────── */

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

async function initPushReminders() {
    const card = document.getElementById("push-reminders-card");
    if (!card) return;
    const btnEn = document.getElementById("push-enable-btn");
    const btnDis = document.getElementById("push-disable-btn");
    const status = document.getElementById("push-status");
    if (!btnEn || !btnDis || !status) return;

    const setStatus = (t) => {
        status.textContent = t;
    };

    const ua = navigator.userAgent || "";
    const likelyPhone = /Android|iPhone|iPad|iPod/i.test(ua);
    const loopbackHost =
        location.hostname === "127.0.0.1" ||
        location.hostname === "localhost" ||
        location.hostname === "[::1]";
    if (likelyPhone && loopbackHost) {
        setStatus(
            "On a phone, 127.0.0.1 / localhost is this device, not your PC. Open your PC's LAN or tunnel URL from the banner (trusted HTTPS for push on Android)."
        );
        btnEn.disabled = true;
        return;
    }

    if (location.protocol === "http:" && !loopbackHost) {
        setStatus(
            "Plain http:// to a LAN IP (192.168…) cannot use push. On this computer use http://127.0.0.1:5000 with start.bat. On a phone use trusted https:// (tunnel, ngrok, or mkcert)."
        );
        btnEn.disabled = true;
        return;
    }

    if (!window.isSecureContext) {
        setStatus(
            "This page is not a secure context for push. Use http://127.0.0.1:5000 on this PC, or trusted HTTPS on a phone (tunnel / mkcert)."
        );
        btnEn.disabled = true;
        return;
    }

    if (!("serviceWorker" in navigator)) {
        setStatus("This browser doesn't support service workers. Use current Google Chrome (not an in-app browser or WebView).");
        btnEn.disabled = true;
        return;
    }

    let swProbe;
    try {
        swProbe = await fetch("/sw.js", { cache: "no-store", credentials: "same-origin" });
    } catch (e) {
        setStatus("Could not load /sw.js over the network. Check Wi‑Fi and that the PC server is running.");
        btnEn.disabled = true;
        return;
    }
    if (!swProbe.ok) {
        setStatus(`Server returned ${swProbe.status} for /sw.js (expected 200).`);
        btnEn.disabled = true;
        return;
    }
    const ct = (swProbe.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("javascript")) {
        setStatus(`Wrong type for /sw.js (${ct || "none"}). Server must send JavaScript.`);
        btnEn.disabled = true;
        return;
    }

    let reg;
    try {
        reg = await navigator.serviceWorker.register("/sw.js", {
            scope: "/",
            updateViaCache: "none",
        });
    } catch (e) {
        const detail = e && e.message ? e.message : String(e);
        setStatus(
            `Worker install failed: ${detail}. If the URL is https://192.168… with the dev (adhoc) certificate, Chrome often cannot fetch sw.js even when the page loads—this is expected. Fix on this PC: open http://127.0.0.1:5000 with start.bat (no SSL). On Android: use Cloudflare Tunnel, ngrok, or mkcert so https:// is fully trusted. You can also try Chrome ⋮ → Site settings → clear data for this site.`
        );
        btnEn.disabled = true;
        return;
    }

    if (!reg.pushManager) {
        setStatus(
            "Push isn't exposed here. Try: full Chrome (stable), not Incognito, not Chrome Lite / Data Saver. Or use Samsung Internet. If you're already on trusted HTTPS and still see this, say so—it's rare."
        );
        btnEn.disabled = true;
        return;
    }

    const syncUi = async () => {
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
            btnEn.hidden = true;
            btnDis.hidden = false;
            setStatus("Reminders enabled on this device.");
        } else {
            btnEn.hidden = false;
            btnDis.hidden = true;
            setStatus(
                loopbackHost
                    ? "Not subscribed yet—tap Enable (http://127.0.0.1 is OK on this PC)."
                    : "Not subscribed yet—tap Enable if https:// is trusted (otherwise use tunnel or http://127.0.0.1 on the PC)."
            );
        }
    };
    await syncUi();

    btnEn.addEventListener("click", async () => {
        setStatus("Working…");
        const perm = await Notification.requestPermission();
        if (perm !== "granted") {
            setStatus("Notification permission denied.");
            return;
        }
        let res;
        try {
            res = await fetch("/api/push/vapid-public-key");
        } catch (e) {
            setStatus("Could not load VAPID key.");
            return;
        }
        const { publicKey } = await res.json();
        if (!publicKey) {
            setStatus("Server missing VAPID public key.");
            return;
        }
        try {
            const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey),
            });
            const body = sub.toJSON();
            const save = await fetch("/api/push/subscribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await save.json();
            if (!data.ok) {
                setStatus("Could not save subscription on server.");
                return;
            }
            setStatus("Subscribed. Incomplete tasks for today will be nagged on the scheduler interval.");
        } catch (e) {
            setStatus("Subscribe failed — on this PC try http://127.0.0.1:5000; on HTTPS use a trusted certificate (tunnel/mkcert).");
        }
        await syncUi();
    });

    btnDis.addEventListener("click", async () => {
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
            const ep = sub.endpoint;
            await sub.unsubscribe();
            await fetch("/api/push/subscribe", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ endpoint: ep }),
            });
        }
        setStatus("Unsubscribed.");
        await syncUi();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach(el => {
        setTimeout(() => {
            el.style.transition = "opacity 0.3s";
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 300);
        }, 4000);
    });
    initPushReminders();
});
