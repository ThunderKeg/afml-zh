const THEME_STORAGE_KEY = "afml-theme";
const THEME_DARK = "dark";
const THEME_LIGHT = "light";
let activeTheme = THEME_DARK;

const safeReadTheme = () => {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
};

const safeWriteTheme = theme => {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage failures; the button still works for this page view.
  }
};

const themeLabels = () => {
  const isZh = document.documentElement.lang.toLowerCase().startsWith("zh");
  return {
    dark: isZh ? "深色" : "Dark",
    light: isZh ? "浅色" : "Light",
    label: isZh ? "切换深色/浅色模式" : "Toggle light and dark mode",
  };
};

const updateThemeToggle = button => {
  if (!button) return;
  const labels = themeLabels();
  button.textContent = activeTheme === THEME_DARK ? labels.dark : labels.light;
  button.setAttribute("aria-label", labels.label);
  button.setAttribute("aria-checked", String(activeTheme === THEME_DARK));
};

const applyTheme = theme => {
  activeTheme = theme === THEME_LIGHT ? THEME_LIGHT : THEME_DARK;
  document.documentElement.dataset.theme = activeTheme;
  updateThemeToggle(document.querySelector(".theme-toggle"));
};

applyTheme(safeReadTheme());

const installThemeToggle = () => {
  const nav = document.querySelector(".book-topbar nav");
  if (!nav || nav.querySelector(".theme-toggle")) return;
  const button = document.createElement("button");
  button.className = "theme-toggle";
  button.type = "button";
  button.setAttribute("role", "switch");
  button.addEventListener("click", () => {
    const nextTheme = activeTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    applyTheme(nextTheme);
    safeWriteTheme(nextTheme);
  });
  nav.appendChild(button);
  updateThemeToggle(button);
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", installThemeToggle);
} else {
  installThemeToggle();
}

document.addEventListener("click", async event => {
  const button = event.target.closest(".copy-code");
  if (!button) return;
  const listing = button.closest(".code-listing");
  const code = listing && listing.querySelector("code");
  if (!code) return;
  const text = code.innerText;
  const previous = button.textContent;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  button.textContent = "已复制";
  window.setTimeout(() => {
    button.textContent = previous || "复制";
  }, 1200);
});

const tocSearch = document.querySelector(".toc-search");
const tocEntries = [...document.querySelectorAll("[data-toc-entry]")];
if (tocSearch && tocEntries.length) {
  const filterContents = () => {
    const query = tocSearch.value.trim().toLowerCase();
    for (const entry of tocEntries) {
      const matches = !query || entry.dataset.search.includes(query);
      entry.hidden = !matches;
      const details = entry.querySelector(".toc-details");
      if (details) details.open = Boolean(query && matches);
    }
    for (const part of document.querySelectorAll(".toc-part")) {
      part.hidden = !part.querySelector("[data-toc-entry]:not([hidden])");
    }
  };
  tocSearch.addEventListener("input", filterContents);
}
