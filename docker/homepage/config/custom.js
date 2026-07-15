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
	const STARTUP_GRACE_MS = 15000;

	let graceExpired = false;
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
			setBadge(card, graceExpired ? "unavailable" : "checking", graceExpired ? "Unavailable" : "Checking");
			return;
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

	function scheduleUpdate() {
		if (updateQueued) return;
		updateQueued = true;
		window.requestAnimationFrame(() => {
			updateQueued = false;
			markLifecycleCards();
			updateBrainHealth();
		});
	}

	function start() {
		scheduleUpdate();
		new MutationObserver(scheduleUpdate).observe(document.body, { childList: true, subtree: true, characterData: true });
		window.setTimeout(() => {
			graceExpired = true;
			scheduleUpdate();
		}, STARTUP_GRACE_MS);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		start();
	}
})();
