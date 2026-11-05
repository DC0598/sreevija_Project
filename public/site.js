const menuButton = document.querySelector("#menuBtn");
const nav = document.querySelector("#nav");

menuButton?.addEventListener("click", () => {
  const isOpen = nav.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(isOpen));
});
