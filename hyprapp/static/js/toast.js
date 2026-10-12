/* Toasts: a confirmation or an error under the topbar, with an optional
 * action such as Undo. */
import { openDialogElement } from "./dom.js";

var toastTimer, toastLeaveTimer;

function dismissToast(el) {
  if (el.hidden) return;
  el.classList.add("is-leaving");
  clearTimeout(toastLeaveTimer);
  toastLeaveTimer = setTimeout(function () {
    el.hidden = true;
    el.classList.remove("is-leaving");
  }, 260);
}

// toast("Saved") · toast("Deleted", "Undo", fn) · toast(err.message, null, null, true)
export function toast(message, actionLabel, actionFn, isError) {
  var el = document.getElementById("toast");
  if (!el) return;
  // A modal <dialog> paints above everything outside it, so a toast raised
  // while a dialog is open has to live inside it to be seen at all.
  var host = openDialogElement() || document.body;
  if (el.parentNode !== host) host.appendChild(el);
  clearTimeout(toastTimer);
  clearTimeout(toastLeaveTimer);
  el.classList.remove("is-leaving");
  el.classList.toggle("toast--error", !!isError);
  el.textContent = message;
  if (actionLabel) {
    var action = document.createElement("button");
    action.className = "toast-action";
    action.textContent = actionLabel;
    action.addEventListener("click", function () {
      clearTimeout(toastTimer);
      dismissToast(el);
      actionFn();
    });
    el.appendChild(action);
  }
  el.hidden = false;
  toastTimer = setTimeout(function () { dismissToast(el); }, actionLabel ? 3500 : 2600);
}

export function toastError(err) { toast(err.message || String(err), null, null, true); }

// Carries a toast across a reload, for changes the page has to be rebuilt for.
export function reloadWith(message) {
  try { sessionStorage.setItem("app-toast", message); } catch (_) {}
  location.reload();
}

try {
  var pending = sessionStorage.getItem("app-toast");
  if (pending) {
    sessionStorage.removeItem("app-toast");
    setTimeout(function () { toast(pending); }, 250);
  }
} catch (_) {}
