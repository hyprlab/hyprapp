/* Every <dialog>: opening by [data-open], closing by [data-close], Escape or
 * a click on the backdrop, and the sheet's exit animation. A dialog that
 * needs setting up first registers it with onOpen(). */
import { prefersReducedMotion } from "./dom.js";
import { setSidebar } from "./sidebar.js";

var openHooks = {};

// fn(dialog, section) runs before the dialog with this id opens.
export function onOpen(id, fn) { openHooks[id] = fn; }

export function openDialog(id, section) {
  var dialog = document.getElementById(id);
  if (!dialog || dialog.open) return;
  if (openHooks[id]) openHooks[id](dialog, section);
  setSidebar(false);
  dialog.showModal();
}

// Delegated, so buttons that arrive later (an empty state re-rendered by
// paging) open their dialog too.
document.addEventListener("click", function (e) {
  var btn = e.target.closest("[data-open]");
  if (btn) openDialog(btn.getAttribute("data-open"), btn.getAttribute("data-settings-section"));
});

// The sheet slides back out through the top before it actually closes, so
// every way of dismissing it routes through here (button, backdrop, Escape).
var SHEET_EXIT_MS = 300;   // keep in step with the sheet-out animation
var sheetExitTimer = null;
export function closeDialog(dialog, then) {
  if (dialog.id !== "sheet" || prefersReducedMotion()) {
    dialog.close();
    if (then) then();
    return;
  }
  if (dialog.classList.contains("is-closing")) return;
  dialog.classList.add("is-closing");
  clearTimeout(sheetExitTimer);
  sheetExitTimer = setTimeout(function () {
    dialog.classList.remove("is-closing");
    dialog.close();
    if (then) then();
  }, SHEET_EXIT_MS);
}

export function markRestoring(d) {
  // Reappear in place: no entrance animation for a dialog that never left.
  d.classList.add("is-restoring");
  setTimeout(function () { d.classList.remove("is-restoring"); }, 60);
}

// A click on a modal's ::backdrop is dispatched to the <dialog> itself, so
// target identity alone can't tell it from a click on the dialog's own
// chrome: the sheet's 840px shell is wider than its 660px article column, so
// its side gutters are the dialog element too. Compare the pointer with the
// dialog's box (which follows the open/close transform) instead, and require
// the press to have started outside as well, so a text selection dragged off
// the article doesn't dismiss it.
function hitOutside(dialog, e) {
  var r = dialog.getBoundingClientRect();
  if (!r.width || !r.height) return false;
  return e.clientX < r.left || e.clientX > r.right ||
         e.clientY < r.top || e.clientY > r.bottom;
}
function onBackdropClick(dialog, close) {
  var pressedOutside = false;
  dialog.addEventListener("pointerdown", function (e) {
    pressedOutside = e.target === dialog && hitOutside(dialog, e);
  });
  dialog.addEventListener("click", function (e) {
    var fromBackdrop = pressedOutside;
    pressedOutside = false;   // don't let a stale press arm a later click
    if (fromBackdrop && e.target === dialog && hitOutside(dialog, e)) close();
  });
}

document.querySelectorAll("dialog").forEach(function (dialog) {
  onBackdropClick(dialog, function () { closeDialog(dialog); });
  dialog.querySelectorAll("[data-close]").forEach(function (btn) {
    btn.addEventListener("click", function () { closeDialog(dialog); });
  });
  if (dialog.id === "sheet") {
    dialog.addEventListener("cancel", function (e) {   // Escape
      e.preventDefault();
      closeDialog(dialog);
    });
  }
});
