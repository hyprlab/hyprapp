/* Pull to refresh, on touch devices. */
import { openDialogElement } from "./dom.js";

var ptr = document.getElementById("ptr");
var THRESHOLD = 80, startY = null, pull = 0;

function canStart() {
  var sidebar = document.getElementById("sidebar");
  return window.scrollY <= 0 && !openDialogElement() && !(sidebar && sidebar.classList.contains("is-open"));
}

function onStart(e) {
  if (!canStart()) { startY = null; return; }
  startY = e.touches[0].clientY;
  pull = 0;
}

function onMove(e) {
  if (startY === null) return;
  pull = Math.max(0, e.touches[0].clientY - startY);
  // Resistance: the spinner follows the finger at a third of its travel.
  var y = Math.min(pull / 2.5, THRESHOLD + 20);
  ptr.classList.add("is-dragging");
  ptr.classList.toggle("is-armed", pull > THRESHOLD * 1.6);
  ptr.style.transform = "translateY(" + y + "px) rotate(" + (pull * 1.5) + "deg)";
}

function onEnd() {
  if (startY === null) return;
  startY = null;
  ptr.classList.remove("is-dragging");
  if (ptr.classList.contains("is-armed")) {
    ptr.classList.add("is-refreshing");
    ptr.style.transform = "translateY(" + (THRESHOLD + 10) + "px)";
    location.reload();
  } else {
    ptr.style.transform = "";
  }
}

if (ptr && "ontouchstart" in window) {
  document.addEventListener("touchstart", onStart, { passive: true });
  document.addEventListener("touchmove", onMove, { passive: true });
  document.addEventListener("touchend", onEnd);
}
