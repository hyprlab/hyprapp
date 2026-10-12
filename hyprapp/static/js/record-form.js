/* The one form for a new record and an edit, and the n key. */
import { api, setBusy } from "./api.js";
import { onOpen, openDialog } from "./dialogs.js";
import { formError, openDialogElement, plainKey } from "./dom.js";
import { remember } from "./restore.js";
import { reloadWith } from "./toast.js";

export var itemModal = document.getElementById("item-modal");
var itemForm = document.getElementById("item-form");

function fill(id, title, body, editing) {
  document.getElementById("item-id").value = id;
  document.getElementById("item-title").value = title;
  document.getElementById("item-body").value = body;
  document.getElementById("item-modal-title").textContent = editing ? "Edit record" : "New record";
}

export function resetItemForm(item) {
  if (!itemForm) return;
  fill(item ? item.id : "", item ? item.title : "", item ? item.body : "", !!item);
  document.getElementById("item-error").hidden = true;
}

if (itemForm) {
  onOpen("item-modal", function () { resetItemForm(); });

  itemForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var errEl = document.getElementById("item-error");
    var btn = itemForm.querySelector("button[type=submit]");
    var id = document.getElementById("item-id").value;
    errEl.hidden = true;
    setBusy(btn, true);
    api(id ? "/items/" + id : "/items", {
      title: document.getElementById("item-title").value.trim(),
      body: document.getElementById("item-body").value
    }).then(function () {
      itemModal.close();   // saved: the reload shows the list, not the form again
      reloadWith(id ? "Record updated" : "Record created");
    }).catch(function (err) {
      formError(errEl, err.message);
      setBusy(btn, false);
    });
  });

  remember("item-modal", {
    save: function () {
      return {
        id: document.getElementById("item-id").value,
        title: document.getElementById("item-title").value,
        body: document.getElementById("item-body").value
      };
    },
    restore: function (d, s) {
      openDialog("item-modal");   // resets the form, then the draft goes back in
      fill(s.id || "", s.title || "", s.body || "", !!s.id);
    }
  });
}

document.addEventListener("keydown", function (e) {
  if (!plainKey(e) || openDialogElement()) return;
  if (e.key === "n" && itemModal) { e.preventDefault(); openDialog("item-modal"); }
});
