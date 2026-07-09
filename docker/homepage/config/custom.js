(() => {
	const STATUS_URL = "/api/config/status.json";
	const REFRESH_MS = 30000;

	const SERVICES = {
		Docker: {
			key: "docker",
			baseText: "Container runtime on brain",
		},
		brain: {
			key: "homepage",
			baseText: "Dashboard service on brain",
		},
	};

	function statusLabel(status) {
		if (status === "healthy") {
			return "🟢 Healthy";
		}
		if (status === "unhealthy") {
			return "🔴 Unhealthy";
		}
		return "⚪ Unknown";
	}

	function findCardByTitle(title) {
		const cardSelectors = ["article", "li", ".service", ".card", ".item", "div"];
		const cards = document.querySelectorAll(cardSelectors.join(", "));

		for (const card of cards) {
			const text = (card.innerText || "")
				.split("\n")
				.map((line) => line.trim())
				.filter(Boolean);

			if (text.includes(title)) {
				return card;
			}
		}

		return null;
	}

	function findDescriptionNode(card) {
		if (!card) {
			return null;
		}

		return (
			card.querySelector(".service-description") ||
			card.querySelector(".description") ||
			card.querySelector("small") ||
			card.querySelector("p") ||
			null
		);
	}

	function setCardDescription(title, text) {
		const card = findCardByTitle(title);
		if (!card) {
			return;
		}

		const descriptionNode = findDescriptionNode(card);
		if (descriptionNode) {
			descriptionNode.textContent = text;
			return;
		}

		const fallback = document.createElement("small");
		fallback.textContent = text;
		card.appendChild(fallback);
	}

	function applyStatuses(payload) {
		const services = (payload && payload.services) || {};

		for (const [title, config] of Object.entries(SERVICES)) {
			const service = services[config.key] || {};
			const label = statusLabel(service.status);
			setCardDescription(title, `${label} | ${config.baseText}`);
		}
	}

	function applyUnknownStatuses() {
		applyStatuses({ services: {} });
	}

	async function refreshStatuses() {
		try {
			const response = await fetch(STATUS_URL, { cache: "no-store" });
			if (!response.ok) {
				applyUnknownStatuses();
				return;
			}

			const payload = await response.json();
			applyStatuses(payload);
		} catch (_error) {
			applyUnknownStatuses();
		}
	}

	function start() {
		refreshStatuses();
		window.setInterval(refreshStatuses, REFRESH_MS);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		start();
	}
})();
