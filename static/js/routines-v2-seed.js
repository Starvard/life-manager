(() => {
  const STORE_KEY = 'life-manager:routines-v2';
  const now = new Date().toISOString();
  const rows = [
    ['Floss','Hygiene','times_per_day',2],
    ['Brush','Hygiene','times_per_day',2],
    ['Shower','Hygiene','times_per_week',4],
    ['Moisturize','Hygiene','daily',null],
    ['Trim Nails','Hygiene','times_per_week',1],
    ['Shave','Hygiene','times_per_week',2],
    ['Play Basketball','Self-Care','times_per_week',2],
    ['Run 5k','Self-Care','times_per_week',2],
    ['Meditate','Self-Care','times_per_week',2],
    ['Drink Water','Self-Care','times_per_day',5],
    ['Physical Therapy','Self-Care','times_per_week',3],
    ['Strength Train','Self-Care','times_per_week',3],
    ['Take Vitamins','Self-Care','times_per_day',2],
    ['Vitamin D Rowan','Self-Care','daily',null],
    ['Jenna Night Routine','Family','daily',null],
    ['Rosemary Night Routine','Family','daily',null],
    ['Rowan Night Routine','Family','daily',null],
    ['Jenna 1:1 Date','Family','every_n_days',28],
    ['Rosemary 1:1 Date','Family','every_n_days',28],
    ['Rowan 1:1 Date','Family','every_n_days',28],
    ['Flowers for Jenna','Family','every_n_days',28],
    ['Romance','Family','every_n_days',14],
    ['Family Activity','Family','times_per_week',1],
    ['Freeze milk','Home','every_n_days',2],
    ['Plant Care','Home','times_per_week',3],
    ['Budget','Home','times_per_week',4],
    ['Walk Jasper','Home','times_per_week',3],
    ['Dishes','Home','times_per_day',2],
    ['Tidy Up','Home','daily',null],
    ['Deep Clean Upstairs','Home','every_n_days',14],
    ['Deep Clean Downstairs','Home','every_n_days',14],
    ['HVAC Maintenance','Home','every_n_months',6],
    ['Knife Sharpening','Home','every_n_months',3],
    ['Meal Plan','Home','times_per_week',1],
    ['Laundry','Home','times_per_week',2],
    ['Mow Lawn','Home','times_per_week',1],
    ['Take out Trash','Home','weekdays',null,[1]],
    ['Lesson Plan','Homeschool','times_per_week',1],
    ['Teach','Homeschool','times_per_week',4],
    ['Emails','Work','times_per_week',5],
    ['Plan','Work','times_per_week',5],
    ['Focus Work','Work','times_per_week',5]
  ];
  const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  function seededState() {
    return {
      version: 1,
      seeded_from: 'v2 default routines',
      seeded_at: now,
      routines: rows.map(([name, area, repeat_type, repeat_value, days_of_week]) => ({
        id: 'seed_' + slug(area + '_' + name),
        name,
        area,
        repeat_type,
        repeat_value: repeat_value == null ? null : repeat_value,
        days_of_week: days_of_week || [],
        notes: '',
        active: true,
        created_at: now,
        updated_at: now
      })),
      completions: []
    };
  }
  try {
    const raw = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
    const empty = !raw || !Array.isArray(raw.routines) || raw.routines.length === 0;
    if (empty) localStorage.setItem(STORE_KEY, JSON.stringify(seededState()));
  } catch (_) {
    localStorage.setItem(STORE_KEY, JSON.stringify(seededState()));
  }
})();