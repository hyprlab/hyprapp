/* Settings > Security: Cloudflare Turnstile.
 *
 * Turning it on (or changing its keys) goes through a real challenge
 * rendered with the new site key; the server saves the keys only if
 * Cloudflare accepts the answer with the new secret. A wrong pair saved
 * blindly would lock everyone out of sign-in. */
import { api, setBusy } from "./api.js";
import { formError } from "./dom.js";
import { toast, toastError } from "./toast.js";

var tsForm = document.getElementById("ts-form");
var tsScript = null;
var tsWidget = null;

function loadTurnstile() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!tsScript) {
    tsScript = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      s.async = true;
      s.onload = function () { resolve(window.turnstile); };
      s.onerror = function () {
        tsScript = null;
        reject(new Error("Couldn't load Cloudflare's challenge. Check the server's connection."));
      };
      document.head.appendChild(s);
    });
  }
  return tsScript;
}

// The widget's own failure codes, for the ones an admin can act on.
function turnstileWidgetError(code) {
  code = String(code || "");
  if (code.indexOf("1101") === 0) return "Cloudflare doesn't recognize that site key.";
  if (code === "110200") return "This address isn't in the widget's hostname list. Add " + location.hostname + " to it in the Cloudflare dashboard.";
  if (code.indexOf("300") === 0 || code.indexOf("600") === 0) return "The challenge failed in this browser (error " + code + "). Try again.";
  return "The challenge failed to load (error " + code + ").";
}

function setTurnstileStatus(status) {
  var chip = document.getElementById("ts-chip");
  chip.textContent = status.on ? "On" : "Off";
  chip.classList.toggle("chip--muted", !status.on);
  document.getElementById("ts-status-text").textContent = status.on
    ? (status.source === "environment"
        ? "From the TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY environment variables. Keys saved here take over from them."
        : "Sign-in and sign-up show a challenge.")
    : "Sign-in and sign-up have no challenge.";
  document.getElementById("ts-off").hidden = !status.on;
  tsForm.querySelector("#ts-verify .btn-label").textContent =
    status.on ? "Verify and save the keys" : "Verify and turn on";
  var secret = document.getElementById("ts-secret");
  secret.value = "";
  secret.placeholder = status.secret_hint
    ? "Saved, ends in " + status.secret_hint + ". Leave empty to keep it."
    : "From the same widget";
  tsForm.setAttribute("data-has-secret", status.secret_hint ? "1" : "0");
}

function clearTurnstileWidget() {
  if (tsWidget !== null && window.turnstile) window.turnstile.remove(tsWidget);
  tsWidget = null;
  document.getElementById("ts-challenge").hidden = true;
}

function showTsError(message) { formError(document.getElementById("ts-error"), message); }

function verifyButton() { return document.getElementById("ts-verify"); }

// Remove, not reset: a reset widget passes again by itself and would
// resubmit the same wrong keys in a loop.
function failed(message) {
  showTsError(message);
  clearTurnstileWidget();
  setBusy(verifyButton(), false);
}

function saveKeys(siteKey, secretKey, token) {
  api("/admin/turnstile", { site_key: siteKey, secret_key: secretKey, token: token })
    .then(function (data) {
      clearTurnstileWidget();
      setTurnstileStatus(data.status);
      setBusy(verifyButton(), false);
      toast("Turnstile is on");
    })
    .catch(function (err) { failed(err.message); });
}

function renderChallenge(turnstile, siteKey, secretKey) {
  clearTurnstileWidget();
  document.getElementById("ts-challenge").hidden = false;
  tsWidget = turnstile.render("#ts-widget", {
    sitekey: siteKey,
    theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light",
    callback: function (token) { saveKeys(siteKey, secretKey, token); },
    "error-callback": function (code) {
      failed(turnstileWidgetError(code));
      return true;   // handled: don't let the widget retry on its own
    },
    "expired-callback": function () { failed("The challenge expired. Press the button again."); }
  });
}

function onSubmit(e) {
  e.preventDefault();
  showTsError("");
  var siteKey = document.getElementById("ts-site").value.trim();
  var secretKey = document.getElementById("ts-secret").value.trim();
  if (!siteKey) { showTsError("Enter the site key."); return; }
  if (!secretKey && tsForm.getAttribute("data-has-secret") !== "1") {
    showTsError("Enter the secret key."); return;
  }
  setBusy(verifyButton(), true);
  loadTurnstile().then(function (turnstile) {
    renderChallenge(turnstile, siteKey, secretKey);
  }).catch(function (err) {
    showTsError(err.message);
    setBusy(verifyButton(), false);
  });
}

if (tsForm) {
  tsForm.addEventListener("submit", onSubmit);
  document.getElementById("ts-off").addEventListener("click", function () {
    showTsError("");
    clearTurnstileWidget();
    api("/admin/turnstile/disable").then(function (data) {
      setTurnstileStatus(data.status);
      toast("Turnstile is off");
    }).catch(toastError);
  });
}
