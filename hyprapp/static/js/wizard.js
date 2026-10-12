/* The first-run wizard on /setup: four steps, the admin account created on
 * the third. Loaded only by setup.html. */
(function () {
  "use strict";
  var CSRF = document.querySelector('meta[name="csrf"]').content;
  var steps = Array.prototype.slice.call(document.querySelectorAll(".wiz-step"));
  var dots = Array.prototype.slice.call(document.querySelectorAll(".wiz-dot"));
  var current = 0;
  var accountCreated = false;

  function show(n) {
    current = n;
    steps.forEach(function (s, i) { s.classList.toggle("is-active", i === n); });
    dots.forEach(function (d, i) { d.classList.toggle("is-active", i <= n); });
    var focus = steps[n].querySelector("input");
    if (focus) focus.focus();
  }

  function err(step, message) {
    var el = document.getElementById("wiz-error-" + step);
    el.textContent = message || "";
    el.hidden = !message;
  }

  function api(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF": CSRF },
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().then(function (data) {
        if (!resp.ok) throw new Error(data.error || "Something went wrong.");
        return data;
      });
    });
  }

  function setBusy(btn, busy) {
    btn.disabled = busy;
    var label = btn.querySelector(".btn-label"), busyEl = btn.querySelector(".btn-busy");
    if (label) label.hidden = busy;
    if (busyEl) busyEl.hidden = !busy;
  }

  document.querySelectorAll("[data-back]").forEach(function (btn) {
    btn.addEventListener("click", function () { show(current - 1); });
  });

  document.querySelectorAll("[data-next]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (current === 0) { show(1); return; }
      if (current === 1) {
        var email = document.getElementById("wiz-email").value.trim();
        var pw = document.getElementById("wiz-password").value;
        var confirm = document.getElementById("wiz-confirm").value;
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { err(1, "Enter a valid email address."); return; }
        if (pw.length < 8) { err(1, "Passwords need at least 8 characters."); return; }
        if (pw !== confirm) { err(1, "Passwords don't match."); return; }
        err(1, null);
        show(2);
        return;
      }
      if (current === 2) {
        err(2, null);
        setBusy(btn, true);
        api("/setup", {
          name: document.getElementById("wiz-name").value.trim(),
          username: document.getElementById("wiz-email").value.trim(),
          password: document.getElementById("wiz-password").value,
          registration_open: document.getElementById("wiz-registration").checked,
          worker_minutes: parseInt(document.getElementById("wiz-worker").value, 10)
        }).then(function () {
          accountCreated = true;
          show(3);
        }).catch(function (e) {
          err(2, e.message);
        }).finally(function () { setBusy(btn, false); });
      }
    });
  });

  document.getElementById("wiz-add-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (!accountCreated) return;
    var input = document.getElementById("wiz-title");
    var title = input.value.trim();
    if (!title) return;
    var btn = this.querySelector("button");
    err(3, null);
    setBusy(btn, true);
    api("/items", { title: title })
      .then(function (data) {
        var li = document.createElement("li");
        li.textContent = data.item.title;
        document.getElementById("wiz-added").appendChild(li);
        input.value = "";
      })
      .catch(function (e) { err(3, e.message); })
      .finally(function () { setBusy(btn, false); });
  });

  document.getElementById("wiz-finish").addEventListener("click", function () {
    location.href = "/";
  });
})();
