/* The search palette: Ctrl/Cmd+K, or / when nothing else has the keyboard. */
import { get } from "./api.js";
import { openDialogElement, plainKey } from "./dom.js";
import { openRecord } from "./records.js";
import { remember } from "./restore.js";

var palette = document.getElementById("search-modal");
var searchInput = document.getElementById("search-input");
var searchResults = document.getElementById("search-results");
var searchTimer = null;
var searchSeq = 0;
var activeIndex = -1;

var kbd = document.getElementById("search-kbd");
if (kbd && /Mac|iPhone|iPad/.test(navigator.platform)) kbd.textContent = "⌘K";

function openPalette() {
  if (!palette || palette.open) return;
  searchInput.value = "";
  searchResults.hidden = true;
  searchResults.textContent = "";
  activeIndex = -1;
  palette.showModal();
  searchInput.focus();
}

function highlight(text, query) {
  var at = text.toLowerCase().indexOf(query.toLowerCase());
  var frag = document.createDocumentFragment();
  if (at === -1) { frag.appendChild(document.createTextNode(text)); return frag; }
  frag.appendChild(document.createTextNode(text.slice(0, at)));
  var mark = document.createElement("mark");
  mark.textContent = text.slice(at, at + query.length);
  frag.appendChild(mark);
  frag.appendChild(document.createTextNode(text.slice(at + query.length)));
  return frag;
}

function paragraph(className, text) {
  var p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  return p;
}

function resultRow(r, i, query) {
  var row = document.createElement("div");
  row.className = "palette-item" + (r.done ? " is-done" : "") + (i === 0 ? " is-active" : "");
  row.setAttribute("data-id", r.id);
  var title = document.createElement("span");
  title.className = "palette-item-title";
  title.appendChild(highlight(r.title, query));
  var meta = document.createElement("span");
  meta.className = "palette-item-meta";
  meta.textContent = r.when;
  row.appendChild(title);
  row.appendChild(meta);
  row.addEventListener("click", function () { choose(i); });
  row.addEventListener("mousemove", function () { setActive(i, true); });
  return row;
}

function renderResults(results, query) {
  searchResults.textContent = "";
  activeIndex = results.length ? 0 : -1;
  if (!results.length) {
    searchResults.appendChild(paragraph("palette-empty", "Nothing matches “" + query + "”."));
  } else {
    searchResults.appendChild(paragraph("palette-label", "Records"));
    results.forEach(function (r, i) { searchResults.appendChild(resultRow(r, i, query)); });
  }
  searchResults.hidden = false;
}

function rows() { return searchResults.querySelectorAll(".palette-item"); }

function setActive(i, noScroll) {
  var all = rows();
  if (!all.length) return;
  activeIndex = Math.max(0, Math.min(all.length - 1, i));
  all.forEach(function (el, n) { el.classList.toggle("is-active", n === activeIndex); });
  if (!noScroll) all[activeIndex].scrollIntoView({ block: "nearest" });
}

function choose(i) {
  var all = rows();
  var pick = all[i === undefined ? activeIndex : i];
  if (!pick) return;
  palette.close();
  openRecord(parseInt(pick.getAttribute("data-id"), 10));
}

var searchBtn = document.getElementById("search-btn");
if (searchBtn) searchBtn.addEventListener("click", openPalette);

if (searchInput) {
  searchInput.addEventListener("input", function () {
    var query = searchInput.value.trim();
    clearTimeout(searchTimer);
    if (query.length < 2) { searchResults.hidden = true; return; }
    // Debounced, and sequenced so a slow answer to an old query never
    // replaces the answer to the current one.
    searchTimer = setTimeout(function () {
      var seq = ++searchSeq;
      get("/search?q=" + encodeURIComponent(query)).then(function (data) {
        if (seq === searchSeq) renderResults(data.results || [], query);
      }).catch(function () {});
    }, 150);
  });
  searchInput.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(activeIndex + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(activeIndex - 1); }
    else if (e.key === "Enter") { e.preventDefault(); choose(); }
  });
}

if (palette) {
  remember("search-modal", {
    save: function () { return { q: searchInput.value }; },
    restore: function (d, s) {
      openPalette();
      searchInput.value = s.q || "";
      searchInput.dispatchEvent(new Event("input"));
    }
  });
}

// On every page, as before the split: these keys are the app's even where
// there is no palette to open.
document.addEventListener("keydown", function (e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openPalette();
    return;
  }
  if (plainKey(e) && !openDialogElement() && e.key === "/") { e.preventDefault(); openPalette(); }
});
