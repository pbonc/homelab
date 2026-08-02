(() => {
  const state = { model:null, category:"all", selected:null };
  const colors = { access:"#37c8e6", deployment:"#e8bd62", telemetry:"#62d991", adsb:"#a99cf5", observability:"#55a9df", notification:"#ec7f9f", logging:"#c291e8", inventory:"#e6a85f", study:"#8bcf8d" };
  const byId = (id) => document.getElementById(id);
  const nodeById = (id) => state.model.nodes.find((node) => node.id === id);
  const categories = () => [...new Set(state.model.flows.map((flow) => flow.category))].sort();
  const filteredFlows = () => state.model.flows.filter((flow) =>
    (state.category === "all" || flow.category === state.category) &&
    (!state.selected || flow.from === state.selected || flow.to === state.selected));

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
        nodes.append(button); return button;
      }));
      section.append(heading,nodes); return section;
    }));
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
    const context=canvas.getContext("2d"); context.scale(ratio,ratio); context.lineWidth=1.35; context.globalAlpha=.58;
    filteredFlows().forEach((flow) => {
      const from=diagram.querySelector(`[data-node="${flow.from}"]`); const to=diagram.querySelector(`[data-node="${flow.to}"]`); if(!from||!to) return;
      const a=from.getBoundingClientRect(), b=to.getBoundingClientRect();
      const x1=a.right-box.left, y1=a.top+a.height/2-box.top, x2=b.left-box.left, y2=b.top+b.height/2-box.top;
      context.strokeStyle=colors[flow.category] || colors.access; context.beginPath(); context.moveTo(x1,y1);
      const bend=Math.max(28,Math.abs(x2-x1)*.42); context.bezierCurveTo(x1+bend,y1,x2-bend,y2,x2,y2); context.stroke();
      context.fillStyle=context.strokeStyle; context.beginPath(); context.moveTo(x2,y2); context.lineTo(x2-6,y2-3); context.lineTo(x2-6,y2+3); context.closePath(); context.fill();
    });
  }

  function render() { renderFilters(); renderBoundaries(); renderDetail(); requestAnimationFrame(drawConnections); }
  fetch("/api/model", {cache:"no-store"}).then((response) => { if(!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((model) => { state.model=model; render(); }).catch((error) => {
      const message=document.createElement("p"); message.className="error"; message.textContent=`Architecture model unavailable: ${error.message}`;
      byId("boundaries").replaceChildren(message);
    });
  window.addEventListener("resize", () => { if(state.model) drawConnections(); });
})();
