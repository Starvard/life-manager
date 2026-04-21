/* ── API Helpers ───────────────────────────────────────────────── */

async function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    let res;
    try {
        res = await fetch(url, opts);
    } catch (e) {
        const msg = e && e.message ? e.message : "Request failed";
        return { ok: false, error: "Network error: " + msg };
    }
    const text = await res.text();
    let data;
    try {
        data = text ? JSON.parse(text) : {};
    } catch (e) {
        const snippet = (text || "").replace(/\s+/g, " ").trim().slice(0, 160);
        return {
            ok: false,
            error: snippet
                ? `Server error (${res.status}): ${snippet}`
                : `Server returned ${res.status} with non-JSON body`,
        };
    }
    return data;
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

    Alpine.data("budgetPage", (initialTxns, initialReport, initialPlan, initialCategories, currentMonth, months, initialOverview, initialBudgets, budgetCategoryList, initialPlaidItems, plaidConfigured, initialPlaidStatus) => ({
        transactions: initialTxns || [],
        report: initialReport || { total_income: 0, total_expenses: 0, net: 0, transaction_count: 0, categories: [], category_status: [], overall_status: {} },
        plan: initialPlan || { month: currentMonth, sections: {}, notes: "" },
        allCategories: initialCategories || [],
        overview: initialOverview || {},
        currentMonth: currentMonth,
        allMonths: months || [],
        view: "status",
        searchQuery: "",
        filterCategory: "",
        filteredTxns: [],
        duplicates: [],
        editingCatId: null,
        editCatValue: "",
        importing: false,
        importMsg: "",
        errorMsg: "",
        importReplaceAll: false,
        budgetLimits: Object.assign({}, initialBudgets || {}),
        budgetCategoryList: budgetCategoryList || [],
        plaidItems: initialPlaidItems || [],
        plaidConfigured: !!plaidConfigured,
        plaidStatus: initialPlaidStatus || {
            configured: !!plaidConfigured,
            env: "sandbox",
            has_client_id: false,
            has_secret: false,
            has_redirect_uri: false,
            client_id_preview: "",
            redirect_uri: "",
            sources: { client_id: "missing", secret: "missing", env: "missing", redirect_uri: "missing" },
        },
        plaidForm: { client_id: "", secret: "", env: "sandbox", redirect_uri: "" },
        savingCreds: false,
        plaidCredMsg: "",
        linking: false,
        syncing: false,
        recategorizing: false,
        csvMsg: "",
        rules: [],
        newRuleKeyword: "",
        newRuleCategory: "",

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
            this.loadRules();
            // Seed the credentials form with non-secret metadata so env is preselected.
            this.plaidForm.env = (this.plaidStatus && this.plaidStatus.env) || "sandbox";
            this.plaidForm.redirect_uri = (this.plaidStatus && this.plaidStatus.redirect_uri) || "";
            if (this.allMonths.indexOf(this.currentMonth) === -1) {
                this.allMonths = this.allMonths.concat([this.currentMonth]).sort();
            }
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
            // Pick up the newly learned keyword rule and refresh the per-category status.
            await this.loadRules();
            await this.refreshReport();
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

        /* Budget over/under helpers */

        overallStatus() {
            return this.report.overall_status || { has_budget: false, total_budget: 0, total_spent: 0, total_remaining: 0, percent: 0, over: false };
        },

        spentForCategory(cat) {
            const row = (this.report.category_status || []).find(r => r.category === cat);
            return row ? row.spent : 0;
        },

        async saveBudgets() {
            // Strip empty/NaN entries before saving
            const cleaned = {};
            for (const [k, v] of Object.entries(this.budgetLimits)) {
                if (v == null || v === "" || Number.isNaN(Number(v))) continue;
                const num = Number(v);
                if (num > 0) cleaned[k] = num;
            }
            this.budgetLimits = cleaned;
            await api("PUT", "/api/budget/budgets", { limits: cleaned });
            await this.refreshReport();
        },

        async refreshReport() {
            const res = await fetch(`/api/budget/report?month=${this.currentMonth}`);
            if (res.ok) this.report = await res.json();
        },

        /* Plaid credentials */

        canSaveCreds() {
            const hasClient = (this.plaidForm.client_id || "").trim().length > 0
                || this.plaidStatus.has_client_id;
            const hasSecret = (this.plaidForm.secret || "").trim().length > 0
                || this.plaidStatus.has_secret;
            const typedSomething = (this.plaidForm.client_id || "").trim()
                || (this.plaidForm.secret || "").trim()
                || (this.plaidForm.redirect_uri || "").trim();
            return !!(hasClient && hasSecret && typedSomething);
        },

        async savePlaidCredentials() {
            this.savingCreds = true;
            this.plaidCredMsg = "";
            try {
                // Only send fields the user actually filled in, so empty form
                // values can never wipe an already-saved secret on the server.
                const body = {};
                const ci = (this.plaidForm.client_id || "").trim();
                const sk = (this.plaidForm.secret || "").trim();
                const ru = (this.plaidForm.redirect_uri || "").trim();
                const ev = (this.plaidForm.env || "").trim();
                if (ci) body.client_id = ci;
                if (sk) body.secret = sk;
                if (ru) body.redirect_uri = ru;
                if (ev) body.env = ev;
                const res = await api("PUT", "/api/budget/plaid/credentials", body);
                if (res && res.ok) {
                    this.plaidStatus = {
                        configured: res.configured,
                        env: res.env,
                        has_client_id: res.has_client_id,
                        has_secret: res.has_secret,
                        has_redirect_uri: res.has_redirect_uri,
                        client_id_preview: ci ? ci.slice(0, 6) + "…" : this.plaidStatus.client_id_preview,
                        redirect_uri: ru || this.plaidStatus.redirect_uri,
                        sources: res.sources,
                    };
                    this.plaidConfigured = res.configured;
                    // Wipe the secret from memory only if we actually sent one.
                    if (sk) this.plaidForm.secret = "";
                    this.plaidCredMsg = res.configured
                        ? "Saved. Plaid is now ready."
                        : "Saved. Still missing fields — check the diagnostic strip above.";
                    setTimeout(() => { this.plaidCredMsg = ""; }, 6000);
                } else {
                    this.plaidCredMsg = (res && res.error) || "Could not save credentials.";
                }
            } catch (e) {
                this.plaidCredMsg = "Save error.";
            }
            this.savingCreds = false;
        },

        async forgetPlaidSecret() {
            if (!confirm("Delete the saved Plaid secret? You'll need to paste it again to re-enable Plaid.")) return;
            const res = await fetch(
                "/api/budget/plaid/credentials?field=PLAID_SECRET",
                { method: "DELETE" }
            );
            const data = await res.json();
            if (data) {
                await this.refreshPlaidStatus();
                this.plaidCredMsg = "Saved secret removed.";
                setTimeout(() => { this.plaidCredMsg = ""; }, 4000);
            }
        },

        async clearPlaidCredentials() {
            if (!confirm("Remove Plaid credentials saved by this app? Env / .env / Cursor secrets (if any) will still apply.")) return;
            const res = await fetch("/api/budget/plaid/credentials", { method: "DELETE" });
            const data = await res.json();
            if (data) {
                this.plaidConfigured = !!data.configured;
                this.plaidStatus.configured = !!data.configured;
                this.plaidStatus.sources = data.sources || this.plaidStatus.sources;
                // Re-fetch full status so UI reflects env/has_* correctly
                await this.refreshPlaidStatus();
                this.plaidCredMsg = "Cleared app-saved credentials.";
                setTimeout(() => { this.plaidCredMsg = ""; }, 4000);
            }
        },

        async refreshPlaidStatus() {
            try {
                const res = await fetch("/api/budget/plaid/credentials");
                if (res.ok) {
                    const data = await res.json();
                    this.plaidStatus = {
                        configured: data.configured,
                        env: data.env,
                        has_client_id: data.has_client_id,
                        has_secret: data.has_secret,
                        has_redirect_uri: data.has_redirect_uri,
                        client_id_preview: data.client_id_preview || "",
                        redirect_uri: data.redirect_uri || "",
                        sources: data.sources,
                    };
                    this.plaidConfigured = !!data.configured;
                }
            } catch (e) { /* ignore */ }
        },

        /* Plaid */

        async startPlaidLink() {
            if (!this.plaidConfigured) return;
            if (typeof window.Plaid === "undefined") {
                this.errorMsg = "Plaid SDK hasn't loaded yet. Please reload the page.";
                setTimeout(() => { this.errorMsg = ""; }, 4000);
                return;
            }
            this.linking = true;
            const res = await api("POST", "/api/budget/plaid/link-token", {});
            if (!res.ok) {
                this.linking = false;
                this.errorMsg = res.error || "Couldn't create Plaid Link token.";
                setTimeout(() => { this.errorMsg = ""; }, 6000);
                return;
            }
            const self = this;
            const handler = window.Plaid.create({
                token: res.link_token,
                onSuccess: async (publicToken, metadata) => {
                    const inst = (metadata && metadata.institution && metadata.institution.name) || "";
                    const ex = await api("POST", "/api/budget/plaid/exchange", {
                        public_token: publicToken,
                        institution_name: inst,
                    });
                    if (ex && ex.ok) {
                        self.plaidItems.push({
                            item_id: ex.item_id,
                            institution_name: ex.institution_name,
                            accounts: ex.accounts || [],
                            last_sync: null,
                        });
                        self.importMsg = `Connected ${ex.institution_name}. Syncing…`;
                        setTimeout(() => { self.importMsg = ""; }, 4000);
                        await self.syncPlaid();
                    } else {
                        self.errorMsg = (ex && ex.error) || "Exchange failed.";
                        setTimeout(() => { self.errorMsg = ""; }, 6000);
                    }
                },
                onExit: () => { self.linking = false; },
            });
            handler.open();
            // Note: Plaid's modal handles "linking" state itself; we reset on exit.
        },

        async syncPlaid() {
            if (this.syncing) return;
            this.syncing = true;
            try {
                const res = await api("POST", "/api/budget/plaid/sync", {});
                if (res && res.ok) {
                    const parts = [];
                    if (res.added) parts.push(`${res.added} new`);
                    if (res.modified) parts.push(`${res.modified} updated`);
                    if (res.removed) parts.push(`${res.removed} removed`);
                    this.importMsg = parts.length ? `Synced: ${parts.join(", ")}.` : "Already up to date.";
                    setTimeout(() => { this.importMsg = ""; }, 5000);
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    this.errorMsg = (res && res.error) || "Sync failed.";
                    setTimeout(() => { this.errorMsg = ""; }, 6000);
                }
            } catch (e) {
                this.errorMsg = "Sync error.";
                setTimeout(() => { this.errorMsg = ""; }, 4000);
            }
            this.syncing = false;
        },

        async removePlaidItem(item) {
            if (!confirm(`Disconnect ${item.institution_name}? Imported transactions stay.`)) return;
            await fetch(`/api/budget/plaid/items/${encodeURIComponent(item.item_id)}`, { method: "DELETE" });
            this.plaidItems = this.plaidItems.filter(p => p.item_id !== item.item_id);
        },

        async recategorizeAll() {
            this.recategorizing = true;
            try {
                const res = await api("POST", "/api/budget/recategorize", {});
                if (res && res.ok) {
                    this.importMsg = `Recategorized ${res.changed} transaction(s).`;
                    setTimeout(() => { this.importMsg = ""; }, 4000);
                    setTimeout(() => window.location.reload(), 800);
                }
            } catch (e) { /* ignore */ }
            this.recategorizing = false;
        },

        /* CSV upload */

        async uploadCsv(ev) {
            const input = ev.target;
            const files = (input && input.files) ? Array.from(input.files) : [];
            if (files.length === 0) return;
            this.csvMsg = "Uploading…";
            const form = new FormData();
            for (const f of files) form.append("files", f);
            try {
                const res = await fetch("/api/budget/import-csv", { method: "POST", body: form });
                const data = await res.json();
                if (data && data.ok) {
                    this.csvMsg = `Imported ${data.new} new / ${data.parsed} parsed from ${files.length} file(s).`;
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    this.csvMsg = (data && data.error) || "Upload failed.";
                }
            } catch (e) {
                this.csvMsg = "Upload error.";
            }
            input.value = "";
        },

        /* Keyword rules */

        async loadRules() {
            try {
                const res = await api("GET", "/api/budget/rules");
                this.rules = (res && res.rules) || [];
            } catch (e) { /* ignore */ }
        },

        async addRule() {
            const k = (this.newRuleKeyword || "").trim();
            const c = (this.newRuleCategory || "").trim();
            if (!k || !c) return;
            const res = await api("POST", "/api/budget/rules", { keyword: k, category: c });
            if (res && res.ok) {
                this.rules = res.rules;
                this.newRuleKeyword = "";
                this.newRuleCategory = "";
            }
        },

        async deleteRule(r) {
            const res = await fetch(`/api/budget/rules/${encodeURIComponent(r.keyword)}`, { method: "DELETE" });
            const data = await res.json();
            if (data) this.rules = data.rules || [];
        },
    }));

    /* ── Alpine.js: Fantasy (Sleeper) ─────────────────────────── */

    Alpine.data("fantasyPage", () => ({
        settings: {},
        plan: { trade_ideas: [], rebuild_horizon_years: 3 },
        rebuildBoard: { order: [], assets: {} },
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
                } catch (e) { /* ignore */ }
            }
            this.loadState();
        },

        async loadState() {
            try {
                const res = await fetch("/api/fantasy/state");
                const data = await res.json();
                this.applyState(data);
            } catch (e) { /* offline */ }
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
            this.settings = Object.assign({ trade_strategy: "rebuild" }, state.settings || {});
            this.plan = Object.assign({ trade_ideas: [], rebuild_horizon_years: 3 }, state.plan || {});
            if (!this.plan.trade_ideas) this.plan.trade_ideas = [];
            if (this.plan.rebuild_horizon_years == null) this.plan.rebuild_horizon_years = 3;
            this.rebuildBoard = state.rebuild_board || { order: [], assets: {} };
            if (!this.rebuildBoard.assets) this.rebuildBoard.assets = {};
            if (!this.rebuildBoard.order) this.rebuildBoard.order = [];
            this.lastSync = state.last_sync || null;
            this.snapshot = state.cached_snapshot || null;
            this.tradeSuggestions = state.trade_suggestions || null;
            this.lastTradeRefresh = state.last_trade_refresh || null;
            this.lastTradeError = state.last_trade_error || null;
        },

        async sync() {
            this.syncing = true;
            this.syncMsg = "";
            const res = await api("POST", "/api/fantasy/sync", { refresh_trades: true });
            if (res.state) this.applyState(res.state);
            if (res.ok) {
                this.syncMsg = "Synced. Trade ideas updated.";
                setTimeout(() => { this.syncMsg = ""; }, 5000);
            } else {
                this.syncMsg = res.error || "Sync failed.";
            }
            this.syncing = false;
        },

        async refreshTrades() {
            this.tradeRefreshing = true;
            this.tradeRefreshMsg = "";
            const res = await api("POST", "/api/fantasy/trade-refresh", {});
            if (res.state) this.applyState(res.state);
            if (res.ok) {
                this.tradeRefreshMsg = res.skipped ? "Refresh already running." : "Updated.";
                setTimeout(() => { this.tradeRefreshMsg = ""; }, 4000);
            } else {
                this.tradeRefreshMsg = this._fantasyErr(res.error) || "Refresh failed.";
            }
            this.tradeRefreshing = false;
        },

        _fantasyErr(code) {
            if (!code) return "";
            const m = {
                "no snapshot": "Sync from Sleeper first, then refresh trades.",
                "stale snapshot": "Tap Sync once — league data was saved in an older format.",
                "bad snapshot": "Re-sync from Sleeper and try again.",
            };
            return m[code] || code;
        },

        playerLabelForAsset(aid) {
            const a = this.rebuildBoard.assets[aid];
            if (!a) return "";
            if (a.kind === "pick") return a.label || aid;
            const pl = this._findPlayer(a.player_id);
            if (!pl) return "Player " + a.player_id;
            const bits = [pl.name];
            if (pl.pos) bits.push(pl.pos);
            if (pl.team) bits.push(pl.team);
            if (a.slot) bits.push(a.slot);
            return bits.join(" · ");
        },

        groupedAssets() {
            const order = (this.rebuildBoard && this.rebuildBoard.order) || [];
            const assets = (this.rebuildBoard && this.rebuildBoard.assets) || {};
            const seen = new Map();
            for (const aid of order) {
                const a = assets[aid];
                if (!a) continue;
                const key = a.group || "Other";
                if (!seen.has(key)) seen.set(key, []);
                seen.get(key).push(aid);
            }
            return Array.from(seen.entries()).map(([title, ids]) => ({ title, ids }));
        },

        hasPicks() {
            const assets = (this.rebuildBoard && this.rebuildBoard.assets) || {};
            for (const k in assets) {
                if (assets[k] && assets[k].kind === "pick") return true;
            }
            return false;
        },

        currentLabel(aid) {
            const a = this.rebuildBoard.assets[aid];
            if (!a) return "";
            if (a.kind === "pick") return a.label || aid;
            const pl = this._findPlayer(a.player_id);
            return pl ? pl.name : "Player " + a.player_id;
        },

        currentMeta(aid) {
            const a = this.rebuildBoard.assets[aid];
            if (!a) return "";
            if (a.kind === "pick") {
                const bits = [];
                if (a.season) bits.push(a.season);
                if (a.round) bits.push("R" + a.round);
                if (a.original_team_label) bits.push("from " + a.original_team_label);
                return bits.join(" · ");
            }
            const pl = this._findPlayer(a.player_id);
            const bits = [];
            if (pl && pl.pos) bits.push(pl.pos);
            if (pl && pl.team) bits.push(pl.team);
            if (a.slot) bits.push(a.slot);
            return bits.join(" · ");
        },

        canResetAuto(aid) {
            const a = this.rebuildBoard.assets[aid];
            if (!a) return false;
            const desired = (a.desired_upgrade || "").trim();
            const auto = (a._auto_desired_upgrade || "").trim();
            if (!auto) return false;
            return desired !== auto;
        },

        async resetToAuto(aid) {
            const a = this.rebuildBoard.assets[aid];
            if (!a) return;
            const auto = a._auto_desired_upgrade || "";
            await this.patchRebuildUpgrade(aid, auto);
        },

        _findPlayer(pid) {
            if (!this.snapshot || !pid) return null;
            const id = String(pid);
            for (const row of this.snapshot.starters || []) {
                if (!row.empty && row.player && String(row.player.id) === id) return row.player;
            }
            for (const list of [this.snapshot.bench, this.snapshot.reserve, this.snapshot.taxi]) {
                for (const p of list || []) {
                    if (String(p.id) === id) return p;
                }
            }
            return null;
        },

        async patchRebuildUpgrade(aid, text) {
            const res = await api("PATCH", "/api/fantasy/rebuild-board", {
                assets: { [aid]: { desired_upgrade: text } },
            });
            if (res.ok && res.state) this.applyState(res.state);
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
            const res = await api("DELETE", "/api/fantasy/trade-ideas/" + encodeURIComponent(id));
            if (res.ok && res.state) this.applyState(res.state);
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
