// SPDX-FileCopyrightText: 2026 James G Willmore
// SPDX-License-Identifier: Apache-2.0

// Shows a wait cursor + spinner overlay while a form submission or htmx request
// (e.g. running a validation, testing a connection) is in flight, so a slow
// database query doesn't look like the page has frozen.
(function () {
  "use strict";

  function showLoading(message) {
    document.body.classList.add("is-loading");
    var messageEl = document.querySelector("#loading-overlay .loading-message");
    if (messageEl) {
      messageEl.textContent = message || "Working…";
    }
  }

  function hideLoading() {
    document.body.classList.remove("is-loading");
  }

  // Plain (non-htmx) form submissions, e.g. "Run", "Save", "Delete" - these
  // navigate to a new page on completion, so there's no matching "hide" call;
  // the overlay simply disappears with the old document.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    if (event.defaultPrevented) {
      return; // e.g. an onsubmit="return confirm(...)" that the user cancelled
    }
    if (form.hasAttribute("hx-post") || form.hasAttribute("hx-get")) {
      return; // handled by the htmx events below instead
    }
    showLoading(form.dataset.loadingMessage);
    form.querySelectorAll("button[type=submit], button:not([type])").forEach(function (button) {
      button.disabled = true;
    });
  });

  // htmx-driven requests, e.g. the "Test connection" button - these swap content
  // in place rather than navigating, so we do need to hide the overlay again.
  document.body.addEventListener("htmx:beforeRequest", function (event) {
    var trigger = event.detail && event.detail.elt;
    showLoading(trigger && trigger.dataset ? trigger.dataset.loadingMessage : undefined);
  });
  document.body.addEventListener("htmx:afterRequest", hideLoading);
})();
