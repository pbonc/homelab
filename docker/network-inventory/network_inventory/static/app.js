(() => {
  const state = { nodes: [], filter: "" };
  const labels = JSON.parse(localStorage.getItem("network-inventory-labels") || "{}");
  const connections = JSON.parse(localStorage.getItem("network-inventory-connections") || "{}");
  const byId = (id) => document.getElementById(id);
  const address = (node) => node.addresses?.[0] || "—";
  const when = (value) => value ? new Date(value).toLocaleString() : "Never";
  const connection = (node) => connections[node.id] || node.connection || "unknown";

  function renderSummary(discovery) {
    const devices = state.nodes.filter((node) => node.kind !== "network");
    byId("online-count").textContent = devices.filter((node) => node.status === "online").length;
    byId("offline-count").textContent = devices.filter((node) => node.status === "offline").length;
    byId("unknown-count").textContent = devices.filter((node) => !node.known).length;
    byId("private-count").textContent = devices.filter((node) => node.private_address).length;
    const status = byId("discovery");
    status.className = `discovery ${discovery.state}`;
    status.textContent = `${discovery.state.toUpperCase()} · ${when(discovery.last_completed_at)}`;
  }

  function nodeCard(node) {
    const card = document.createElement("article");
    card.className = `node ${node.status} ${node.known ? "known" : "unidentified"}`;
    const name = document.createElement("strong");
    name.textContent = labels[node.id] || node.name;
    const detail = document.createElement("span");
    detail.textContent = `${address(node)} · ${node.vendor || node.kind} · ${node.status}`;
    card.append(name, detail);
    return card;
  }

  function renderTopology() {
    const root = byId("topology");
    const devices = state.nodes.filter((node) => node.kind !== "network");
    const groups = [
      ["ethernet", "Wired / Ethernet"],
      ["wifi", "Wi-Fi"],
      ["unknown", "Connection unknown"],
    ];
    root.replaceChildren(...groups.map(([key, title]) => {
      const section = document.createElement("section");
      section.className = "connection-group";
      const heading = document.createElement("h3");
      heading.textContent = title;
      const nodes = document.createElement("div");
      nodes.className = "connection-nodes";
      const matching = devices.filter((node) => connection(node) === key);
      if (matching.length) nodes.replaceChildren(...matching.map(nodeCard));
      else nodes.textContent = "No devices classified here.";
      section.append(heading, nodes);
      return section;
    }));
  }

  async function copyKnown(node) {
    const name = labels[node.id] || "replace-with-device-name";
    const value = JSON.stringify({
      id: `device-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
      name,
      kind: "client",
      connection: connection(node),
      address: address(node),
      mac: node.mac,
    }, null, 2);
    await navigator.clipboard.writeText(value);
  }

  function renderUnknown() {
    const needle = state.filter.toLowerCase();
    const unknown = state.nodes.filter((node) => !node.known && [
      address(node), node.mac, node.vendor, node.hostname, labels[node.id],
    ].filter(Boolean).join(" ").toLowerCase().includes(needle));
    const body = byId("unknown-table");
    body.replaceChildren(...unknown.map((node) => {
      const row = document.createElement("tr");
      const status = document.createElement("td");
      status.className = `status ${node.status}`;
      status.textContent = node.status;
      const ip = document.createElement("td"); ip.textContent = address(node);
      const mac = document.createElement("td"); mac.textContent = node.mac || "—";
      if (node.private_address) mac.append(Object.assign(document.createElement("div"), { className:"private", textContent:"Private/randomized" }));
      const clues = document.createElement("td");
      clues.textContent = [node.hostname, node.vendor].filter(Boolean).join(" · ") || "No hostname/vendor";
      const labelCell = document.createElement("td");
      const input = document.createElement("input");
      input.value = labels[node.id] || "";
      input.placeholder = "e.g. Paul's iPhone";
      labelCell.append(input);
      const connectionCell = document.createElement("td");
      const select = document.createElement("select");
      for (const [value, text] of [["unknown", "Unknown"], ["ethernet", "Wired"], ["wifi", "Wi-Fi"]]) {
        const option = document.createElement("option");
        option.value = value; option.textContent = text; option.selected = connection(node) === value;
        select.append(option);
      }
      connectionCell.append(select);
      const observed = document.createElement("td");
      observed.textContent = `${when(node.first_seen_at)} → ${when(node.last_seen_at)}`;
      const action = document.createElement("td");
      const apply = document.createElement("button");
      apply.textContent = "Apply";
      apply.addEventListener("click", () => {
        labels[node.id] = input.value.trim();
        connections[node.id] = select.value;
        localStorage.setItem("network-inventory-labels", JSON.stringify(labels));
        localStorage.setItem("network-inventory-connections", JSON.stringify(connections));
        apply.textContent = "Saved";
        window.setTimeout(() => { apply.textContent = "Apply"; }, 1200);
        renderTopology();
      });
      const copy = document.createElement("button");
      copy.textContent = "Copy known-device JSON";
      copy.addEventListener("click", () => copyKnown(node));
      action.append(apply, document.createTextNode(" "), copy);
      row.append(status, ip, mac, clues, labelCell, connectionCell, observed, action);
      return row;
    }));
    byId("empty").hidden = unknown.length > 0;
  }

  async function load() {
    const response = await fetch("/api/v1/topology", { cache:"no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.nodes = payload.nodes || [];
    renderSummary(payload.discovery); renderTopology(); renderUnknown();
  }

  function showError(error) {
    byId("discovery").textContent = `UNAVAILABLE · ${error.message}`;
    byId("discovery").className = "discovery";
  }
  byId("refresh").addEventListener("click", () => load().catch(showError));
  byId("filter").addEventListener("input", (event) => { state.filter = event.target.value; renderUnknown(); });
  load().catch(showError);
  window.setInterval(() => load().catch(showError), 30000);
})();
