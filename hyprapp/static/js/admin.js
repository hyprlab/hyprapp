/* Settings > Admin: registration, instance settings and the users. */
import { api } from "./api.js";
import { formError } from "./dom.js";
import { reloadWith, toast, toastError } from "./toast.js";

var regOpen = document.getElementById("reg-open");
if (regOpen) {
  regOpen.addEventListener("change", function () {
    api("/admin/registration", { open: regOpen.checked }).then(function (data) {
      toast(data.open ? "Registration is open" : "Registration is closed");
    }).catch(toastError);
  });
}

[["inst-worker", "worker_minutes", "Background interval saved"],
 ["inst-perpage", "items_per_page", "Page size saved"]].forEach(function (spec) {
  var input = document.getElementById(spec[0]);
  if (!input) return;
  input.addEventListener("change", function () {
    var body = {};
    body[spec[1]] = parseInt(input.value, 10);
    api("/admin/instance", body).then(function () { toast(spec[2]); }).catch(toastError);
  });
});

var adduserForm = document.getElementById("admin-adduser");
if (adduserForm) {
  adduserForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var errEl = document.getElementById("au-error");
    errEl.hidden = true;
    api("/admin/users", {
      name: document.getElementById("au-name").value.trim(),
      username: document.getElementById("au-email").value.trim(),
      password: document.getElementById("au-password").value,
      is_admin: document.getElementById("au-admin").checked
    }).then(function () {
      reloadWith("User created");
    }).catch(function (err) { formError(errEl, err.message); });
  });
}

function bindUserRow(item) {
  var userId = item.getAttribute("data-user");
  var username = item.getAttribute("data-username");
  var pwBtn = item.querySelector("[data-admin-password]");
  var toggleBtn = item.querySelector("[data-admin-toggle]");
  var deleteBtn = item.querySelector("[data-admin-delete]");
  if (pwBtn) {
    pwBtn.addEventListener("click", function () {
      var pw = prompt('New password for "' + username + '" (at least 8 characters):');
      if (pw === null) return;
      api("/admin/users/" + userId + "/password", { new: pw })
        .then(function () { toast("Password reset for " + username); })
        .catch(toastError);
    });
  }
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      api("/admin/users/" + userId + "/toggle-admin").then(function (data) {
        reloadWith(username + (data.is_admin ? " is now an admin" : " is no longer an admin"));
      }).catch(toastError);
    });
  }
  if (deleteBtn) {
    deleteBtn.addEventListener("click", function () {
      if (!confirm('Delete "' + username + '" and everything they own? This cannot be undone.')) return;
      api("/admin/users/" + userId + "/delete")
        .then(function () { reloadWith("Deleted " + username); })
        .catch(toastError);
    });
  }
}

document.querySelectorAll(".manage-item[data-user]").forEach(bindUserRow);
