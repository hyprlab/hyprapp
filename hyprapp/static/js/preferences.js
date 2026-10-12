/* Settings > Appearance and Account: the default view, the name and the
 * password. The theme is theme.js; infinite scroll is paging.js. */
import { api } from "./api.js";
import { formError } from "./dom.js";
import { toast, toastError } from "./toast.js";

document.querySelectorAll('input[name="view_mode"]').forEach(function (radio) {
  radio.addEventListener("change", function () {
    api("/settings", { view_mode: radio.value })
      .then(function () { toast("Default view saved"); })
      .catch(toastError);
  });
});

// The sidebar's account row follows the name: the email stands in for it.
function showName(value) {
  var nameEl = document.getElementById("user-name");
  var emailEl = document.getElementById("user-email");
  var avatar = document.getElementById("user-avatar");
  var email = (emailEl && emailEl.textContent) || "";
  if (nameEl) nameEl.textContent = value || email;
  if (avatar) avatar.textContent = (value || email).charAt(0).toUpperCase();
  if (emailEl) emailEl.hidden = !value;
}

var acctName = document.getElementById("acct-name");
if (acctName) {
  acctName.addEventListener("change", function () {
    var value = acctName.value.trim();
    api("/settings", { name: value }).then(function () {
      toast("Name saved");
      showName(value);
    }).catch(toastError);
  });
}

var passwordForm = document.getElementById("password-form");
if (passwordForm) {
  passwordForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var errEl = document.getElementById("pw-error");
    errEl.hidden = true;
    api("/account/password", {
      current: document.getElementById("pw-current").value,
      new: document.getElementById("pw-new").value
    }).then(function () {
      passwordForm.reset();
      toast("Password updated");
    }).catch(function (err) { formError(errEl, err.message); });
  });
}
