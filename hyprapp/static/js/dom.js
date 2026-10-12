/* Small page helpers more than one module needs. */

export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function openDialogElement() {
  return document.querySelector("dialog[open]");
}

// A key press that is the app's to handle: not typed into a field, and not
// part of a browser or system shortcut.
export function plainKey(e) {
  var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable;
  return !(typing || e.ctrlKey || e.metaKey || e.altKey);
}

// An inline form error: shown with a message, hidden without one.
export function formError(el, message) {
  el.textContent = message || "";
  el.hidden = !message;
}
