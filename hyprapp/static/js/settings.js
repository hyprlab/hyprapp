/* The settings window: a rail of sections and one pane at a time. On a phone
 * only one of the two shows, and .is-showing-pane says which. */
import { onOpen, openDialog } from "./dialogs.js";
import { remember } from "./restore.js";

var settingsModal = document.getElementById("settings-modal");
var narrow = window.matchMedia("(max-width: 700px)");

function settingsItems() {
  return settingsModal ? Array.prototype.slice.call(settingsModal.querySelectorAll(".settings-navitem")) : [];
}

function showSettingsSection(name, focusItem) {
  var chosen = null;
  settingsItems().forEach(function (item) {
    var on = item.getAttribute("data-section") === name;
    item.classList.toggle("is-active", on);
    item.setAttribute("aria-selected", on ? "true" : "false");
    item.tabIndex = on ? 0 : -1;
    if (on) chosen = item;
  });
  if (!chosen) return;
  settingsModal.querySelectorAll(".settings-pane").forEach(function (pane) {
    var on = pane.getAttribute("data-pane") === name;
    if (on && !pane.classList.contains("is-active")) pane.scrollTop = 0;
    pane.classList.toggle("is-active", on);
  });
  document.getElementById("settings-section-title").textContent =
    chosen.querySelector("span").textContent;
  settingsModal.classList.add("is-showing-pane");
  if (focusItem) chosen.focus();
}

function showSettingsList() {
  settingsModal.classList.remove("is-showing-pane");
  var active = settingsModal.querySelector(".settings-navitem.is-active");
  if (active) active.focus();
}

// Arrow keys move through the rail and select as they go (the WAI-ARIA
// vertical tab pattern); Home and End jump to the ends.
function onRailKey(e) {
  var items = settingsItems();
  var at = items.indexOf(document.activeElement);
  if (at === -1) return;
  var next = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: items.length - 1 }[e.key];
  if (next === undefined) return;
  e.preventDefault();
  next = (next + items.length) % items.length;
  showSettingsSection(items[next].getAttribute("data-section"), true);
  if (narrow.matches) settingsModal.classList.remove("is-showing-pane");
}

if (settingsModal) {
  // A named section opens straight to it. Otherwise the window reopens where
  // it was left, except on a phone, where it starts at the list.
  onOpen("settings-modal", function (dialog, section) {
    if (section) showSettingsSection(section);
    else if (narrow.matches) dialog.classList.remove("is-showing-pane");
  });

  settingsItems().forEach(function (item) {
    item.addEventListener("click", function () {
      showSettingsSection(item.getAttribute("data-section"));
    });
  });
  settingsModal.querySelector(".settings-nav").addEventListener("keydown", onRailKey);
  settingsModal.querySelector(".settings-back").addEventListener("click", showSettingsList);
  // On a phone, Escape inside a section goes back to the list first.
  settingsModal.addEventListener("cancel", function (e) {
    if (narrow.matches && settingsModal.classList.contains("is-showing-pane")) {
      e.preventDefault();
      showSettingsList();
    }
  });

  remember("settings-modal", {
    save: function (d) {
      var active = d.querySelector(".settings-navitem.is-active");
      var pane = d.querySelector(".settings-pane.is-active");
      return {
        section: active && active.getAttribute("data-section"),
        pane: d.classList.contains("is-showing-pane"),
        scroll: pane ? pane.scrollTop : 0
      };
    },
    restore: function (d, s) {
      openDialog("settings-modal", s.section);
      if (narrow.matches && !s.pane) d.classList.remove("is-showing-pane");
      var pane = d.querySelector(".settings-pane.is-active");
      if (pane) requestAnimationFrame(function () { pane.scrollTop = s.scroll || 0; });
    }
  });
}
