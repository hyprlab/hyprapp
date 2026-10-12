/* The sidebar as a drawer, under 900px. */
var sidebar = document.getElementById("sidebar");
var scrim = document.querySelector(".scrim");

export function setSidebar(open) {
  if (!sidebar) return;
  sidebar.classList.toggle("is-open", open);
  if (scrim) scrim.hidden = !open;
}

document.querySelectorAll("[data-open-sidebar]").forEach(function (el) {
  el.addEventListener("click", function () { setSidebar(true); });
});
document.querySelectorAll("[data-close-sidebar]").forEach(function (el) {
  el.addEventListener("click", function () { setSidebar(false); });
});
