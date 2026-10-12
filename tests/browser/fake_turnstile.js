/* Stands in for https://challenges.cloudflare.com/turnstile/v0/api.js in the
 * browser tests. A test steers it with window.__turnstileMode before the
 * widget renders: "pass" (the default), "error:<code>", or "expire".
 * Calls are recorded in window.__turnstileCalls.
 */
(function () {
  var explicit = /render=explicit/.test((document.currentScript || {}).src || "");
  var calls = window.__turnstileCalls = [];
  var count = 0;
  function mode() { return window.__turnstileMode || "pass"; }

  function render(target, opts) {
    var host = typeof target === "string" ? document.querySelector(target) : target;
    var id = "widget-" + (++count);
    calls.push(["render", opts.sitekey, opts.theme]);
    var box = document.createElement("div");
    box.className = "fake-turnstile";
    box.textContent = "Challenge for " + opts.sitekey;
    host.appendChild(box);
    setTimeout(function () {
      var m = mode();
      if (m === "pass") opts.callback("GOOD_TOKEN");
      else if (m.indexOf("error:") === 0) opts["error-callback"](m.slice(6));
      else if (m === "expire") opts["expired-callback"]();
    }, 30);
    return id;
  }

  window.turnstile = {
    render: render,
    remove: function (id) { calls.push(["remove", id]); },
    reset: function (id) { calls.push(["reset", id]); }
  };

  // Implicit rendering, as on the sign-in and sign-up pages: the widget adds
  // its answer to the form as a hidden field.
  function autoRender() {
    document.querySelectorAll(".cf-turnstile[data-sitekey]").forEach(function (el) {
      calls.push(["auto", el.getAttribute("data-sitekey")]);
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = "cf-turnstile-response";
      input.value = mode() === "pass" ? "GOOD_TOKEN" : "refused-token";
      el.appendChild(input);
    });
  }
  if (!explicit) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoRender);
    else autoRender();
  }
})();
