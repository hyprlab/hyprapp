/* Dialogs survive a reload.
 *
 * Refreshing the page brings back the dialog that was open, as it was: the
 * settings section and its scroll, a half-typed record, the search query.
 * It is the default for every <dialog>, including ones added later: one with
 * nothing to remember simply reopens. Add data-restore="off" to a dialog that
 * must not come back. Only a reload restores; arriving at the page any other
 * way starts clean. sessionStorage keeps it to this tab.
 *
 * A dialog with state registers remember(id, {save, restore}); one whose
 * state lives in the URL registers fromUrl instead, which opens it from the
 * address (the sheet's ?open=<id>) and is never restored the other way.
 */
import { markRestoring } from "./dialogs.js";

var RESTORE_KEY = "app-dialog";
var memory = {};
var topDialog = null;

export function remember(id, pair) { memory[id] = pair; }

function rememberDialog() {
  try {
    if (!topDialog || !topDialog.open || topDialog.getAttribute("data-restore") === "off") {
      sessionStorage.removeItem(RESTORE_KEY);
      return;
    }
    var pair = memory[topDialog.id];
    sessionStorage.setItem(RESTORE_KEY, JSON.stringify({
      id: topDialog.id,
      path: location.pathname,
      state: pair && pair.save ? pair.save(topDialog) : null
    }));
  } catch (_) {}
}

function takeRemembered() {
  var navEntry = (performance.getEntriesByType && performance.getEntriesByType("navigation")[0]) || {};
  var remembered = null;
  try { remembered = JSON.parse(sessionStorage.getItem(RESTORE_KEY) || "null"); } catch (_) {}
  try { sessionStorage.removeItem(RESTORE_KEY); } catch (_) {}
  if (navEntry.type !== "reload" || !remembered || remembered.path !== location.pathname) return null;
  return remembered;
}

function watchDialogs() {
  var watcher = new MutationObserver(function (records) {
    records.forEach(function (r) {
      if (r.target.open) topDialog = r.target;
      else if (topDialog === r.target) topDialog = document.querySelector("dialog[open]");
    });
    rememberDialog();
  });
  document.querySelectorAll("dialog[id]").forEach(function (d) {
    watcher.observe(d, { attributes: true, attributeFilter: ["open"] });
  });
  // The latest draft, section and scroll are read as the page goes away.
  window.addEventListener("pagehide", rememberDialog);
}

// A dialog whose state lives in the URL opens from it; true if one did.
function openFromUrl(remembered) {
  for (var id in memory) {
    var stateForIt = remembered && remembered.id === id ? remembered.state || {} : null;
    if (memory[id].fromUrl && memory[id].fromUrl(stateForIt)) return true;
  }
  return false;
}

function reopen(remembered) {
  var dialog = document.getElementById(remembered.id);
  var pair = memory[remembered.id] || {};
  if (!dialog || dialog.tagName !== "DIALOG" || dialog.getAttribute("data-restore") === "off") return;
  if (pair.fromUrl) return;
  markRestoring(dialog);
  if (pair.restore) pair.restore(dialog, remembered.state || {});
  else dialog.showModal();
}

// Called once, after every module has registered.
export function restoreDialogs() {
  var remembered = takeRemembered();
  watchDialogs();
  if (!openFromUrl(remembered) && remembered) reopen(remembered);
}
