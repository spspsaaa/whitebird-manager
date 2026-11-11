"use strict";
const output = document.getElementById("output");
async function activeWhitebirdTab() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab || !tab.id || !tab.url) throw Error("Открой страницу кошельков WhiteBird.");
  const url = new URL(tab.url);
  if (url.protocol !== "https:" || url.hostname !== "whitebird.io") {
    throw Error("Расширение работает только на https://whitebird.io.");
  }
  return tab;
}
async function readFromTab(func) {
  const tab = await activeWhitebirdTab();
  const results = await chrome.scripting.executeScript({target:{tabId:tab.id},func});
  return results?.[0]?.result;
}
document.getElementById("wallets").addEventListener("click", async () => {
  output.textContent = "Чтение таблицы…";
  try {
    const result = await readFromTab(() => {
      // Only visible DOM text. Do not click or change anything on the page.
      const visible = el => {
        const s = getComputedStyle(el);
        return s.display !== "none" && s.visibility !== "hidden" && el.getClientRects().length > 0;
      };
      const clean = s => (s || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
      const exact = /^(RUB\.wb|USDT)$/i;
      const labels = [...document.querySelectorAll("td,th,span,div,a,button,p")]
        .filter(el => visible(el) && exact.test(clean(el.textContent)) &&
          ![...el.children].some(child => exact.test(clean(child.textContent))));
      const found = {};
      for (const label of labels) {
        const currency = clean(label.textContent).toUpperCase() === "USDT" ? "USDT" : "RUB.wb";
        if (found[currency]) continue;
        let parent = label;
        for (let depth = 0; parent && depth < 7; depth++, parent = parent.parentElement) {
          if (!visible(parent)) continue;
          const cells = [...parent.children].filter(visible).map(el => clean(el.innerText));
          const text = clean(parent.innerText);
          if (text.length > 260 || !text.includes(currency)) continue;
          // Match only a cell/row with a named currency and a separate balance column.
          // Avoid confusing price in USD or approximate USD equivalent with balance.
          if (cells.length >= 3) {
            const labelIndex = cells.findIndex(c => c === currency || c.startsWith(currency + " "));
            const candidates = cells.slice(labelIndex + 1);
            // Typical WhiteBird columns: currency | price | balance | equivalent | reserved | actions.
            if (labelIndex >= 0 && candidates.length >= 2) {
              const candidate = candidates[1].replace(/\s/g, "");
              if (/^\d[\d.,]*$/.test(candidate)) {found[currency] = candidate;break;}
            }
          }
        }
      }
      return {found, count: labels.length};
    });
    const found = result?.found || {};
    const lines = ["RUB.wb: " + (found["RUB.wb"] || "не найдено"),
                   "USDT: " + (found.USDT || "не найдено")];
    if (!found["RUB.wb"] || !found.USDT) lines.push("Структура таблицы может отличаться. Не считай «не найдено» нулём.");
    output.textContent = lines.join("\n");
  } catch (error) { output.textContent = error.message || "Не удалось прочитать страницу."; }
});
document.getElementById("read").addEventListener("click", async () => {
  output.textContent = "Чтение…";
  try {
    const selected = await readFromTab(() => window.getSelection()?.toString().trim().slice(0,150) || "");
    output.textContent = selected || "Сначала выдели текст на странице.";
  } catch (error) { output.textContent = error.message || "Не удалось прочитать страницу."; }
});
