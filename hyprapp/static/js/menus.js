/* Dropdown menus: the topbar sort, and any .menu. */
document.querySelectorAll(".menu").forEach(function (menu) {
  var btn = menu.querySelector(".menubtn");
  var pop = menu.querySelector(".menupop");
  if (!btn || !pop) return;
  function set(open) {
    menu.classList.toggle("is-open", open);
    pop.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    set(pop.hidden);
  });
  document.addEventListener("click", function (e) {
    if (!menu.contains(e.target)) set(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") set(false);
  });
});
