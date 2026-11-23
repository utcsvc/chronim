(() => {
  if (globalThis.__chronimInstalled) return;
  globalThis.__chronimInstalled = true;
  const fail = (message, code="BROWSER_ERROR") => ({success:false,error:{message,code}});
  const select = selector => {
    if(typeof selector!=="string" || !selector) throw new Error("Selector must be a non-empty string");
    try { return document.querySelector(selector); } catch { throw new Error(`Invalid CSS selector: ${selector}`); }
  };
  async function run(action,p={}) {
    if(action==="page.source") return document.documentElement?.outerHTML || "";
    if(action==="element.wait") {
      const state=p.state??"attached", allowed=["attached","detached","visible","hidden"];
      if(!allowed.includes(state)) throw new Error(`Unsupported wait state: ${state}`);
      const end=Date.now()+Math.max(0,Number(p.timeout??10))*1000;
      while(true) {
        const el=select(p.selector), present=!!el;
        const visible=present && isVisible(el);
        const textMatches=!p.text || (el?.innerText??el?.textContent??"").includes(String(p.text));
        const done=state==="attached"?present&&textMatches:state==="detached"?!present:state==="visible"?visible&&textMatches:!visible;
        if(done) return el?describe(el):true;
        if(Date.now()>=end) break;
        await new Promise(r=>setTimeout(r,100));
      }
      const e=new Error(`Element did not reach state '${state}' before timeout: ${p.selector}`); e.code="TIMEOUT"; throw e;
    }
    if(action==="element.click") return await clickElement(p.selector, p.timeout??10);
    if(action.startsWith("element.")) {
      const el=select(p.selector);
      if(action==="element.exists") return !!el;
      if(action==="element.find_all") return Array.from(document.querySelectorAll(p.selector),describe);
      if(!el) { const e=new Error(`Element not found: ${p.selector}`); e.code="ELEMENT_NOT_FOUND"; throw e; }
      switch(action) {
        case "element.type": { el.focus(); const setter=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),"value")?.set; if(setter) setter.call(el,String(p.text??"")); else el.textContent=String(p.text??""); el.dispatchEvent(new InputEvent("input",{bubbles:true,inputType:"insertText",data:String(p.text??"")})); el.dispatchEvent(new Event("change",{bubbles:true})); return true; }
        case "element.clear": { el.focus(); if("value" in el) { const setter=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),"value")?.set; setter?setter.call(el,""):el.value=""; } else el.textContent=""; el.dispatchEvent(new Event("input",{bubbles:true})); el.dispatchEvent(new Event("change",{bubbles:true})); return true; }
        case "element.get_text": return el.innerText ?? el.textContent ?? "";
        case "element.get_attribute": return el.getAttribute(String(p.attribute));
        case "element.get_html": return el.innerHTML;
        case "element.get_style": {
          if(p.property !== undefined && p.property !== null) {
            if(typeof p.property !== "string" || !p.property.trim()) throw new Error("CSS property must be a non-empty string");
            return getComputedStyle(el).getPropertyValue(p.property.trim());
          }
          const style=getComputedStyle(el), result={};
          for(let i=0;i<style.length;i++) { const name=style[i]; result[name]=style.getPropertyValue(name); }
          return result;
        }
        case "element.set_style": {
          if(typeof p.property !== "string" || !p.property.trim()) throw new Error("CSS property must be a non-empty string");
          if(p.value === undefined || p.value === null) throw new Error("CSS value is required");
          el.style.setProperty(p.property.trim(), String(p.value));
          return true;
        }
        case "element.find": return describe(el);
      }
    }
    if(action==="keyboard.press" || action==="keyboard.hotkey") {
      const keys=action==="keyboard.press"?[p.key]:p.keys;
      if(!Array.isArray(keys) || !keys.length) throw new Error("At least one key is required");
      const target=document.activeElement||document.body;
      const normalized=keys.map(normalizeKey), modifierNames={Control:"ctrlKey",Shift:"shiftKey",Alt:"altKey",Meta:"metaKey"};
      const modifiers={ctrlKey:false,shiftKey:false,altKey:false,metaKey:false};
      const isHotkey=action==="keyboard.hotkey", modifierKeys=isHotkey?normalized.slice(0,-1):[];
      for(const key of modifierKeys) if(modifierNames[key]) { modifiers[modifierNames[key]]=true; target.dispatchEvent(new KeyboardEvent("keydown",{key,bubbles:true,cancelable:true,...modifiers})); }
      const key=normalized.at(-1);
      target.dispatchEvent(new KeyboardEvent("keydown",{key,bubbles:true,cancelable:true,...modifiers}));
      if(!isHotkey) target.dispatchEvent(new KeyboardEvent("keypress",{key,bubbles:true,cancelable:true,...modifiers}));
      if(key==="Enter" && target.form) target.form.requestSubmit();
      target.dispatchEvent(new KeyboardEvent("keyup",{key,bubbles:true,cancelable:true,...modifiers}));
      for(const mod of [...modifierKeys].reverse()) if(modifierNames[mod]) { modifiers[modifierNames[mod]]=false; target.dispatchEvent(new KeyboardEvent("keyup",{key:mod,bubbles:true,cancelable:true,...modifiers})); }
      return true;
    }
    if(action==="mouse.scroll") { window.scrollBy(Number(p.x)||0,Number(p.y)||0); return {x:scrollX,y:scrollY}; }
    if(action==="mouse.move") { const el=document.elementFromPoint(Number(p.x),Number(p.y)); if(el) el.dispatchEvent(new MouseEvent("mousemove",{clientX:Number(p.x),clientY:Number(p.y),bubbles:true})); return true; }
    throw new Error(`Unsupported content action: ${action}`);
  }
  function describe(el) { return {tag:el.tagName.toLowerCase(),id:el.id||null,classes:Array.from(el.classList||[]),text:(el.innerText||el.textContent||"").trim().slice(0,1000),attributes:Array.from(el.attributes||[]).reduce((o,a)=>(o[a.name]=a.value,o),{})}; }
  function isVisible(el) { const style=getComputedStyle(el), rect=el.getBoundingClientRect(); return style.visibility!=="hidden" && style.display!=="none" && rect.width>0 && rect.height>0; }
  async function clickElement(selector, timeout) {
    const end=Date.now()+Math.max(0,Number(timeout))*1000;
    let previous=null, stable=0, scrolled=false;
    while(true) {
      const target=select(selector);
      if(target) {
        if(!scrolled) { target.scrollIntoView({block:"center",inline:"center"}); scrolled=true; }
        const rect=target.getBoundingClientRect(), style=getComputedStyle(target);
        const enabled=!("disabled" in target && target.disabled) && target.getAttribute("aria-disabled")!=="true";
        const shown=isVisible(target), point=document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2);
        const receives=!!point && (point===target || target.contains(point));
        const box=[rect.x,rect.y,rect.width,rect.height].map(n=>Math.round(n*10)/10);
        stable=previous && box.every((n,i)=>n===previous[i])?stable+1:0; previous=box;
        if(shown && enabled && style.pointerEvents!=="none" && receives && stable>=1) { target.click(); return true; }
      }
      if(Date.now()>=end) break;
      await new Promise(r=>setTimeout(r,100));
    }
    const e=new Error(`Element did not become visible, enabled, stable, and clickable before timeout: ${selector}`); e.code="TIMEOUT"; throw e;
  }
  function normalizeKey(k) { const map={ENTER:"Enter",RETURN:"Enter",ESC:"Escape",SPACE:" ",CTRL:"Control",CMD:"Meta",ARROWUP:"ArrowUp",ARROWDOWN:"ArrowDown",ARROWLEFT:"ArrowLeft",ARROWRIGHT:"ArrowRight"}; return map[String(k).toUpperCase()]||String(k); }
  chrome.runtime.onMessage.addListener((message,_sender,respond)=>{
    if(message?.type==="chronim.ping") { respond({ok:true}); return; }
    if(message?.type==="chronim.command") { run(message.action,message.payload).then(result=>respond({success:true,result}),e=>respond(fail(e.message,e.code))); return true; }
  });
})();
