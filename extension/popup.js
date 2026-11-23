const $ = id => document.getElementById(id);
const ICON_CLOSE = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15"/></svg>';

async function send(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response?.ok) throw new Error(response?.error || "The extension could not complete that action");
  return response;
}

function displayError(message = "") { $("error").textContent = message; }

async function loadTabs() {
  const { tabs = [] } = await send({ type: "chronim.popup.tabs" });
  $("tab-count").textContent = `${tabs.length} open`;
  $("tabs-list").replaceChildren();
  $("empty-tabs").hidden = tabs.length !== 0;
  for (const tab of tabs) {
    const row = document.createElement("li");
    row.className = `tab-row${tab.active ? " active" : ""}`;
    const activate = document.createElement("button");
    activate.type = "button";
    activate.className = "tab-select";
    activate.title = tab.title || tab.url || "Untitled tab";
    activate.setAttribute("aria-label", `Switch to ${tab.title || tab.url || "untitled tab"}`);
    const marker = document.createElement("span");
    marker.className = "tab-marker";
    marker.setAttribute("aria-hidden", "true");
    const copy = document.createElement("span");
    copy.className = "tab-copy";
    const title = document.createElement("strong");
    title.textContent = tab.title || "New tab";
    const host = document.createElement("small");
    try { host.textContent = new URL(tab.url).host || tab.url; } catch { host.textContent = tab.url || ""; }
    copy.append(title, host);
    activate.append(marker, copy);
    activate.addEventListener("click", () => runCommand("tabs.switch", { tab_id: tab.id }));
    const close = document.createElement("button");
    close.type = "button";
    close.className = "tab-close";
    close.innerHTML = ICON_CLOSE;
    close.setAttribute("aria-label", `Close ${tab.title || "tab"}`);
    close.addEventListener("click", () => runCommand("tabs.close", { tab_id: tab.id }));
    row.append(activate, close);
    $("tabs-list").append(row);
  }
}

async function refresh() {
  try {
    const state = await send({ type: "chronim.popup.status" });
    $("status").textContent = state.connected ? "Connected" : "Disconnected";
    $("dot").classList.toggle("online", state.connected);
    $("server").textContent = state.server ? "Bridge running" : "Bridge offline";
    $("version").textContent = state.version || "0.1.0";
    $("connect").hidden = state.connected || !state.hasKey;
    if (state.activeTab) {
      $("page-title").textContent = state.activeTab.title || "Untitled page";
      if (document.activeElement !== $("address")) $("address").value = state.activeTab.url || "";
    } else {
      $("page-title").textContent = "No active tab";
      if (document.activeElement !== $("address")) $("address").value = "";
    }
    if (state.lastError) displayError(state.lastError);
    await loadTabs();
  } catch (error) { displayError(error.message); }
}

async function runCommand(action, payload = {}) {
  displayError("");
  try { await send({ type: "chronim.popup.command", action, payload }); await refresh(); }
  catch (error) { displayError(error.message); }
}

$("navigate-form").addEventListener("submit", event => {
  event.preventDefault();
  let url = $("address").value.trim();
  if (!url) return;
  if (!/^[a-z][a-z\d+.-]*:\/\//i.test(url)) url = `https://${url}`;
  if (!/^https?:\/\//i.test(url)) { displayError("Use an http or https address"); return; }
  runCommand("browser.open", { url });
});

document.querySelectorAll("[data-command]").forEach(button => {
  button.addEventListener("click", () => runCommand(button.dataset.command));
});
$("new-tab").addEventListener("click", () => runCommand("tabs.new"));
$("capture").addEventListener("click", async () => {
  try {
    const { result } = await send({ type: "chronim.popup.command", action: "browser.screenshot" });
    $("screenshot").src = result;
    $("screenshot-wrap").hidden = false;
    displayError("");
  } catch (error) { displayError(error.message); }
});
$("hide-capture").addEventListener("click", () => { $("screenshot-wrap").hidden = true; $("screenshot").removeAttribute("src"); });

$("save").addEventListener("click", async () => {
  const apiKey = $("key").value.trim();
  const port = Number($("port").value);
  if (apiKey.length < 32) { displayError("Enter a key with at least 32 characters"); return; }
  if (!Number.isInteger(port) || port < 1 || port > 65535) { displayError("Enter a valid bridge port"); return; }
  try {
    await send({ type: "chronim.popup.save", apiKey, port });
    $("key").value = "";
    displayError("");
    setTimeout(refresh, 250);
    setTimeout(refresh, 1200);
  } catch (error) { displayError(error.message); }
});
$("disconnect").addEventListener("click", async () => {
  try { await send({ type: "chronim.popup.disconnect" }); await refresh(); }
  catch (error) { displayError(error.message); }
});
$("connect").addEventListener("click", async () => {
  try { await send({ type: "chronim.popup.connect" }); displayError(""); setTimeout(refresh, 400); }
  catch (error) { displayError(error.message); }
});

refresh();
const poller = setInterval(refresh, 1800);
window.addEventListener("unload", () => clearInterval(poller), { once: true });
