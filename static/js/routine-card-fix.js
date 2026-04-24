(function () {
    function schedInt(sched, dayIdx) {
        if (typeof _schedInt === "function") return _schedInt(sched, dayIdx);
        const raw = (sched || [])[dayIdx];
        const n = Number(raw);
        return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
    }

    function schedCount(sched) {
        if (typeof _taskScheduledSlotCount === "function") return _taskScheduledSlotCount(sched);
        let n = 0;
        for (let dayIdx = 0; dayIdx < 7; dayIdx++) n += schedInt(sched, dayIdx);
        return n;
    }

    function fillCount(days) {
        if (typeof _taskTotalFillCount === "function") return _taskTotalFillCount(days || []);
        let n = 0;
        for (const row of (days || []).slice(0, 7)) {
            for (const val of (row || [])) if (val) n += 1;
        }
        return n;
    }

    function slotIndex(sched, dayIdx, dotIdx) {
        if (typeof _schedSlotIndex === "function") return _schedSlotIndex(sched, dayIdx, dotIdx);
        let k = 0;
        for (let d = 0; d < dayIdx; d++) k += schedInt(sched, d);
        return k + dotIdx;
    }

    function fixedDotClass(task, dayIdx, dotIdx) {
        const sched = task.scheduled || [];
        const isScheduled = dotIdx < schedInt(sched, dayIdx);
        const row = task.days[dayIdx] || [];
        const filled = !!row[dotIdx];
        const cls = {};

        if (filled) {
            cls.filled = true;
            if (!isScheduled) cls.unscheduled = true;
            return cls;
        }

        const nSched = schedCount(sched);
        const nFill = fillCount(task.days || []);
        const pool = Math.min(nSched, nFill);
        const freq = Number(task.freq || 0);

        if (freq > 0 && freq < 1 && nSched > 0 && nFill === 0) {
            cls["overdue-1"] = true;
            return cls;
        }

        const todayIdx = this.todayIdx;
        if (todayIdx > 6 && isScheduled) {
            cls["overdue-4"] = true;
            return cls;
        }

        const slotK = isScheduled ? slotIndex(sched, dayIdx, dotIdx) : -1;
        if (todayIdx >= 0 && todayIdx <= 6 && dayIdx <= todayIdx && isScheduled && slotK >= pool) {
            const lev = typeof this._overdueStreakLevel === "function" ? this._overdueStreakLevel(task) : 1;
            if (lev > 0) {
                cls["overdue-" + lev] = true;
                return cls;
            }
        }

        if (!isScheduled) cls.unscheduled = true;
        return cls;
    }

    function patchAllRoutineCards() {
        if (!window.Alpine) return;
        document.querySelectorAll("[x-data]").forEach(function (el) {
            let data;
            try { data = window.Alpine.$data(el); } catch (_) { return; }
            if (!data || !data.card || typeof data.dotClass !== "function") return;
            if (data.__routineCardDisplayFixApplied) return;
            data.dotClass = fixedDotClass;
            data.__routineCardDisplayFixApplied = true;
        });
    }

    document.addEventListener("alpine:initialized", function () { setTimeout(patchAllRoutineCards, 0); });
    document.addEventListener("click", function () { setTimeout(patchAllRoutineCards, 0); });
    window.addEventListener("load", function () { setTimeout(patchAllRoutineCards, 50); });
})();
