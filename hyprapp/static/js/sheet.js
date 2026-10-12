/* The detail sheet: one record, full height, with its actions and keys.
 * Opened from a card, the palette, or ?open=<id>, which also makes it a link. */
import { api, get } from "./api.js";
import { closeDialog, markRestoring } from "./dialogs.js";
import { openDialogElement, plainKey } from "./dom.js";
import { itemModal, resetItemForm } from "./record-form.js";
import { itemIds, onOpenRecord, removeCard, setCardDone, setCardPinned } from "./records.js";
import { remember } from "./restore.js";
import { reloadWith, toast, toastError } from "./toast.js";

var sheet = document.getElementById("sheet");
var currentItem = null;

function renderSheet(item) {
  currentItem = item;
  document.getElementById("sheet-title").textContent = item.title;
  document.getElementById("sheet-kicker").textContent = item.done ? "Done" : "Open";
  document.getElementById("sheet-meta").textContent = "Created " +
    new Date(item.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  // textContent, never innerHTML: the body is whatever the user typed.
  var body = document.getElementById("sheet-body");
  body.textContent = "";
  (item.body || "").split(/\n{2,}/).forEach(function (para) {
    if (!para.trim()) return;
    var p = document.createElement("p");
    p.textContent = para;
    body.appendChild(p);
  });
  var pin = document.getElementById("sheet-pin");
  pin.classList.toggle("is-pinned", item.pinned);
  pin.setAttribute("title", item.pinned ? "Unpin (p)" : "Pin (p)");
  var done = document.getElementById("sheet-done");
  done.classList.toggle("is-done", item.done);
  done.setAttribute("title", item.done ? "Mark as open (d)" : "Mark as done (d)");
}

function setOpenParam(id) {
  var params = new URLSearchParams(location.search);
  if (id) params.set("open", id); else params.delete("open");
  var qs = params.toString();
  history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
}

function openItem(id, opts) {
  if (!sheet) return;
  opts = opts || {};
  get("/items/" + id).then(function (data) {
    renderSheet(data.item);
    if (!sheet.open) {
      if (opts.restoring) markRestoring(sheet);
      sheet.showModal();
    }
    sheet.scrollTop = opts.scroll || 0;
    setOpenParam(id);
  }).catch(toastError);
}

function openSibling(step) {
  if (!currentItem) return;
  var ids = itemIds();
  var next = ids[ids.indexOf(currentItem.id) + step];
  if (next !== undefined && ids.indexOf(currentItem.id) !== -1) openItem(next);
}

function toggle(field, setCard) {
  if (!currentItem) return;
  var change = {};
  change[field] = !currentItem[field];
  api("/items/" + currentItem.id, change).then(function (data) {
    renderSheet(data.item);
    setCard(data.item.id, data.item[field]);
  }).catch(toastError);
}
function togglePin() { toggle("pinned", setCardPinned); }
function toggleDone() { toggle("done", setCardDone); }

function editCurrent() {
  if (!currentItem) return;
  var item = currentItem;
  closeDialog(sheet, function () {
    resetItemForm(item);
    itemModal.showModal();
  });
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  // Plain HTTP on a LAN has no clipboard API, so fall back to the old way.
  return new Promise(function (resolve) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    (openDialogElement() || document.body).appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (_) {}
    ta.remove();
    resolve();
  });
}

function copyLink() {
  if (!currentItem) return;
  var btn = this;
  copyText(location.origin + "/?open=" + currentItem.id).then(function () {
    btn.classList.add("show-tip");
    setTimeout(function () { btn.classList.remove("show-tip"); }, 1200);
  });
}

function deleteCurrent() {
  if (!currentItem) return;
  var id = currentItem.id;
  api("/items/" + id + "/delete").then(function (data) {
    closeDialog(sheet);
    removeCard(id);
    // Undo instead of a confirm dialog: the delete happens at once, and the
    // snapshot the server returned is enough to put it back.
    toast("Record deleted", "Undo", function () {
      api("/items/restore", data.item)
        .then(function () { reloadWith("Record restored"); })
        .catch(toastError);
    });
  }).catch(toastError);
}

var KEYS = {
  j: function () { openSibling(1); },
  k: function () { openSibling(-1); },
  p: togglePin,
  d: toggleDone,
  e: editCurrent
};

if (sheet) {
  onOpenRecord(openItem);
  sheet.addEventListener("close", function () {
    currentItem = null;
    setOpenParam(null);
  });
  document.getElementById("sheet-prev").addEventListener("click", function () { openSibling(-1); });
  document.getElementById("sheet-next").addEventListener("click", function () { openSibling(1); });
  document.getElementById("sheet-pin").addEventListener("click", togglePin);
  document.getElementById("sheet-done").addEventListener("click", toggleDone);
  document.getElementById("sheet-edit").addEventListener("click", editCurrent);
  document.getElementById("sheet-copy").addEventListener("click", copyLink);
  document.getElementById("sheet-delete").addEventListener("click", deleteCurrent);

  document.addEventListener("keydown", function (e) {
    if (!plainKey(e) || !sheet.open || !KEYS[e.key]) return;
    e.preventDefault();
    KEYS[e.key]();
  });

  // The record lives in the URL; only the scroll offset needs remembering.
  remember("sheet", {
    save: function (d) { return { scroll: d.scrollTop }; },
    fromUrl: function (state) {
      var deepLink = parseInt(new URLSearchParams(location.search).get("open"), 10);
      if (!deepLink) return false;
      openItem(deepLink, { restoring: !!state, scroll: state ? state.scroll : 0 });
      return true;
    }
  });
}
