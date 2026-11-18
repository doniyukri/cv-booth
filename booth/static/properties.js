(function () {
  const minWidth = 250;
  const mainMin = 280;
  const storeKey = "cvbooth.propertiesWidth";

  function install() {
    // Compose and Profile each have a rail. One stored width applies to every rail.
    const works = [...document.querySelectorAll(".work")];
    if (!works.length) return;

    function visibleWork() {
      return works.find((work) => work.getClientRects().length > 0) || null;
    }

    function clamp(px, work) {
      const bounds = work.getBoundingClientRect();
      if (bounds.width < minWidth + mainMin) return null;
      const floor = Math.max(minWidth, px);
      const max = Math.max(minWidth, bounds.width - mainMin);
      return Math.round(Math.min(max, floor));
    }

    function apply(px, save) {
      const work = visibleWork();
      if (!work) return null;
      const width = clamp(px, work);
      if (width == null) return null;
      const max = clamp(100000, work) || width;
      works.forEach((item) => {
        item.style.setProperty("--properties-width", width + "px");
        const handle = item.querySelector(".properties-resize");
        if (!handle) return;
        handle.setAttribute("aria-valuenow", String(width));
        handle.setAttribute("aria-valuemax", String(max));
      });
      if (save) localStorage.setItem(storeKey, String(width));
      return width;
    }

    const saved = Number(localStorage.getItem(storeKey));
    if (saved) apply(saved, false);

    works.forEach((work) => {
      const handle = work.querySelector(".properties-resize");
      if (!handle) return;
      let dragging = false;
      handle.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) return;
        dragging = true;
        handle.classList.add("is-dragging");
        document.body.classList.add("resizing-properties");
        try { handle.setPointerCapture(event.pointerId); } catch (err) {}
        event.preventDefault();
      });
      handle.addEventListener("pointermove", (event) => {
        if (!dragging) return;
        const current = visibleWork();
        if (!current) return;
        const bounds = current.getBoundingClientRect();
        apply(bounds.right - event.clientX - handle.offsetWidth / 2, false);
      });
      function endDrag() {
        if (!dragging) return;
        dragging = false;
        handle.classList.remove("is-dragging");
        document.body.classList.remove("resizing-properties");
        const width = handle.getAttribute("aria-valuenow") || String(minWidth);
        localStorage.setItem(storeKey, width);
      }
      handle.addEventListener("pointerup", endDrag);
      handle.addEventListener("pointercancel", endDrag);
      handle.addEventListener("keydown", (event) => {
        const current = Number(handle.getAttribute("aria-valuenow")) || minWidth;
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          apply(current + 16, true);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          apply(current - 16, true);
        }
      });
    });
    window.addEventListener("resize", () => {
      apply(Number(localStorage.getItem(storeKey)) || minWidth, false);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
