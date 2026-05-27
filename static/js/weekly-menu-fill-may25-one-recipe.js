(function () {
  // Reliable May 25 menu reference. This does not depend on recipe/menu database writes.
  const MENU = [
    ['Monday', 'Scrambled eggs + fruit/yogurt', 'Easy leftovers', 'Cheese + crackers + fruit', 'Meatballs + leftover veggies + pasta salad'],
    ['Tuesday', 'Scrambled eggs with cheese + side salad', 'Leftover meatballs plate', 'Apple + peanut butter', 'Ground turkey black bean taco melts'],
    ['Wednesday', 'Turkey egg scramble + side salad', 'Leftover turkey taco lunch', 'Blueberry yogurt', 'Lemon garlic chicken + carrots + potatoes'],
    ['Thursday', 'Chicken egg bites + side salad', 'Leftover lemon garlic chicken', 'Egg + fruit', 'Peanut chicken cauliflower rice bowl'],
    ['Friday', 'Eggs with leftover chicken + greens', 'Leftover peanut chicken', 'Cheese + crackers + pickles', 'Steak + broccoli'],
    ['Saturday', 'Chicken egg bites or quick eggs', 'Leftover steak + broccoli', 'Hummus carrots or edamame', 'Chickpea tomato Banza pasta bake'],
    ['Sunday', 'Eggs + toast/roll + fruit', 'Leftover pasta bake', 'Peanut butter crackers + fruit', 'Snacky leftover dinner']
  ];

  const RECIPES = [
    ['Meatballs', '400°F for 15–18 min. Mix beef, ricotta, egg, crushed crackers, Italian seasoning, garlic powder, salt, pepper. Roll small, bake, serve with leftover veggies and pasta salad.'],
    ['Turkey taco melts', 'Brown turkey. Add taco seasoning, splash water, black beans, and salsa. Simmer 3–5 min. Add to tortillas/bread/rolls with cheese and toast.'],
    ['Lemon garlic chicken', '425°F. Roast potatoes/carrots 15 min with oil, salt, pepper, garlic. Add lemon-garlic chicken and roast until done. Save extra chicken.'],
    ['Peanut chicken cauliflower rice', 'Whisk peanut butter, soy/fish sauce, lemon/lime, hot water. Cook cauliflower rice, add carrots and chicken, toss with sauce.'],
    ['Steak and broccoli', 'Thaw steak Thursday. Pat dry, salt/pepper, sear hot, rest 5–10 min. Cook broccoli and finish with garlic, lemon, butter/oil.'],
    ['Chickpea Banza pasta bake', '375°F. Cook Banza 1–2 min short. Mix with tomato sauce, chickpeas, ricotta, optional leftovers. Top cheese, bake 20–25 min.'],
    ['Snacky leftover dinner', 'Pull out leftovers, fruit, cheese/crackers, pickles, yogurt/cottage cheese. Warm what needs warming and build plates.']
  ];

  function onRecipesPage() { return location.pathname.startsWith('/recipes'); }

  function injectMenuReference() {
    if (!onRecipesPage() || document.getElementById('may25-menu-reference')) return;
    const menuSection = document.querySelector('section[x-show="tab === \'menu\'"]');
    if (!menuSection) return;

    const box = document.createElement('div');
    box.id = 'may25-menu-reference';
    box.className = 'card';
    box.style.marginBottom = '1rem';
    box.innerHTML = `
      <div class="card-title">This Week's Menu — May 25</div>
      <p class="rcp-hint">Quick reference for this week. This is hardcoded so it shows even if the recipe/menu database is being annoying.</p>
      <div style="overflow-x:auto; margin-top:.75rem;">
        <table class="rcp-inv-table">
          <thead><tr><th>Day</th><th>Breakfast</th><th>Lunch</th><th>Nap Snack</th><th>Dinner</th></tr></thead>
          <tbody>
            ${MENU.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}
          </tbody>
        </table>
      </div>
      <details style="margin-top:1rem;">
        <summary style="cursor:pointer; font-weight:700;">Recipe quick steps</summary>
        <div style="display:grid; gap:.6rem; margin-top:.75rem;">
          ${RECIPES.map(r => `<div><strong>${r[0]}</strong><br><span>${r[1]}</span></div>`).join('')}
        </div>
      </details>
    `;
    menuSection.insertBefore(box, menuSection.firstElementChild);
  }

  function run() {
    injectMenuReference();
    setTimeout(injectMenuReference, 500);
    setTimeout(injectMenuReference, 1500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
