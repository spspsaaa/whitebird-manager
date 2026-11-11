"use strict";
const output = document.getElementById("output");
document.getElementById("read").addEventListener("click", async () => {
  output.textContent = "Чтение…";
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab || !/^https:\/\//i.test(tab.url || "")) {
      output.textContent = "Открой защищённую страницу WhiteBird (https://).";
      return;
    }
    // Only access the tab after the user explicitly clicks this button.
    const results = await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      func: () => window.getSelection()?.toString().trim().slice(0, 150) || ""
    });
    const selected = results?.[0]?.result || "";
    if (!selected) {
      output.textContent = "Сначала выдели на странице только сумму баланса.";
      return;
    }
    // Display locally only; never transmit or persist selected content.
    output.textContent = selected;
  } catch {
    output.textContent = "Не удалось прочитать страницу. Проверь, разрешены ли расширения в этом профиле.";
  }
});
