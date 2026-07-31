/* Routine card performance patch
 *
 * The pool/overdue behavior added to routines is useful, but the original
 * Alpine methods recalculated the same weekly task state for every dot render.
 * On a full routine page that becomes extremely expensive. This override keeps
 * the same behavior while caching each task's derived state until its dots change.
 */
(function () {
    const BONUS_RATIO = 0.4;
    const taskCache = new WeakMap();

    function schedInt(sched, di) {
        if (!sched || di < 0 || di > 6) return 0;
        const s = Number(sched[di]);
        return Number.isFinite(s) ? Math.max(0, Math.floor(s)) : 0;
    }

    function taskWeight(task) {
        const w = Number(task && task.weight);
        return Number.isFinite(w) && w > 0 ? w : 1;
    }

    function signatureForTask(task) {
        const sched = task.scheduled || [];
        const days = task.days || [];
        const prev = Number(task.prev_week_overdue_streak) || 0;
        let sig = `${task.weight || 1}|${prev}|${sched.join(',')}|`;
        for (let di = 0; di < 7; di++) {
            const row = days[di] || [];
            sig += row.map(v => (v ? '1' : '0')).join('') + ';';
        }
        return sig;
    }

    function buildTaskState(task) {
        const sched = task.scheduled || [];
        const days = task.days || [];
        const w = taskWeight(task);
        const scheduledPrefix = [0, 0, 0, 0, 0, 0, 0];
        let nSched = 0;
        let nFill = 0;
        let extraPossible = 0;

        for (let di = 0; di < 7; di++) {
            scheduledPrefix[di] = nSched;
            const sc = schedInt(sched, di);
            nSched += sc;
            const row = days[di] || [];
            for (let i = 0; i < row.length; i++) {
                if (row[i]) nFill++;
            }
            if (row.length > sc) extraPossible += (row.length - sc) * w * BONUS_RATIO;
        }

        const pool = Math.min(nSched, nFill);
        let poolLeft = pool;
        const poolFlags = [];
        const earnedByDay = [0, 0, 0, 0, 0, 0, 0];
        const possibleByDay = [0, 0, 0, 0, 0, 0, 0];

        for (let di = 0; di < 7; di++) {
            const sc = schedInt(sched, di);
            const row = days[di] || [];
            possibleByDay[di] = (sc * w) + (Math.max(0, row.length - sc) * w * BONUS_RATIO);
            poolFlags[di] = [];
            for (let i = 0; i < row.length; i++) {
                if (row[i] && poolLeft > 0) {
                    poolFlags[di][i] = true;
                    earnedByDay[di] += w;
                    poolLeft--;
                } else {
                    poolFlags[di][i] = false;
                    if (row[i]) earnedByDay[di] += w * BONUS_RATIO;
                }
            }
        }

        return { sched, days, w, nSched, nFill, pool, scheduledPrefix, poolFlags, earnedByDay, possibleByDay, possibleTotal: (nSched * w) + extraPossible };
    }

    function stateForTask(task) {
        if (!task || typeof task !== 'object') return buildTaskState({});
        const sig = signatureForTask(task);
        const cached = taskCache.get(task);
        if (cached && cached.sig === sig) return cached.state;
        const state = buildTaskState(task);
        taskCache.set(task, { sig, state });
        return state;
    }

    function scheduledSlotIndex(state, di, doi) {
        return (state.scheduledPrefix[di] || 0) + doi;
    }

    function overdueStreakLevel(task, todayIdx) {
        if (todayIdx < 0 || todayIdx > 6) return 0;
        const state = stateForTask(task);
        const inherited = Math.max(0, Number(task.prev_week_overdue_streak) || 0);
        let streak = 0;
        let brokeWithinWeek = false;

        for (let d = todayIdx; d >= 0; d--) {
            const sc = schedInt(state.sched, d);
            if (sc === 0) continue;
            const row = state.days[d] || [];
            let unmet = false;
            for (let doi = 0; doi < sc; doi++) {
                const slotK = scheduledSlotIndex(state, d, doi);
                if (slotK >= state.pool && !row[doi]) {
                    unmet = true;
                    break;
                }
            }
            if (unmet) streak++;
            else { brokeWithinWeek = true; break; }
        }

        if (!brokeWithinWeek) streak += inherited;
        return streak > 0 ? Math.min(streak, 4) : 0;
    }

    function dotClassFor(task, di, doi, todayIdx) {
        const state = stateForTask(task);
        const sc = schedInt(state.sched, di);
        const isScheduled = doi < sc;
        const row = state.days[di] || [];
        const filled = !!row[doi];
        const poolFill = filled && !!((state.poolFlags[di] || [])[doi]);
        const slotK = isScheduled ? scheduledSlotIndex(state, di, doi) : -1;
        const cls = {};

        if (filled) {
            cls.filled = true;
            if (!isScheduled && !poolFill) cls.unscheduled = true;
            return cls;
        }

        if (isScheduled && slotK >= 0 && slotK < state.pool) {
            cls.filled = true;
            return cls;
        }

        if (todayIdx > 6 && isScheduled) {
            cls['overdue-4'] = true;
            return cls;
        }

        if (todayIdx >= 0 && todayIdx <= 6 && di <= todayIdx && isScheduled && slotK >= state.pool) {
            const lev = overdueStreakLevel(task, todayIdx);
            if (lev > 0) {
                cls['overdue-' + lev] = true;
                return cls;
            }
        }

        if (!isScheduled) cls.unscheduled = true;
        return cls;
    }

    function taskListProgress(taskList) {
        let earned = 0;
        let possible = 0;
        for (const task of taskList || []) {
            const state = stateForTask(task);
            earned += state.earnedByDay.reduce((a, b) => a + b, 0);
            possible += state.possibleTotal;
        }
        return { earned, possible };
    }

    function dayProgressForCard(card, dayIdx) {
        let earned = 0;
        let possible = 0;
        const allTasks = [...(card.tasks || []), ...(card.extra_tasks || [])];
        for (const task of allTasks) {
            const state = stateForTask(task);
            earned += state.earnedByDay[dayIdx] || 0;
            possible += state.possibleByDay[dayIdx] || 0;
        }
        return { earned, possible };
    }

    function todayIndex(card) {
        const ws = new Date(card.week_start + 'T00:00:00');
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        const diff = Math.floor((now - ws) / 86400000);
        if (diff < 0) return -1;
        if (diff > 6) return 7;
        return diff;
    }

    document.addEventListener('alpine:init', () => {
        Alpine.data('routineCard', (weekKey, areaKey, initialCard) => ({
            card: initialCard,
            newExtraName: '',

            init() {
                if (!Array.isArray(this.card.extra_tasks)) this.card.extra_tasks = [];
            },

            get todayIdx() { return todayIndex(this.card); },
            _overdueStreakLevel(task) { return overdueStreakLevel(task, this.todayIdx); },
            dotClass(task, di, doi) { return dotClassFor(task, di, doi, this.todayIdx); },

            async toggleDot(taskIdx, dayIdx, dotIdx) {
                const dots = this.card.tasks[taskIdx].days[dayIdx];
                dots[dotIdx] = !dots[dotIdx];
                await api('PATCH', `/api/routine-cards/${weekKey}/${areaKey}/toggle`, { task: taskIdx, day: dayIdx, dot: dotIdx, list: 'tasks' });
            },

            async toggleDotExtra(taskIdx, dayIdx, dotIdx) {
                const dots = this.card.extra_tasks[taskIdx].days[dayIdx];
                dots[dotIdx] = !dots[dotIdx];
                await api('PATCH', `/api/routine-cards/${weekKey}/${areaKey}/toggle`, { task: taskIdx, day: dayIdx, dot: dotIdx, list: 'extra_tasks' });
            },

            async addExtraRow() {
                const name = (this.newExtraName || '').trim();
                if (!name) return;
                const res = await api('POST', `/api/routine-cards/${weekKey}/${areaKey}/extra-task`, { name });
                if (res.ok && res.extra_tasks) {
                    this.card.extra_tasks = res.extra_tasks;
                    this.newExtraName = '';
                }
            },

            async removeExtraRow(taskIdx) {
                const res = await fetch(`/api/routine-cards/${weekKey}/${areaKey}/extra-task/${taskIdx}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.ok) this.card.extra_tasks.splice(taskIdx, 1);
            },

            async saveNotes() {
                await api('PUT', `/api/routine-cards/${weekKey}/${areaKey}/notes`, { notes: this.card.notes });
            },

            _progressForTaskList(taskList) { return taskListProgress(taskList); },
            cardProgress() {
                const a = taskListProgress(this.card.tasks || []);
                const b = taskListProgress(this.card.extra_tasks || []);
                const possible = a.possible + b.possible;
                return possible > 0 ? Math.round(((a.earned + b.earned) / possible) * 100) : 0;
            }
        }));

        Alpine.data('routineDayCard', (weekKey, areaKey, initialCard, dayIdx) => ({
            card: initialCard,
            dayIdx: dayIdx,
            newExtraName: '',

            init() {
                if (!Array.isArray(this.card.extra_tasks)) this.card.extra_tasks = [];
            },

            get todayIdx() { return todayIndex(this.card); },
            _overdueStreakLevel(task) { return overdueStreakLevel(task, this.todayIdx); },
            hasDotsForDay(task) {
                const sched = task.scheduled ? task.scheduled[this.dayIdx] : 0;
                const row = task.days[this.dayIdx] || [];
                return sched > 0 || row.length > 0;
            },
            dotClass(task, di, doi) { return dotClassFor(task, di, doi, this.todayIdx); },

            async toggleDot(taskIdx, dotIdx) {
                const dots = this.card.tasks[taskIdx].days[this.dayIdx];
                dots[dotIdx] = !dots[dotIdx];
                this._updateScore();
                await api('PATCH', `/api/routine-cards/${weekKey}/${areaKey}/toggle`, { task: taskIdx, day: this.dayIdx, dot: dotIdx, list: 'tasks' });
            },

            async toggleDotExtra(taskIdx, dotIdx) {
                const dots = this.card.extra_tasks[taskIdx].days[this.dayIdx];
                dots[dotIdx] = !dots[dotIdx];
                this._updateScore();
                await api('PATCH', `/api/routine-cards/${weekKey}/${areaKey}/toggle`, { task: taskIdx, day: this.dayIdx, dot: dotIdx, list: 'extra_tasks' });
            },

            async addExtraRow() {
                const name = (this.newExtraName || '').trim();
                if (!name) return;
                const res = await api('POST', `/api/routine-cards/${weekKey}/${areaKey}/extra-task`, { name });
                if (res.ok && res.extra_tasks) {
                    this.card.extra_tasks = res.extra_tasks;
                    this.newExtraName = '';
                    this._updateScore();
                }
            },

            async removeExtraRow(taskIdx) {
                const res = await fetch(`/api/routine-cards/${weekKey}/${areaKey}/extra-task/${taskIdx}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.ok) {
                    this.card.extra_tasks.splice(taskIdx, 1);
                    this._updateScore();
                }
            },

            async saveNotes() {
                await api('PUT', `/api/routine-cards/${weekKey}/${areaKey}/notes`, { notes: this.card.notes });
            },

            dayProgress() {
                const p = dayProgressForCard(this.card, this.dayIdx);
                return p.possible > 0 ? Math.round((p.earned / p.possible) * 100) : 0;
            },

            _updateScore() {
                const el = document.getElementById('day-score-display');
                if (!el) return;
                const cards = document.querySelectorAll('[x-data]');
                let totalEarned = 0;
                let totalPossible = 0;
                cards.forEach(c => {
                    const data = Alpine.$data(c);
                    if (data && data.card && typeof data.dayIdx === 'number') {
                        const p = dayProgressForCard(data.card, data.dayIdx);
                        totalEarned += p.earned;
                        totalPossible += p.possible;
                    }
                });
                const pct = totalPossible > 0 ? Math.round((totalEarned / totalPossible) * 100) : 0;
                el.textContent = totalPossible > 0 ? pct + '%' : '—';
            }
        }));
    });
})();
