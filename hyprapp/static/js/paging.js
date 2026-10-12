/* Paging: Load more, or infinite scroll, both through the same ?partial=1
 * list the server renders for a page load. */
import { api, setBusy } from "./api.js";
import { recordsRoot } from "./records.js";
import { toast, toastError } from "./toast.js";

var loading = false;
var pagerObserver = null;

function infiniteOn() {
  return recordsRoot && recordsRoot.getAttribute("data-infinite") === "1";
}

function pageUrl(btn) {
  var params = new URLSearchParams(location.search);
  params.delete("open");
  params.set("page", btn.getAttribute("data-page"));
  params.set("partial", "1");
  params.set("view", recordsRoot.getAttribute("data-view"));
  return location.pathname + "?" + params.toString();
}

function appendPage(html, btn) {
  var holder = document.createElement("div");
  holder.innerHTML = html;
  var incoming = holder.querySelector(".grid--cards, .grid--list");
  var target = recordsRoot.querySelector(".grid--cards, .grid--list");
  if (incoming && target) {
    while (incoming.firstChild) target.appendChild(incoming.firstChild);
  }
  var oldPager = btn.closest(".pager");
  var newPager = holder.querySelector(".pager, .pager-end");
  if (newPager) oldPager.replaceWith(newPager); else oldPager.remove();
}

function loadMore(btn) {
  if (loading || !btn || !recordsRoot) return;
  loading = true;
  setBusy(btn, true);
  fetch(pageUrl(btn), { headers: { "Accept": "text/html" } })
    .then(function (resp) {
      if (!resp.ok) throw new Error();
      return resp.text();
    })
    .then(function (html) {
      appendPage(html, btn);
      loading = false;
      watchPager();
    })
    .catch(function () {
      loading = false;
      setBusy(btn, false);
      toast("Couldn't load more records.", null, null, true);
    });
}

// Watch the pager row, not the last record: it is replaced wholesale by
// every load, so re-observing after each one is enough.
function watchPager() {
  if (pagerObserver) pagerObserver.disconnect();
  var btn = document.getElementById("load-more");
  if (!btn || !infiniteOn() || !("IntersectionObserver" in window)) return;
  pagerObserver = new IntersectionObserver(function (entries) {
    if (entries[0].isIntersecting) loadMore(document.getElementById("load-more"));
  }, { rootMargin: "600px 0px" });
  pagerObserver.observe(btn.closest(".pager"));
}

document.addEventListener("click", function (e) {
  var btn = e.target.closest("#load-more");
  if (btn) loadMore(btn);
});
watchPager();

// The preference, in Settings > Appearance.
var infinite = document.getElementById("infinite-scroll");
if (infinite) {
  infinite.addEventListener("change", function () {
    // Takes effect on the page behind the modal, no reload needed.
    if (recordsRoot) recordsRoot.setAttribute("data-infinite", infinite.checked ? "1" : "0");
    watchPager();
    api("/settings", { infinite_scroll: infinite.checked })
      .then(function () {
        toast(infinite.checked ? "Records load as you scroll" : "Load more records by hand");
      })
      .catch(toastError);
  });
}
