/* ── API Helpers ───────────────────────────────────────────────── */

async function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    return res.json();
}

/** Matches services/score_helpers: pool of scheduled completions across the week. */
const ROUTINE_BONUS_RATIO = 0.4;

function _schedInt(sched, di) {
    if (!sched || di < 0 || di > 6) return 0;
    const s = Number(sched[di]);
    return Number.isFinite(s) ? Math.max(0, Math.floor(s)) : 0;
}

function _taskScheduledSlotCount(sched) {
    let n = 0;
    for (let di = 0; di < 7; di++) n += _schedInt(sched, di);
    return n;
}

function _taskTotalFillCount(days) {
    let n = 0;
    for (let di = 0; di < Math.min(7, days.length); di++) {
        const row = days[di] || [];
        for (let i = 0; i < row.length; i++) if (row[i]) n++;
    }
    return n;
}

/** Which filled cells consume the main pool (full weight), Mon→Sun row order. */
function poolFilledFlags(task) {
    const sched = task.scheduled || [];
    const days = task.days || [];
    const nSched = _taskScheduledSlotCount(sched);
    const nFill = _taskTotalFillCount(days);
    const pool = Math.min(nSched, nFill);
    let left = pool;
    const out = [];
    for (let di = 0; di < 7; di++) {
        const row = days[di] || [];
        out[di] = row.map((filled) => {
            if (filled && left > 0) {
                left--;
                return true;
            }
            return false;
        });
    }
    return out;
}

function _schedSlotIndex(sched, di, doi) {
    let k = 0;
    for (let d = 0; d < di; d++) k += _schedInt(sched, d);
    return k + doi;
}

function earnedByDayForTask(task) {
    const r = ROUTINE_BONUS_RATIO;
    let w = Number(task.weight);
    if (!Number.isFinite(w) || w <= 0) w = 1;
    const sched = task.scheduled || [];
    const days = task.days || [];
    const nSched = _taskScheduledSlotCount(sched);
    const nFill = _taskTotalFillCount(days);
    let poolLeft = Math.min(nSched, nFill);
    const out = [0, 0, 0, 0, 0, 0, 0];
    for (let di = 0; di < 7; di++) {
        const row = days[di] || [];
        for (let i = 0; i < row.length; i++) {
            if (!row[i]) continue;
            if (poolLeft > 0) {
                out[di] += w;
                poolLeft--;
            } else {
                out[di] += w * r;
            }
        }
    }
    return out;
}

function possibleByDayForTask(task, dayIdx) {
    let w = Number(task.weight);
    if (!Number.isFinite(w) || w <= 0) w = 1;
    const r = ROUTINE_BONUS_RATIO;
    const sched = task.scheduled || [];
    const days = task.days || [];
    let possible = 0;
    const sc = _schedInt(sched, dayIdx);
    const row = days[dayIdx] || [];
    const nrow = row.length;
    for (let j = 0; j < sc; j++) possible += w;
    for (let j = sc; j < nrow; j++) possible += w * r;
    return possible;
}

