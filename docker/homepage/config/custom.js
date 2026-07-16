(() => {
	const THRESHOLDS = {
		warning: {
			cpu: 85,
			memory: 85,
			disk: 85,
		},
		critical: {
			cpu: 95,
			memory: 95,
			disk: 95,
		},
	};
	const UNAVAILABLE_AFTER_MS = 15000;
	const WEATHER_URL = "http://192.168.1.23:8000/api/current/weather";
	const WEATHER_REFRESH_MS = 300000;
	const SECURITY_URL = "http://192.168.1.23:8010/api/status";
	const SECURITY_REFRESH_MS = 900000;

	let missingSince = null;
	let unavailableTimer = null;
	let updateQueued = false;

	function serviceCard(name) {
		for (const card of document.querySelectorAll(".service-card")) {
			const title = card.querySelector(".service-name");
			const titleText = title
				? Array.from(title.childNodes).find((node) => node.nodeType === Node.TEXT_NODE)?.textContent.trim()
				: null;
			if (titleText === name) {
				return card;
			}
		}
		return null;
	}

	function percent(text, label) {
		const match = text.match(new RegExp(`${label}\\s*(\\d+(?:\\.\\d+)?)\\s*%`, "i"));
		return match ? Number(match[1]) : null;
	}

	function bytes(value, unit) {
		const powers = { B: 0, KB: 1, MB: 2, GB: 3, TB: 4, PB: 5 };
		return Number(value) * 1024 ** (powers[unit.toUpperCase()] ?? 0);
	}

	function diskPercent(text) {
		const used = text.match(/(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB)\s*Used/i);
		const total = text.match(/(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB)\s*Total/i);
		if (!used || !total) {
			return null;
		}

		const totalBytes = bytes(total[1], total[2]);
		return totalBytes > 0 ? (bytes(used[1], used[2]) / totalBytes) * 100 : null;
	}

	function setBadge(card, state, label) {
		if (card.dataset.health !== state) {
			card.dataset.health = state;
		}

		let badge = card.querySelector(".brain-health-badge");
		if (!badge) {
			badge = document.createElement("span");
			badge.className = "brain-health-badge";
			card.appendChild(badge);
		}
		if (badge.textContent !== label) {
			badge.textContent = label;
		}
	}

	function setSecurityBadge(card, state, label) {
		card.dataset.security = state;
		let badge = card.querySelector(".security-status-badge");
		if (!badge) {
			badge = document.createElement("span");
			badge.className = "security-status-badge";
			card.appendChild(badge);
		}
		badge.textContent = label;
	}

	async function refreshSecurity() {
		const card = serviceCard("Aikido Security");
		if (card) {
			try {
				const response = await fetch(SECURITY_URL, { cache: "no-store" });
				if (!response.ok) throw new Error("HTTP " + response.status);
				const payload = await response.json();
				const counts = payload.counts || {};
				const labels = {
					clear: "Clear",
					low_medium: ((counts.medium || 0) + (counts.low || 0)) + " low/medium",
					high: (counts.high || 0) + " high",
					critical: (counts.critical || 0) + " critical",
					stale: "Stale",
					unavailable: "Unavailable",
				};
				setSecurityBadge(card, payload.status, labels[payload.status] || "Unknown");
			} catch (_error) {
				setSecurityBadge(card, "unavailable", "Unavailable");
			}
		}
		window.setTimeout(refreshSecurity, SECURITY_REFRESH_MS);
	}

	function updateBrainHealth() {
		const card = serviceCard("brain");
		if (!card) {
			return;
		}

		const text = card.textContent.replace(/\s+/g, " ");
		const cpu = percent(text, "CPU");
		const memory = percent(text, "Mem");
		const disk = diskPercent(text);

		if (cpu === null || memory === null || disk === null) {
			if (missingSince === null) {
				missingSince = Date.now();
			}

			const missingFor = Date.now() - missingSince;
			if (missingFor >= UNAVAILABLE_AFTER_MS) {
				setBadge(card, "unavailable", "Unavailable");
			} else {
				if (!card.dataset.health) {
					setBadge(card, "checking", "Checking");
				}
				if (unavailableTimer === null) {
					unavailableTimer = window.setTimeout(() => {
						unavailableTimer = null;
						scheduleUpdate();
					}, UNAVAILABLE_AFTER_MS - missingFor);
				}
			}
			return;
		}

		missingSince = null;
		if (unavailableTimer !== null) {
			window.clearTimeout(unavailableTimer);
			unavailableTimer = null;
		}

		const critical = [];
		if (cpu >= THRESHOLDS.critical.cpu) critical.push(`CPU ${Math.round(cpu)}%`);
		if (memory >= THRESHOLDS.critical.memory) critical.push(`RAM ${Math.round(memory)}%`);
		if (disk >= THRESHOLDS.critical.disk) critical.push(`Disk ${Math.round(disk)}%`);
		if (critical.length) {
			setBadge(card, "critical", `Critical: ${critical.join(", ")}`);
			return;
		}

		const warnings = [];
		if (cpu >= THRESHOLDS.warning.cpu) warnings.push(`CPU ${Math.round(cpu)}%`);
		if (memory >= THRESHOLDS.warning.memory) warnings.push(`RAM ${Math.round(memory)}%`);
		if (disk >= THRESHOLDS.warning.disk) warnings.push(`Disk ${Math.round(disk)}%`);

		if (warnings.length) {
			setBadge(card, "warning", `Attention: ${warnings.join(", ")}`);
		} else {
			setBadge(card, "active", "Active");
		}
	}

	function markLifecycleCards() {
		for (const card of document.querySelectorAll(".service-card")) {
			const description = card.querySelector(".service-description")?.textContent || "";
			if (description.startsWith("Planned |")) card.dataset.lifecycle = "planned";
			if (description.startsWith("Future |")) card.dataset.lifecycle = "future";
		}
	}

	function weatherBanner() {
		let banner = document.querySelector(".local-weather-header");
		if (banner) return banner;
		const informationWidgets = document.querySelector("#information-widgets");
		const container = document.querySelector("#inner_wrapper .container");
		if (!informationWidgets && !container) return null;
		banner = document.createElement("a");
		banner.className = "local-weather-header";
		banner.href = "http://192.168.1.23:3001/d/homelab-weather/local-weather";
		banner.setAttribute("aria-label", "Open the Local Weather dashboard in Grafana");
		banner.textContent = "Local weather: waiting for telemetry";
		if (informationWidgets) {
			informationWidgets.insertAdjacentElement("afterend", banner);
		} else {
			container.prepend(banner);
		}
		return banner;
	}

	function weatherValue(measurements, field, digits = 0) {
		const value = measurements[field]?.value;
		return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
	}

	async function refreshWeather() {
		const banner = weatherBanner();
		if (banner) {
			try {
				const response = await fetch(WEATHER_URL, { cache: "no-store" });
				if (!response.ok) throw new Error(`HTTP ${response.status}`);
				const payload = await response.json();
				const measurements = payload.data?.measurements || {};
				if (!Number.isFinite(measurements.outdoor_temperature?.value)) {
					throw new Error("no current weather");
				}
				const observed = new Date(payload.data.observed_at);
				const observedTime = Number.isNaN(observed.getTime())
					? "unknown"
					: observed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
				const freshness = payload.stale ? "STALE" : "LATEST";
				banner.dataset.state = payload.stale ? "stale" : "current";
				banner.textContent = [
					`LOCAL WEATHER ${freshness}`,
					`${weatherValue(measurements, "outdoor_temperature", 1)}\u00b0F`,
					`${weatherValue(measurements, "outdoor_humidity")}% humidity`,
					`Wind ${weatherValue(measurements, "wind_speed", 1)} mph`,
					`Rain ${weatherValue(measurements, "rain_rate", 2)} in/h`,
					`${weatherValue(measurements, "relative_pressure", 2)} inHg`,
					`UV ${weatherValue(measurements, "uv_index")}`,
					`Observed ${observedTime}`,
				].join("  |  ");
			} catch (_error) {
				banner.dataset.state = "unavailable";
				banner.textContent = "Local weather unavailable";
			}
		}
		window.setTimeout(refreshWeather, WEATHER_REFRESH_MS);
	}

	function scheduleUpdate() {
		if (updateQueued) return;
		updateQueued = true;
		window.requestAnimationFrame(() => {
			updateQueued = false;
			weatherBanner();
			markLifecycleCards();
			updateBrainHealth();
		});
	}

	function start() {
		scheduleUpdate();
		refreshWeather();
		refreshSecurity();
		new MutationObserver(scheduleUpdate).observe(document.body, { childList: true, subtree: true, characterData: true });
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		start();
	}
})();
