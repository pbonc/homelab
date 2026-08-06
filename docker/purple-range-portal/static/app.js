const state = document.getElementById("connection-state");
const stateText = document.getElementById("state-text");
const launch = document.getElementById("open-target");
const help = document.getElementById("launch-help");
const probe = document.getElementById("tunnel-probe");
const check = document.getElementById("check-connection");

function setConnection(ready) {
  state.className = `state ${ready ? "state-ready" : "state-offline"}`;
  stateText.textContent = ready ? "Tunnel ready" : "Tunnel not detected";
  launch.classList.toggle("disabled", !ready);
  launch.setAttribute("aria-disabled", ready ? "false" : "true");
  help.innerHTML = ready
    ? "This browser can reach the isolated target through <code>127.0.0.1:3008</code>."
    : "Start the range and tunnel, then check again. No vulnerable service is exposed to the LAN.";
}

function checkConnection() {
  state.className = "state state-checking";
  stateText.textContent = "Checking tunnel";
  check.disabled = true;
  const timeout = window.setTimeout(() => {
    probe.src = "";
    check.disabled = false;
    setConnection(false);
  }, 3500);
  probe.onload = () => {
    window.clearTimeout(timeout);
    check.disabled = false;
    setConnection(true);
  };
  probe.onerror = () => {
    window.clearTimeout(timeout);
    check.disabled = false;
    setConnection(false);
  };
  probe.src = `http://127.0.0.1:3008/assets/public/images/JuiceShop_Logo.png?portal_probe=${Date.now()}`;
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("copy unavailable");
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.dataset.copy);
    try {
      await copyText(source.textContent);
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = original; }, 1200);
    } catch {
      button.textContent = "Select text";
    }
  });
});

launch.addEventListener("click", (event) => {
  if (launch.getAttribute("aria-disabled") === "true") event.preventDefault();
});
check.addEventListener("click", checkConnection);
checkConnection();
