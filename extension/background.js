const VERSION = "0.1.0";
let socket = null;
let reconnectTimer = null;
let connected = false;
let serverAvailable = false;
let lastError = "";

async function config() {
  const result = await chrome.storage.local.get(["apiKey", "port", "enabled"]);
  return { apiKey: result.apiKey || "", port: Number(result.port || 8765), enabled: result.enabled !== false };
}
async function saveState(patch) {
  if (Object.hasOwn(patch, "lastError")) lastError = patch.lastError;
  await chrome.storage.local.set({ ...patch, connected, server: serverAvailable, lastError, version: VERSION });
}
async function connectBridge() {
  const cfg = await config();
  if (!cfg.enabled || !cfg.apiKey || socket) return;
  const ws = new WebSocket(`ws://127.0.0.1:${cfg.port}`);
  let authenticatedResponse = false;
  socket = ws;
  ws.onopen = () => { serverAvailable = true; saveState({}); ws.send(JSON.stringify({ type: "hello", role: "extension", token: cfg.apiKey })); };
  ws.onmessage = async event => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { ws.close(); return; }
    if (msg.type === "auth") {
      authenticatedResponse = true; serverAvailable = true;
      if (!msg.success) { await saveState({ lastError: "API key rejected" }); ws.close(); return; }
      connected = true; await saveState({ lastError: "" }); return;
    }
    if (msg.type === "request") {
      try {
        const result = await execute(msg.action, msg.payload || {});
        ws.send(JSON.stringify({ type: "response", id: msg.id, success: true, result: result ?? null }));
      } catch (e) {
        ws.send(JSON.stringify({ type: "response", id: msg.id, success: false,
          error: { code: e.code || "BROWSER_ERROR", message: e.message || String(e) } }));
      }
    }
  };
  ws.onerror = () => {};
  ws.onclose = async () => {
    if (socket === ws) socket = null;
    connected = false; if (!authenticatedResponse) serverAvailable = false; await saveState({});
    clearTimeout(reconnectTimer); reconnectTimer = setTimeout(connectBridge, 1500);
  };
}
async function currentTab(tabId = null) {
  if (tabId !== null && tabId !== undefined) {
    const id=Number(tabId);
    if(!Number.isInteger(id) || id<0) throw new Error("tab_id must be a valid Chrome tab ID");
    try { return await chrome.tabs.get(id); }
    catch { throw new Error(`Chrome tab ${id} is not available`); }
  }
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs[0]?.id) throw new Error("No active Chrome tab is available");
  return tabs[0];
}
async function inject(tabId) {
  try { await chrome.tabs.sendMessage(tabId, { type: "chronim.ping" }); }
  catch { await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] }); }
}
async function content(action, payload = {}) {
  const tab = await currentTab(payload.target_tab_id); await inject(tab.id);
  const response = await chrome.tabs.sendMessage(tab.id, { type: "chronim.command", action, payload });
  if (!response?.success) { const error = new Error(response?.error?.message || "Content command failed"); error.code = response?.error?.code; throw error; }
  return response.result;
}
async function execute(action, p) {
  switch (action) {
    case "browser.open": {
      if (typeof p.url !== "string" || !/^https?:\/\//i.test(p.url)) throw new Error("URL must use http or https");
      const tab = await currentTab(p.target_tab_id); await chrome.tabs.update(tab.id, { url: p.url }); return { url: p.url };
    }
    case "browser.back": { const t=await currentTab(p.target_tab_id); await chrome.tabs.goBack(t.id); return true; }
    case "browser.forward": { const t=await currentTab(p.target_tab_id); await chrome.tabs.goForward(t.id); return true; }
    case "browser.refresh": { const t=await currentTab(p.target_tab_id); await chrome.tabs.reload(t.id); return true; }
    case "browser.close": { const t=await currentTab(p.target_tab_id); await chrome.tabs.remove(t.id); return true; }
    case "browser.title": return (await currentTab(p.target_tab_id)).title || "";
    case "browser.url": return (await currentTab(p.target_tab_id)).url || "";
    case "browser.screenshot": { const t=await currentTab(p.target_tab_id); if(p.target_tab_id!=null && !t.active) throw new Error("Chrome can capture a screenshot only from the active tab"); return await chrome.tabs.captureVisibleTab(t.windowId, { format: "png" }); }
    case "browser.execute_js": {
      if(typeof p.code!=="string" || p.code.length>100000) throw new Error("JavaScript code must be a string under 100 KB");
      const tab=await currentTab(p.target_tab_id);
      const [injection]=await chrome.scripting.executeScript({
        target:{tabId:tab.id}, world:"MAIN", args:[p.code],
        func:async code=>await (0,eval)(code)
      });
      return injection?.result ?? null;
    }
    case "browser.sleep": await new Promise(r => setTimeout(r, Math.max(0, Math.min(Number(p.seconds)*1000, 300000)))); return true;
    case "browser.wait_for_load": {
      const tab=await currentTab(p.target_tab_id);
      if (tab.status === "complete") return true;
      return await new Promise((resolve, reject) => {
        const timer=setTimeout(() => { chrome.tabs.onUpdated.removeListener(listener); reject(Object.assign(new Error("Timed out waiting for page load"),{code:"TIMEOUT"})); }, Math.max(1,Number(p.timeout||30))*1000);
        const listener=(id,change) => { if(id===tab.id && change.status==="complete") { clearTimeout(timer); chrome.tabs.onUpdated.removeListener(listener); resolve(true); } };
        chrome.tabs.onUpdated.addListener(listener);
      });
    }
    case "trusted.click": case "trusted.type": {
      const tab=await currentTab(p.target_tab_id);
      if(!Number.isInteger(tab.id)) throw new Error("A valid tab is required for trusted input");
      await chrome.debugger.attach({tabId:tab.id}, "1.3");
      try {
        if(action==="trusted.click") {
          const x=Number(p.x), y=Number(p.y);
          if(!Number.isFinite(x)||!Number.isFinite(y)) throw new Error("x and y must be finite viewport coordinates");
          await chrome.debugger.sendCommand({tabId:tab.id}, "Input.dispatchMouseEvent", {type:"mouseMoved",x,y});
          await chrome.debugger.sendCommand({tabId:tab.id}, "Input.dispatchMouseEvent", {type:"mousePressed",x,y,button:"left",clickCount:1});
          await chrome.debugger.sendCommand({tabId:tab.id}, "Input.dispatchMouseEvent", {type:"mouseReleased",x,y,button:"left",clickCount:1});
        } else {
          if(typeof p.text!=="string") throw new Error("text must be a string");
          await chrome.debugger.sendCommand({tabId:tab.id}, "Input.insertText", {text:p.text});
        }
        return true;
      } finally { await chrome.debugger.detach({tabId:tab.id}).catch(()=>{}); }
    }
    case "page.source":
    case "element.click": case "element.type": case "element.clear": case "element.get_text": case "element.get_attribute": case "element.get_html": case "element.get_style": case "element.set_style": case "element.find": case "element.find_all": case "element.exists": case "element.wait":
    case "keyboard.press": case "keyboard.hotkey": case "mouse.scroll": case "mouse.move": return content(action, p);
    case "tabs.new": { const tab=await chrome.tabs.create(p.url?{url:p.url}:{}); return {id:tab.id,url:tab.url||"",title:tab.title||""}; }
    case "tabs.close": await chrome.tabs.remove(Number(p.tab_id)); return true;
    case "tabs.switch": { const tab=await chrome.tabs.update(Number(p.tab_id),{active:true}); await chrome.windows.update(tab.windowId,{focused:true}); return {id:tab.id,url:tab.url||"",title:tab.title||""}; }
    case "tabs.list": return (await chrome.tabs.query({})).map(t=>({id:t.id,url:t.url||"",title:t.title||"",active:!!t.active,window_id:t.windowId}));
    case "tabs.active": { const t=await currentTab(); return {id:t.id,url:t.url||"",title:t.title||"",active:true,window_id:t.windowId}; }
    default: throw Object.assign(new Error(`Unsupported Chronim action: ${action}`),{code:"PROTOCOL_ERROR"});
  }
}
chrome.runtime.onInstalled.addListener(() => connectBridge());
chrome.runtime.onStartup.addListener(() => connectBridge());
chrome.runtime.onMessage.addListener((message, _sender, respond) => {
  if (message?.type === "chronim.popup.status") {
    Promise.all([config(), currentTab().catch(() => null)]).then(([c, activeTab]) => respond({
      ok: true, connected, server: serverAvailable, version: VERSION, enabled: c.enabled,
      hasKey: !!c.apiKey, lastError,
      activeTab: activeTab ? { id: activeTab.id, title: activeTab.title || "", url: activeTab.url || "" } : null
    })); return true;
  }
  if (message?.type === "chronim.popup.tabs") {
    chrome.tabs.query({}).then(tabs => respond({ ok: true, tabs: tabs.map(t => ({
      id: t.id, title: t.title || "", url: t.url || "", active: !!t.active, window_id: t.windowId
    })) }), error => respond({ ok: false, error: error.message }));
    return true;
  }
  if (message?.type === "chronim.popup.command") {
    execute(message.action, message.payload || {}).then(
      result => respond({ ok: true, result }),
      error => respond({ ok: false, error: error.message || String(error) })
    );
    return true;
  }
  if (message?.type === "chronim.popup.save") {
    chrome.storage.local.set({ apiKey:message.apiKey, port:Number(message.port||8765), enabled:true }).then(() => {
      if(socket) socket.close(); else connectBridge(); respond({ ok:true });
    }); return true;
  }
  if (message?.type === "chronim.popup.connect") {
    chrome.storage.local.set({ enabled:true }).then(() => {
      if(socket) socket.close(); else connectBridge(); respond({ ok:true });
    }); return true;
  }
  if (message?.type === "chronim.popup.disconnect") {
    chrome.storage.local.set({enabled:false}).then(() => { if(socket) socket.close(); respond({ok:true}); }); return true;
  }
});
connectBridge();
