(function () {
  const switcher = document.getElementById("profile-switch");
  const menu = document.getElementById("profile-menu");
  const label = document.getElementById("profile-label");
  const mark = document.getElementById("profile-mark");
  if (!switcher || !menu || !label || !mark) return;

  let snapshot = { active: "default", profiles: [] };
  let selectSeq = 0;

  function key(base, id) {
    return !id || id === "default" ? base : base + "." + id;
  }

  function close() {
    menu.hidden = true;
    switcher.setAttribute("aria-expanded", "false");
  }

  function open() {
    menu.hidden = false;
    switcher.setAttribute("aria-expanded", "true");
  }

  function publish(data) {
    snapshot = data;
    paint();
    document.dispatchEvent(
      new CustomEvent("cvbooth:profile", {
        detail: { active: data.active, profiles: data.profiles, initial: false },
      })
    );
  }

  function paint() {
    const current =
      snapshot.profiles.find((profile) => profile.id === snapshot.active) ||
      snapshot.profiles[0];
    const name = current ? current.name : "Profile";
    label.textContent = name;
    mark.textContent = (name.trim().charAt(0) || "?").toUpperCase();
    switcher.title = name;
    menu.replaceChildren();
    snapshot.profiles.forEach((profile) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "profile-option" + (profile.id === snapshot.active ? " is-current" : "");
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", profile.id === snapshot.active ? "true" : "false");
      button.textContent = profile.name;
      button.addEventListener("click", () => {
        choose(profile.id);
      });
      menu.append(button);
    });
    const onStylePage = document.body.classList.contains("page-style");
    const rule = document.createElement("div");
    rule.className = "profile-rule";
    rule.setAttribute("role", "separator");
    const edit = document.createElement("a");
    edit.className = "profile-option menu-link";
    edit.href = onStylePage ? "/#profile" : "#profile";
    edit.textContent = "Edit master";
    edit.addEventListener("click", (event) => {
      close();
      if (onStylePage) return;
      event.preventDefault();
      document.dispatchEvent(new CustomEvent("cvbooth:edit-master"));
    });
    const create = document.createElement("a");
    create.className = "profile-option menu-link";
    create.href = onStylePage ? "/#new-profile" : "#new-profile";
    create.textContent = "New profile";
    create.addEventListener("click", (event) => {
      close();
      if (onStylePage) return;
      event.preventDefault();
      document.dispatchEvent(new CustomEvent("cvbooth:new-profile"));
    });
    menu.append(rule, edit, create);
  }

  async function fetchSnapshot() {
    const res = await fetch("/api/profiles");
    const data = await res.json();
    if (!res.ok) throw new Error((data.errors || ["Could not load profiles."]).join("\n"));
    return data;
  }

  async function choose(id) {
    close();
    if (id === snapshot.active) return;
    const seq = ++selectSeq;
    document.dispatchEvent(new CustomEvent("cvbooth:profile-save"));
    try {
      const res = await fetch("/api/profiles/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id }),
      });
      const data = await res.json();
      if (seq !== selectSeq) return;
      if (!res.ok) throw new Error((data.errors || ["Could not switch profile."]).join("\n"));
      publish(data);
    } catch (err) {
      if (seq !== selectSeq) return;
      document.dispatchEvent(
        new CustomEvent("cvbooth:profile-error", {
          detail: { message: String(err.message || err) },
        })
      );
    }
  }

  switcher.addEventListener("click", () => {
    if (menu.hidden) open();
    else close();
  });
  document.addEventListener("click", (event) => {
    if (!switcher.contains(event.target) && !menu.contains(event.target)) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !menu.hidden) close();
  });

  window.cvboothProfile = {
    key: key,
    close: close,
    publish: publish,
    select: choose,
    ready: fetchSnapshot().then((data) => {
      snapshot = data;
      paint();
      return data;
    }),
  };
})();
