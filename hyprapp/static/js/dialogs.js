/* Every <dialog>: opening by [data-open], closing by [data-close], Escape or
 * a click on the backdrop, and the exit animations. A dialog that
 * needs setting up first registers it with onOpen(). */
import { prefersReducedMotion } from "./dom.js";
import { setSidebar } from "./sidebar.js";

var openHooks = {};

// fn(dialog, section) runs before the dialog with this id opens.
export function onOpen(id, fn) { openHooks[id] = fn; }

export function openDialog(id, section) {
  var dialog = document.getElementById(id);
  if (!dialog) return;
  var leaving = dialog.classList.contains("is-closing");
  if (dialog.open && !leaving) return;
  if (openHooks[id]) openHooks[id](dialog, section);
  setSidebar(false);
  if (leaving) cancelExit(dialog);   // asked for again while sliding out: stay
  else dialog.showModal();
}

// Delegated, so buttons that arrive later (an empty state re-rendered by
// paging) open their dialog too.
document.addEventListener("click", function (e) {
  var btn = e.target.closest("[data-open]");
  if (btn) openDialog(btn.getAttribute("data-open"), btn.getAttribute("data-settings-section"));
});

// A dialog marked data-exit (the sheet, the slideout) animates out before it
// actually closes, so every way of dismissing it routes through here (button,
// backdrop, Escape).
var EXIT_MS = 300;   // keep in step with the sheet-out and slideout-out animations
function cancelExit(dialog) {
  clearTimeout(dialog.exitTimer);
  dialog.classList.remove("is-closing");
}
export function closeDialog(dialog, then) {
  if (!dialog.hasAttribute("data-exit") || prefersReducedMotion()) {
    dialog.close();
    if (then) then();
    return;
  }
  if (dialog.classList.contains("is-closing")) return;
  dialog.classList.add("is-closing");
  // Keys pressed while it slides out are the page's, not its fields'.
  if (dialog.contains(document.activeElement)) document.activeElement.blur();
  dialog.exitTimer = setTimeout(function () {
    dialog.classList.remove("is-closing");
    dialog.close();
    if (then) then();
  }, EXIT_MS);
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
  if (dialog.hasAttribute("data-exit")) {
    dialog.addEventListener("cancel", function (e) {   // Escape
      e.preventDefault();
      closeDialog(dialog);
    });
  }
});
