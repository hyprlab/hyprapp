/* Talking to the server. Every call goes through here, so the CSRF header and
 * the {"error": "..."} convention live in exactly one place. */
var CSRF = (document.querySelector('meta[name="csrf"]') || {}).content || "";

export function api(url, body) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF": CSRF },
    body: JSON.stringify(body || {})
  });
}

// X-CSRF on a GET too: it is what makes the server answer a signed-out call
// with a JSON 401 rather than the sign-in page.
export function get(url) {
  return request(url, { headers: { "X-CSRF": CSRF, "Accept": "application/json" } });
}

function request(url, opts) {
  return fetch(url, opts).then(function (resp) {
    return resp.json().catch(function () { return {}; }).then(function (data) {
      if (!resp.ok) throw new Error(data.error || "Something went wrong.");
      return data;
    });
  }, function () {
    throw new Error("Can't reach the server.");
  });
}

export function setBusy(btn, busy) {
  if (!btn) return;
  btn.disabled = busy;
  var label = btn.querySelector(".btn-label"), busyEl = btn.querySelector(".btn-busy");
  if (label) label.hidden = busy;
  if (busyEl) busyEl.hidden = !busy;
}
