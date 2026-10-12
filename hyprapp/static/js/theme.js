/* Light, dark or the system's choice. The inline script in base.html sets the
 * theme before first paint; this keeps it in step afterwards, on every page. */
import { api } from "./api.js";

var root = document.documentElement;
var media = window.matchMedia("(prefers-color-scheme: dark)");

function applyTheme(pref) {
  root.setAttribute("data-theme-pref", pref);
  root.setAttribute("data-theme", pref === "system" ? (media.matches ? "dark" : "light") : pref);
}

media.addEventListener("change", function () {
  if (root.getAttribute("data-theme-pref") === "system") applyTheme("system");
});

// The same switch in the topbar and the sidebar foot.
document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    var radio = document.querySelector('input[name="theme"][value="' + next + '"]');
    if (radio) radio.checked = true;
    api("/settings", { theme: next }).catch(function () {});
  });
});

document.querySelectorAll('input[name="theme"]').forEach(function (radio) {
  radio.addEventListener("change", function () {
    applyTheme(radio.value);
    api("/settings", { theme: radio.value }).catch(function () {});
  });
});
