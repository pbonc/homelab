(() => {
  const state = { model:null, category:"all", selected:null, hovered:null };
  const colors = { access:"#37c8e6", deployment:"#e8bd62", telemetry:"#62d991", adsb:"#a99cf5", observability:"#55a9df", notification:"#ec7f9f", logging:"#c291e8", inventory:"#e6a85f", study:"#8bcf8d" };
  const byId = (id) => document.getElementById(id);
  const nodeById = (id) => state.model.nodes.find((node) => node.id === id);
  const categories = () => [...new Set(state.model.flows.map((flow) => flow.category))].sort();
  const filteredFlows = () => state.model.flows.filter((flow) =>
    (state.category === "all" || flow.category === state.category) &&
    (!state.selected || flow.from === state.selected || flow.to === state.selected));
  const traceNode = () => state.selected || state.hovered;

  function renderFilters() {
    byId("filters").replaceChildren(...["all", ...categories()].map((category) => {
      const button = document.createElement("button");
      button.type = "button"; button.className = `filter${state.category === category ? " active" : ""}`;
      button.textContent = category === "all" ? "All flows" : category;
      button.addEventListener("click", () => { state.category = category; render(); });
      return button;
    }));
  }

  function renderBoundaries() {
    const active = new Set(filteredFlows().flatMap((flow) => [flow.from, flow.to]));
    const boundaries = [...state.model.boundaries].sort((a,b) => a.order - b.order);
    byId("boundaries").replaceChildren(...boundaries.map((boundary) => {
      const section = document.createElement("section"); section.className = "boundary";
      const heading = document.createElement("h3"); heading.textContent = boundary.name;
      const nodes = document.createElement("div"); nodes.className = "nodes";
      nodes.replaceChildren(...state.model.nodes.filter((node) => node.boundary === boundary.id).map((node) => {
        const button = document.createElement("button");
        button.type = "button"; button.className = `node${state.selected === node.id ? " selected" : ""}${active.has(node.id) ? "" : " dim"}`;
        button.dataset.node = node.id; button.dataset.type = node.type;
        button.innerHTML = `<strong></strong><small></small>`;
        button.querySelector("strong").textContent = node.name;
        button.querySelector("small").textContent = `${node.type} · ${node.endpoint}`;
        button.addEventListener("click", () => { state.selected = state.selected === node.id ? null : node.id; render(); });
        button.addEventListener("mouseenter", () => { state.hovered=node.id; updateTrace(); });
        button.addEventListener("mouseleave", () => { state.hovered=null; updateTrace(); });
        button.addEventListener("focus", () => { state.hovered=node.id; updateTrace(); });
        button.addEventListener("blur", () => { state.hovered=null; updateTrace(); });
        nodes.append(button); return button;
      }));
      section.append(heading,nodes); return section;
    }));
  }

  function traceCard(flow, direction) {
    const peer=nodeById(direction === "input" ? flow.from : flow.to);
    const item=document.createElement("article"); item.className=`trace-card ${direction === "output" ? "output" : "input"}`;
    const name=document.createElement("strong"); name.textContent=peer.name;
    const detail=document.createElement("span"); detail.textContent=`${flow.label} · ${flow.protocol}`;
    item.append(name,detail); return item;
  }

  function renderFocus() {
    const focus=byId("focus-view");
    if (!state.selected) { focus.hidden=true; byId("boundaries").hidden=false; byId("connections").hidden=false; return; }
    const node=nodeById(state.selected); const flows=filteredFlows();
    const inputs=flows.filter((flow) => flow.to === node.id);
    const outputs=flows.filter((flow) => flow.from === node.id);
    const toolbar=document.createElement("div"); toolbar.className="focus-toolbar";
    const note=document.createElement("p"); note.textContent=`Focused trace · ${inputs.length} inputs · ${outputs.length} outputs`;
    const back=document.createElement("button"); back.type="button"; back.className="back"; back.textContent="← Full map";
    back.addEventListener("click", () => { state.selected=null; render(); }); toolbar.append(note,back);
    const lanes=document.createElement("div"); lanes.className="trace-lanes";
    const incoming=document.createElement("section"); incoming.className="trace-lane"; incoming.innerHTML="<h3>Inputs</h3>";
    if(inputs.length) incoming.append(...inputs.map((flow) => traceCard(flow,"input"))); else incoming.append(Object.assign(document.createElement("p"),{className:"trace-empty",textContent:"No inputs in this filter"}));
    const center=document.createElement("article"); center.className="trace-center";
    const centerName=document.createElement("strong"); centerName.textContent=node.name;
    const centerDetail=document.createElement("span"); centerDetail.textContent=`${node.type} · ${node.endpoint}`; center.append(centerName,centerDetail);
    const outgoing=document.createElement("section"); outgoing.className="trace-lane"; outgoing.innerHTML="<h3>Outputs</h3>";
    if(outputs.length) outgoing.append(...outputs.map((flow) => traceCard(flow,"output"))); else outgoing.append(Object.assign(document.createElement("p"),{className:"trace-empty",textContent:"No outputs in this filter"}));
    const inboundArrow=document.createElement("div"); inboundArrow.className="trace-arrow inbound"; inboundArrow.setAttribute("aria-hidden","true");
    const outboundArrow=document.createElement("div"); outboundArrow.className="trace-arrow outbound"; outboundArrow.setAttribute("aria-hidden","true");
    lanes.append(incoming,inboundArrow,center,outboundArrow,outgoing); focus.replaceChildren(toolbar,lanes);
    focus.hidden=false; byId("boundaries").hidden=true; byId("connections").hidden=true;
  }

  function updateTrace() {
    const traced=traceNode();
    document.querySelectorAll(".node").forEach((button) => {
      button.classList.toggle("tracing", Boolean(traced && button.dataset.node === traced));
    });
    drawConnections();
  }

  function renderDetail() {
    const detail = byId("detail"); const copy = detail.querySelector(".detail-copy");
    const node = state.selected ? nodeById(state.selected) : null;
    copy.replaceChildren();
    const eyebrow = document.createElement("p"); eyebrow.className="eyebrow"; eyebrow.textContent = node ? node.type.toUpperCase() : "VISIBLE FLOWS";
    const title = document.createElement("h2"); title.textContent = node ? node.name : `${filteredFlows().length} data flows`;
    const summary = document.createElement("p"); summary.textContent = node ? node.summary : "Select a component to isolate its immediate inputs and outputs.";
    const endpoint = document.createElement("p"); if (node) endpoint.innerHTML = `Endpoint: <code></code>`, endpoint.querySelector("code").textContent=node.endpoint;
    copy.append(eyebrow,title,summary); if(node) copy.append(endpoint);
    byId("flow-list").replaceChildren(...filteredFlows().map((flow) => {
      const item=document.createElement("div"); item.className=`flow ${flow.category}`;
      const main=document.createElement("strong"); main.textContent=`${nodeById(flow.from).name} → ${nodeById(flow.to).name}`;
      const meta=document.createElement("span"); meta.textContent=`${flow.label} · ${flow.protocol}`;
      item.append(main,meta); return item;
    }));
    byId("text-flows").replaceChildren(...filteredFlows().map((flow) => {
      const item=document.createElement("li"); item.textContent=`${nodeById(flow.from).name} to ${nodeById(flow.to).name}: ${flow.label} (${flow.protocol})`; return item;
    }));
  }

  function drawConnections() {
    const canvas=byId("connections"); const diagram=canvas.parentElement; const ratio=window.devicePixelRatio || 1;
    const box=diagram.getBoundingClientRect(); canvas.width=box.width*ratio; canvas.height=box.height*ratio;
    const context=canvas.getContext("2d"); context.scale(ratio,ratio);
    const traced=traceNode();
    filteredFlows().forEach((flow) => {
      const from=diagram.querySelector(`[data-node="${flow.from}"]`); const to=diagram.querySelector(`[data-node="${flow.to}"]`); if(!from||!to) return;
      const a=from.getBoundingClientRect(), b=to.getBoundingClientRect();
      const forward=b.left >= a.right;
      const x1=(forward ? a.right : a.left)-box.left, y1=a.top+a.height/2-box.top;
      const x2=(forward ? b.left : b.right)-box.left, y2=b.top+b.height/2-box.top;
      const active=!traced || flow.from===traced || flow.to===traced;
      const width=traced ? (active ? 3.6 : .8) : 2.1;
      const alpha=traced ? (active ? .96 : .07) : .70;
      const bend=Math.max(32,Math.abs(x2-x1)*.44);
      const curve=() => {
        context.beginPath(); context.moveTo(x1,y1);
        context.bezierCurveTo(x1+(forward?bend:-bend),y1,x2+(forward?-bend:bend),y2,x2,y2);
      };
      context.globalAlpha=active ? alpha : .07;
      context.strokeStyle="#07111f"; context.lineWidth=width+3; curve(); context.stroke();
      context.strokeStyle=colors[flow.category] || colors.access; context.lineWidth=width; curve(); context.stroke();
      context.fillStyle=context.strokeStyle; context.beginPath(); context.arc(x1,y1,active?3.2:2,0,Math.PI*2); context.fill();
      context.beginPath(); context.moveTo(x2,y2); context.lineTo(x2+(forward?-8:8),y2-4); context.lineTo(x2+(forward?-8:8),y2+4); context.closePath(); context.fill();
    });
    context.globalAlpha=1;
  }

  function render() { renderFilters(); renderBoundaries(); renderFocus(); renderDetail(); if(!state.selected) requestAnimationFrame(drawConnections); }
  fetch("/api/model", {cache:"no-store"}).then((response) => { if(!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((model) => { state.model=model; render(); }).catch((error) => {
      const message=document.createElement("p"); message.className="error"; message.textContent=`Architecture model unavailable: ${error.message}`;
      byId("boundaries").replaceChildren(message);
    });
  window.addEventListener("resize", () => { if(state.model) drawConnections(); });
})();
