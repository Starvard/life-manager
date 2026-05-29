(() => {
  const STORE_KEY = 'life-manager:routines-v2';
  const DAY = 86400000;
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const app = document.getElementById('app');
  if (!app) return;
  const pad = n => String(n).padStart(2, '0');
  const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; };
  const nowIso = () => new Date().toISOString();
  const parse = s => new Date(String(s || '').slice(0, 10) + 'T00:00:00');
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const addDays = (s,n) => { const d = parse(s); d.setDate(d.getDate()+n); return iso(d); };
  const addMonths = (s,n) => { const d = parse(s); d.setMonth(d.getMonth()+n); return iso(d); };
  const diff = (a,b) => Math.round((parse(a)-parse(b))/DAY);
  const weekStart = s => { const d = parse(s); d.setDate(d.getDate()-((d.getDay()+6)%7)); return iso(d); };
  const esc = s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const nice = s => parse(s).toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric' });
  const state = () => JSON.parse(localStorage.getItem(STORE_KEY) || '{"version":1,"routines":[],"completions":[]}');
  const save = s => localStorage.setItem(STORE_KEY, JSON.stringify(s));
  const comps = (s,id) => (s.completions || []).filter(c => c.routine_id === id && !c.deleted).sort((a,b)=>String(a.completed_at).localeCompare(String(b.completed_at)));
  const todayComps = (s,id,today) => comps(s,id).filter(c => c.completed_date === today);
  const latest = (s,id) => { const c = comps(s,id); return c[c.length-1]; };
  const weekComps = (s,id,today) => { const a = weekStart(today), b = addDays(a,6); return comps(s,id).filter(c => c.completed_date >= a && c.completed_date <= b); };
  const label = r => { const v = Number(r.repeat_value || 1); if (r.repeat_type === 'daily') return 'Daily'; if (r.repeat_type === 'times_per_day') return `${v}/day`; if (r.repeat_type === 'times_per_week') return `${v}/week`; if (r.repeat_type === 'every_n_days') return v === 1 ? 'Daily' : `Every ${v} days`; if (r.repeat_type === 'every_n_months') return v === 1 ? 'Monthly' : `Every ${v} months`; if (r.repeat_type === 'weekdays') return (r.days_of_week || []).map(d => weekdays[d]).join(', '); return 'Routine'; };
  const status = (today,due) => { const d = diff(today,due); if (d === 0) return 'Today'; if (d === 1) return '1 day overdue'; if (d > 1) return `${d} days overdue`; if (d === -1) return 'Tomorrow'; if (d > -31) return `In ${-d} days`; return nice(due); };
  const dailyType = r => r.repeat_type === 'daily' || r.repeat_type === 'times_per_day';
  function nextWeekday(days,today,after=false){ const set=(days||[]).length?days:[0]; for(let o=after?1:0;o<=14;o++){const d=addDays(today,o); if(set.includes((parse(d).getDay()+6)%7)) return d;} return today; }
  function lastWeekday(days,today){ const set=(days||[]).length?days:[0]; for(let o=0;o<=14;o++){const d=addDays(today,-o); if(set.includes((parse(d).getDay()+6)%7)) return d;} return today; }
  function item(s,r,today){
    const tc = todayComps(s,r.id,today), last = latest(s,r.id), lastDate = last && last.completed_date;
    let bucket='due', rank=1, due=today, text='Today', side=dailyType(r)?'daily':'recurring';
    if(r.repeat_type==='daily'){ if(tc.length){bucket='done'; rank=80; text='Done'; due=addDays(today,1);} else {bucket='today'; rank=10;} }
    else if(r.repeat_type==='times_per_day'){ const goal=Math.max(1,Number(r.repeat_value||1)), done=Math.min(tc.length,goal); text=`${done}/${goal}`; rank=10+done; if(done>=goal){bucket='done'; rank=80; text=`Done · ${done}/${goal}`; due=addDays(today,1);} else bucket='today'; }
    else if(r.repeat_type==='times_per_week'){ const goal=Math.max(1,Number(r.repeat_value||1)), done=weekComps(s,r.id,today).length, ws=weekStart(today); text=done>=goal?'Complete this week':`${Math.min(done,goal)}/${goal} this week`; due=done>=goal?addDays(ws,7):today; if(tc.length&&done>=goal){bucket='done'; rank=80;} else if(done>=goal){bucket='upcoming'; rank=40;} else {bucket='due'; rank=2;} }
    else if(r.repeat_type==='weekdays'){ const sch=lastWeekday(r.days_of_week,today), doneSince=lastDate && diff(lastDate,sch)>=0; if(tc.length){bucket='done'; rank=80; text='Done today'; due=nextWeekday(r.days_of_week,today,true);} else if(!doneSince && diff(today,sch)>=0){due=sch; const d=diff(today,due); bucket=d>0?'overdue':'due'; rank=d>0?0:1; text=status(today,due);} else {due=nextWeekday(r.days_of_week,today); const d=diff(today,due); bucket=d===0?'due':(d<=-31?'future':'upcoming'); rank=d===0?1:(bucket==='upcoming'?40:60); text=status(today,due);} }
    else { due=r.repeat_type==='every_n_months'?(lastDate?addMonths(lastDate,Number(r.repeat_value||1)):today):(lastDate?addDays(lastDate,Number(r.repeat_value||1)):today); const d=diff(today,due); if(tc.length){bucket='done'; rank=80; text='Done today';} else if(d>0){bucket='overdue'; rank=0; text=status(today,due);} else if(d===0){bucket='due'; rank=1; text='Today';} else if(d>=-30){bucket='upcoming'; rank=40; text=status(today,due);} else {bucket='future'; rank=60; text=status(today,due);} }
    return {routine:r, side, bucket, rank, due, text, repeat:label(r)};
  }
  function sort(a){return [...a].sort((x,y)=>x.rank-y.rank||String(x.due).localeCompare(String(y.due))||String(x.routine.area).localeCompare(String(y.routine.area))||String(x.routine.name).localeCompare(String(y.routine.name)));}
  function card(x, all=false){ const r=x.routine, cls=all?'all':x.bucket, action=x.bucket==='done'?'Undo':'Done'; return `<div class="v2-card ${cls}" data-id="${esc(r.id)}"><span class="v2-main"><strong>${esc(r.name)}</strong><small>${esc(x.text)} · ${esc(r.area||'General')} · ${esc(x.repeat)}</small></span><button class="v2-btn ${x.bucket==='done'?'':'primary'}" data-action="${x.bucket==='done'?'undo':'done'}">${action}</button></div>`; }
  function sec(title, rows, all=false){return rows.length?`<section class="v2-section card"><h2>${title}<small>${rows.length}</small></h2>${rows.map(x=>card(x,all)).join('')}</section>`:'';}
  function complete(id){ const s=state(); s.completions.push({id:'completion_'+Date.now(), routine_id:id, completed_at:nowIso(), completed_date:todayIso()}); save(s); render(); }
  function undo(id){ const s=state(), t=todayIso(); const i=s.completions.map((c,i)=>({c,i})).filter(x=>x.c.routine_id===id&&x.c.completed_date===t&&!x.c.deleted).pop()?.i; if(i!==undefined)s.completions.splice(i,1); save(s); render(); }
  function openEdit(r){ const f=document.getElementById('formWrap'); if(!f)return; f.classList.add('open'); document.getElementById('editId').value=r.id; document.getElementById('formTitle').textContent='Edit routine'; document.getElementById('nameInput').value=r.name||''; document.getElementById('areaInput').value=r.area||''; document.getElementById('typeInput').value=r.repeat_type||'every_n_days'; document.getElementById('valueInput').value=r.repeat_value||1; document.getElementById('daysInput').value=(r.days_of_week||[]).map(d=>weekdays[d]).join(', '); document.getElementById('notesInput').value=r.notes||''; }
  function render(){ const s=state(), today=todayIso(); const rows=sort((s.routines||[]).filter(r=>r.active!==false&&!r.deleted).map(r=>item(s,r,today))); const daily=rows.filter(x=>x.side==='daily'), recur=rows.filter(x=>x.side==='recurring'); const dOpen=daily.filter(x=>x.bucket!=='done'), dDone=daily.filter(x=>x.bucket==='done'); const due=recur.filter(x=>x.bucket==='overdue'||x.bucket==='due'), up=recur.filter(x=>x.bucket==='upcoming'), future=recur.filter(x=>x.bucket==='future'), done=recur.filter(x=>x.bucket==='done'); const all=sort(rows.map(x=>({...x,rank:99}))); app.innerHTML=`<div class="v2-column v2-daily-col"><div class="v2-column-title"><strong>Daily Stack</strong><span>${dOpen.length} open</span></div>${sec('Today',dOpen)}${sec('Done Today',dDone)}</div><div class="v2-column v2-recurring-col"><div class="v2-column-title"><strong>Recurring Stack</strong><span>${due.length} due</span></div>${sec('Due / Overdue',due)}${sec('Coming Up',up)}${sec('Far Future',future)}${sec('Done Today',done)}${sec('All Routines',all,true)}</div>`; const by=Object.fromEntries(rows.map(x=>[x.routine.id,x])); app.querySelectorAll('.v2-card').forEach(el=>{const x=by[el.dataset.id]; if(!x)return; el.addEventListener('click',e=>{if(e.target.closest('button'))return; openEdit(x.routine);}); el.querySelector('button')?.addEventListener('click',e=>{e.stopPropagation(); e.currentTarget.dataset.action==='undo'?undo(x.routine.id):complete(x.routine.id);});}); }
  setTimeout(render, 0);
  window.addEventListener('storage', render);
})();