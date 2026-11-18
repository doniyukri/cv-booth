(function () {
  var KEY = "cvbooth.theme";
  function readStored() {
    try {
      var value = localStorage.getItem(KEY);
      return value === "dark" || value === "light" ? value : "light";
    } catch (err) {
      return "light";
    }
  }
  function apply(theme) {
    var dark = theme === "dark";
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
    var button = document.getElementById("theme-toggle");
    if (!button) return;
    button.setAttribute("aria-pressed", dark ? "true" : "false");
    button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    button.title = dark ? "Switch to light mode" : "Switch to dark mode";
  }
  apply(readStored());
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || !target.closest || !target.closest("#theme-toggle")) return;
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(KEY, next);
    } catch (err) {}
    apply(next);
  });
  document.addEventListener("DOMContentLoaded", function () {
    apply(readStored());
  });
  window.addEventListener("storage", function (event) {
    if (event.key === KEY) apply(readStored());
  });
})();