function progressForTaskList(taskList) {
    let earned = 0, possible = 0;
    for (const task of taskList) {
        const byDay = earnedByDayForTask(task);
        earned += byDay.reduce((a, b) => a + b, 0);
        for (let di = 0; di < 7; di++) {
            possible += possibleByDayForTask(task, di);
        }
    }
    return { earned, possible };
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

        _overdueStreakLevel(task) {
            const ti = this.todayIdx;
            if (ti < 0 || ti > 6) return 0;
            const sched = task.scheduled || [];
            const days = task.days || [];
            const nSched = _taskScheduledSlotCount(sched);
            const nFill = _taskTotalFillCount(days);
            const pool = Math.min(nSched, nFill);
            let streak = 0;
            for (let d = ti; d >= 0; d--) {
                const sc = _schedInt(sched, d);
                const row = days[d] || [];
                let unmet = false;
                for (let doi = 0; doi < sc; doi++) {
                    const slotK = _schedSlotIndex(sched, d, doi);
                    if (slotK >= pool && !row[doi]) {
                        unmet = true;
                        break;
                    }
                }
                if (unmet) streak++;
                else break;
            }
            return streak > 0 ? Math.min(streak, 4) : 0;
        },

        dotClass(task, di, doi) {
            const sched = task.scheduled || [];
            const sc = _schedInt(sched, di);
            const isScheduled = doi < sc;
            const row = task.days[di] || [];
            const filled = !!row[doi];
            const poolFlags = poolFilledFlags(task);
            const poolRow = poolFlags[di] || [];
            const poolFill = filled && poolRow[doi];
            const slotK = isScheduled ? _schedSlotIndex(sched, di, doi) : -1;
            const pool = Math.min(
                _taskScheduledSlotCount(sched),
                _taskTotalFillCount(task.days || [])
            );
            const cls = {};

            if (filled) {
                cls.filled = true;
                if (!isScheduled && !poolFill) cls.unscheduled = true;
                return cls;
            }

            if (isScheduled && slotK >= 0 && slotK < pool) {
                cls.filled = true;
                return cls;
            }

            const ti = this.todayIdx;

            if (ti > 6 && isScheduled) {
                cls["overdue-4"] = true;
                return cls;
            }

            if (ti >= 0 && ti <= 6 && di <= ti && isScheduled && slotK >= pool) {
                const lev = this._overdueStreakLevel(task);
                if (lev > 0) {
                    cls["overdue-" + lev] = true;
                    return cls;
                }
            }

            if (!isScheduled) cls.unscheduled = true;

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

        /** Matches server score_helpers pool + bonus model. */
        _progressForTaskList(taskList) {
            return progressForTaskList(taskList);
        },

        cardProgress() {
            const a = this._progressForTaskList(this.card.tasks);
            const b = this._progressForTaskList(this.card.extra_tasks || []);
            const earned = a.earned + b.earned;
            const possible = a.possible + b.possible;
            return possible > 0 ? Math.round((earned / possible) * 100) : 0;
        }
    }));

    /* ── Alpine.js: Routine Day Card (single-day view) ────────── */

    Alpine.data("routineDayCard", (weekKey, areaKey, initialCard, dayIdx) => ({
        card: initialCard,
        dayIdx: dayIdx,
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

        _overdueStreakLevel(task) {
            const ti = this.todayIdx;
            if (ti < 0 || ti > 6) return 0;
            const sched = task.scheduled || [];
            const days = task.days || [];
            const nSched = _taskScheduledSlotCount(sched);
            const nFill = _taskTotalFillCount(days);
            const pool = Math.min(nSched, nFill);
            let streak = 0;
            for (let d = ti; d >= 0; d--) {
                const sc = _schedInt(sched, d);
                const row = days[d] || [];
                let unmet = false;
                for (let doi = 0; doi < sc; doi++) {
                    const slotK = _schedSlotIndex(sched, d, doi);
                    if (slotK >= pool && !row[doi]) {
                        unmet = true;
                        break;
                    }
                }
                if (unmet) streak++;
                else break;
            }
            return streak > 0 ? Math.min(streak, 4) : 0;
        },

        hasDotsForDay(task) {
            const sched = task.scheduled ? task.scheduled[this.dayIdx] : 0;
            const row = task.days[this.dayIdx] || [];
            return sched > 0 || row.length > 0;
        },

        dotClass(task, di, doi) {
            const sched = task.scheduled || [];
            const sc = _schedInt(sched, di);
            const isScheduled = doi < sc;
            const row = task.days[di] || [];
            const filled = !!row[doi];
            const poolFlags = poolFilledFlags(task);
            const poolRow = poolFlags[di] || [];
            const poolFill = filled && poolRow[doi];
            const slotK = isScheduled ? _schedSlotIndex(sched, di, doi) : -1;
            const pool = Math.min(
                _taskScheduledSlotCount(sched),
                _taskTotalFillCount(task.days || [])
            );
            const cls = {};

            if (filled) {
                cls.filled = true;
                if (!isScheduled && !poolFill) cls.unscheduled = true;
                return cls;
            }

            if (isScheduled && slotK >= 0 && slotK < pool) {
                cls.filled = true;
                return cls;
            }

            const ti = this.todayIdx;

            if (ti > 6 && isScheduled) {
                cls["overdue-4"] = true;
                return cls;
            }

            if (ti >= 0 && ti <= 6 && di <= ti && isScheduled && slotK >= pool) {
                const lev = this._overdueStreakLevel(task);
                if (lev > 0) {
                    cls["overdue-" + lev] = true;
                    return cls;
                }
            }

            if (!isScheduled) cls.unscheduled = true;

            return cls;
        },

        async toggleDot(taskIdx, dotIdx) {
            const dots = this.card.tasks[taskIdx].days[this.dayIdx];
            dots[dotIdx] = !dots[dotIdx];
            this._updateScore();
            await api("PATCH",
                `/api/routine-cards/${weekKey}/${areaKey}/toggle`,
                { task: taskIdx, day: this.dayIdx, dot: dotIdx, list: "tasks" }
            );
        },

        async toggleDotExtra(taskIdx, dotIdx) {
            const dots = this.card.extra_tasks[taskIdx].days[this.dayIdx];
            dots[dotIdx] = !dots[dotIdx];
            this._updateScore();
            await api("PATCH",
                `/api/routine-cards/${weekKey}/${areaKey}/toggle`,
                { task: taskIdx, day: this.dayIdx, dot: dotIdx, list: "extra_tasks" }
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

        dayProgress() {
            const di = this.dayIdx;
            let earned = 0, possible = 0;
            const allTasks = [...this.card.tasks, ...(this.card.extra_tasks || [])];
            for (const task of allTasks) {
                earned += earnedByDayForTask(task)[di];
                possible += possibleByDayForTask(task, di);
            }
            return possible > 0 ? Math.round((earned / possible) * 100) : 0;
        },

        _updateScore() {
            const el = document.getElementById("day-score-display");
            if (!el) return;
            const cards = document.querySelectorAll("[x-data]");
            let totalEarned = 0, totalPossible = 0;
            cards.forEach(c => {
                const data = Alpine.$data(c);
                if (data && typeof data.dayProgress === "function") {
                    const di = data.dayIdx;
                    const allTasks = [...data.card.tasks, ...(data.card.extra_tasks || [])];
                    for (const task of allTasks) {
                        totalEarned += earnedByDayForTask(task)[di];
                        totalPossible += possibleByDayForTask(task, di);
                    }
                }
            });
            const pct = totalPossible > 0 ? Math.round((totalEarned / totalPossible) * 100) : 0;
            el.textContent = totalPossible > 0 ? pct + "%" : "—";
        },
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

    /* ── Alpine.js: Fantasy (Sleeper) ─────────────────────────── */

    Alpine.data("fantasyPage", () => ({
        settings: {},
        plan: { trade_ideas: [] },
        lastSync: null,
        snapshot: null,
        tradeSuggestions: null,
        lastTradeRefresh: null,
        lastTradeError: null,
        syncing: false,
        syncMsg: "",
        tradeRefreshing: false,
        tradeRefreshMsg: "",
        newIdea: "",

        init() {
            const el = document.getElementById("fantasy-bootstrap");
            if (el) {
                try {
                    this.applyState(JSON.parse(el.textContent || "{}"));
                } catch (e) {
                    /* ignore */
                }
            }
            this.loadState();
        },

        async loadState() {
            try {
                const res = await fetch("/api/fantasy/state");
                const data = await res.json();
                this.applyState(data);
            } catch (e) {
                /* offline */
            }
        },

        async saveSettings() {
            const res = await api("PUT", "/api/fantasy/settings", this.settings);
            if (res.ok && res.state) this.applyState(res.state);
        },

        async savePlan() {
            const res = await api("PUT", "/api/fantasy/plan", this.plan);
            if (res.ok && res.state) this.applyState(res.state);
        },

        applyState(state) {
            if (!state) return;
            this.settings = Object.assign({}, state.settings || {});
            this.plan = Object.assign({ trade_ideas: [] }, state.plan || {});
            if (!this.plan.trade_ideas) this.plan.trade_ideas = [];
            this.lastSync = state.last_sync || null;
            this.snapshot = state.cached_snapshot || null;
            this.tradeSuggestions = state.trade_suggestions || null;
            this.lastTradeRefresh = state.last_trade_refresh || null;
            this.lastTradeError = state.last_trade_error || null;
        },

        async sync() {
            this.syncing = true;
            this.syncMsg = "";
            try {
                const res = await api("POST", "/api/fantasy/sync", { refresh_trades: true });
                if (res.ok && res.state) {
                    this.applyState(res.state);
                    this.syncMsg = "Synced. Trade ideas updated.";
                    setTimeout(() => { this.syncMsg = ""; }, 5000);
                } else {
                    this.syncMsg = res.error || "Sync failed.";
                }
            } catch (e) {
                this.syncMsg = "Network error.";
            }
            this.syncing = false;
        },

        async refreshTrades() {
            this.tradeRefreshing = true;
            this.tradeRefreshMsg = "";
            try {
                const res = await api("POST", "/api/fantasy/trade-refresh", {});
                if (res.ok && res.state) {
                    this.applyState(res.state);
                    this.tradeRefreshMsg = res.skipped ? "Refresh already running." : "Updated.";
                    setTimeout(() => { this.tradeRefreshMsg = ""; }, 4000);
                } else {
                    if (res.state) this.applyState(res.state);
                    this.tradeRefreshMsg = res.error || "Refresh failed.";
                }
            } catch (e) {
                this.tradeRefreshMsg = "Network error.";
            }
            this.tradeRefreshing = false;
        },

        playerLine(p) {
            if (!p) return "";
            const bits = [p.name];
            if (p.pos) bits.push(p.pos);
            if (p.team) bits.push(p.team);
            if (p.fantasy_value != null) bits.push("≈" + p.fantasy_value);
            return bits.join(" · ");
        },

        recordStr() {
            const s = this.snapshot?.team?.settings;
            if (!s) return "";
            const w = s.wins != null ? s.wins : "—";
            const l = s.losses != null ? s.losses : "—";
            const t = s.ties != null ? s.ties : 0;
            return `${w}-${l}` + (t ? `-${t}` : "");
        },

        fpStr() {
            const s = this.snapshot?.team?.settings;
            if (!s || s.fpts == null) return "";
            let out = String(s.fpts);
            if (s.fpts_decimal != null && s.fpts_decimal !== "") {
                const d = Number(s.fpts_decimal);
                if (!Number.isNaN(d)) out += "." + String(d).padStart(2, "0");
            }
            return out;
        },

        fmtTime(iso) {
            if (!iso) return "";
            try {
                const d = new Date(iso);
                return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
            } catch (e) {
                return iso;
            }
        },

        posTeam(p) {
            if (!p) return "";
            const bits = [p.pos, p.team].filter(Boolean);
            return bits.length ? bits.join(" · ") : "";
        },

        async addIdea() {
            const text = (this.newIdea || "").trim();
            if (!text) return;
            const res = await api("POST", "/api/fantasy/trade-ideas", { text });
            if (res.ok && res.state) {
                this.applyState(res.state);
                this.newIdea = "";
            }
        },

        async removeIdea(id) {
            const res = await fetch("/api/fantasy/trade-ideas/" + encodeURIComponent(id), { method: "DELETE" });
            const data = await res.json();
            if (data.ok && data.state) this.applyState(data.state);
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
