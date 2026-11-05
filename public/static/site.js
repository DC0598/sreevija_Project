const menuButton = document.querySelector("#menuBtn");
const nav = document.querySelector("#nav");

menuButton?.addEventListener("click", () => {
  const isOpen = nav.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(isOpen));
});

document.querySelectorAll(".password-toggle").forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const field = toggle.closest(".password-field")?.querySelector("input");
    if (!field) return;

    const showPassword = field.type === "password";
    field.type = showPassword ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(showPassword));
    toggle.setAttribute("aria-label", showPassword ? "Hide password" : "Show password");
  });
});
