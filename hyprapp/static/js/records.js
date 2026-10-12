/* The record list: finding a record's card or row, updating it in place, the
 * optimistic pin, and opening a record (the sheet registers how). */
import { api } from "./api.js";
import { toastError } from "./toast.js";

export var recordsRoot = document.getElementById("records-root");

var opener = function () {};

// fn(id) opens a record; the sheet registers it.
export function onOpenRecord(fn) { opener = fn; }
export function openRecord(id) { opener(id); }

function cardFor(id) {
  return recordsRoot && recordsRoot.querySelector('[data-item="' + id + '"]');
}

export function itemIds() {
  if (!recordsRoot) return [];
  return Array.prototype.map.call(recordsRoot.querySelectorAll("[data-item]"), function (el) {
    return parseInt(el.getAttribute("data-item"), 10);
  });
}

export function setCardDone(id, done) {
  var el = cardFor(id);
  if (!el) return;
  el.classList.toggle("is-done", !!done);
  var meta = el.querySelector(".card-meta");
  if (meta) meta.textContent = done ? "Done" : "Open";
}

export function setCardPinned(id, pinned) {
  var el = cardFor(id);
  var btn = el && el.querySelector(".pinbtn");
  if (!btn) return;
  btn.classList.toggle("is-pinned", !!pinned);
  btn.setAttribute("title", pinned ? "Unpin" : "Pin");
  btn.setAttribute("aria-label", pinned ? "Unpin" : "Pin");
}

export function removeCard(id) {
  var el = cardFor(id);
  if (el) el.remove();
}

function togglePin(pin) {
  var pid = parseInt(pin.getAttribute("data-pin"), 10);
  var next = !pin.classList.contains("is-pinned");
  setCardPinned(pid, next);             // optimistic: the UI answers at once
  api("/items/" + pid, { pinned: next }).catch(function (err) {
    setCardPinned(pid, !next);          // and rolls back if the server says no
    toastError(err);
  });
}

if (recordsRoot) {
  // Delegated: records appended by paging need no binding of their own. One
  // listener for both, so a click on the pin never opens the record.
  recordsRoot.addEventListener("click", function (e) {
    var pin = e.target.closest("[data-pin]");
    if (pin) {
      e.stopPropagation();
      togglePin(pin);
      return;
    }
    var card = e.target.closest("[data-item]");
    if (card) openRecord(parseInt(card.getAttribute("data-item"), 10));
  });
  recordsRoot.addEventListener("keydown", function (e) {
    var card = e.target.closest("[data-item]");
    if (card && e.target === card && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      openRecord(parseInt(card.getAttribute("data-item"), 10));
    }
  });
}
