(() => {
  const state = { nodes: [], filter: "" };
  const labels = JSON.parse(localStorage.getItem("network-inventory-labels") || "{}");
  const byId = (id) => document.getElementById(id);
  const address = (node) => node.addresses?.[0] || "—";
  const when = (value) => value ? new Date(value).toLocaleString() : "Never";

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

  function renderTopology() {
    const root = byId("topology");
    root.replaceChildren(...state.nodes.filter((node) => node.kind !== "network").map((node) => {
      const card = document.createElement("article");
      card.className = `node ${node.status} ${node.known ? "known" : "unidentified"}`;
      const name = document.createElement("strong");
      name.textContent = labels[node.id] || node.name;
      const detail = document.createElement("span");
      detail.textContent = `${address(node)} · ${node.kind} · ${node.status}`;
      card.append(name, detail);
      return card;
    }));
  }

  function copyKnown(node) {
    const name = labels[node.id] || "replace-with-device-name";
    const value = JSON.stringify({ id: `device-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`, name, kind: "client", address: address(node), mac: node.mac }, null, 2);
    navigator.clipboard.writeText(value);
  }

  function renderUnknown() {
    const needle = state.filter.toLowerCase();
    const unknown = state.nodes.filter((node) => !node.known && [address(node), node.mac, labels[node.id]].filter(Boolean).join(" ").toLowerCase().includes(needle));
    const body = byId("unknown-table");
    body.replaceChildren(...unknown.map((node) => {
      const row = document.createElement("tr");
      const status = document.createElement("td"); status.className = `status ${node.status}`; status.textContent = node.status;
      const ip = document.createElement("td"); ip.textContent = address(node);
      const mac = document.createElement("td"); mac.textContent = node.mac || "—"; if (node.private_address) mac.append(Object.assign(document.createElement("div"), { className:"private", textContent:"Private/randomized" }));
      const labelCell = document.createElement("td"); const input = document.createElement("input"); input.value = labels[node.id] || ""; input.placeholder = "e.g. Paul's iPhone"; input.addEventListener("change", () => { labels[node.id] = input.value.trim(); localStorage.setItem("network-inventory-labels", JSON.stringify(labels)); renderTopology(); }); labelCell.append(input);
      const observed = document.createElement("td"); observed.textContent = `${when(node.first_seen_at)} → ${when(node.last_seen_at)}`;
      const action = document.createElement("td"); const button = document.createElement("button"); button.textContent = "Copy known-device JSON"; button.addEventListener("click", () => copyKnown(node)); action.append(button);
      row.append(status, ip, mac, labelCell, observed, action); return row;
    }));
    byId("empty").hidden = unknown.length > 0;
  }

  async function load() {
    const response = await fetch("/api/v1/topology", { cache:"no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json(); state.nodes = payload.nodes || [];
    renderSummary(payload.discovery); renderTopology(); renderUnknown();
  }

  byId("refresh").addEventListener("click", () => load().catch(showError));
  byId("filter").addEventListener("input", (event) => { state.filter = event.target.value; renderUnknown(); });
  function showError(error) { byId("discovery").textContent = `UNAVAILABLE · ${error.message}`; byId("discovery").className = "discovery"; }
  load().catch(showError); window.setInterval(() => load().catch(showError), 30000);
})();
