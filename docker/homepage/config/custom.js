(() => {
	const STATUS_URLS = ["/api/config/status.json", "/status.json"];
	const REFRESH_MS = 30000;

	const SERVICES = [
		{
			title: "Docker",
			key: "docker",
			baseText: "Container runtime on brain",
			hrefContains: "docs.docker.com",
		},
		{
			title: "brain",
			key: "homepage",
			baseText: "Dashboard service on brain",
			hrefContains: ":3000",
		},
	];

	function statusLabel(status) {
		if (status === "healthy") {
			return "🟢 Healthy";
		}
		if (status === "unhealthy") {
			return "🔴 Unhealthy";
		}
		return "⚪ Unknown";
	}

	function closestCard(element) {
		if (!element) {
			return null;
		}

		return (
			element.closest("article") ||
			element.closest("li") ||
			element.closest(".service") ||
			element.closest(".card") ||
			element.closest(".item") ||
			element.closest("[class*='service']") ||
			element.closest("[class*='item']") ||
			element.parentElement ||
			null
		);
	}

	function findCard(service) {
		if (service.hrefContains) {
			const links = document.querySelectorAll("a[href]");
			for (const link of links) {
				if ((link.getAttribute("href") || "").includes(service.hrefContains) || (link.href || "").includes(service.hrefContains)) {
					const cardFromLink = closestCard(link);
					if (cardFromLink) {
						return cardFromLink;
					}
				}
			}
		}

		const cardSelectors = ["article", "li", ".service", ".card", ".item", "div"];
		const cards = document.querySelectorAll(cardSelectors.join(", "));

		for (const card of cards) {
			const text = (card.innerText || "")
				.split("\n")
				.map((line) => line.trim())
				.filter(Boolean);

			if (text.includes(service.title)) {
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

	function setCardDescription(service, text) {
		const card = findCard(service);
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

		for (const config of SERVICES) {
			const serviceState = services[config.key] || {};
			const label = statusLabel(serviceState.status);
			setCardDescription(config, `${label} | ${config.baseText}`);
		}
	}

	function applyUnknownStatuses() {
		applyStatuses({ services: {} });
	}

	async function loadStatusPayload() {
		for (const url of STATUS_URLS) {
			try {
				const response = await fetch(url, { cache: "no-store" });
				if (!response.ok) {
					continue;
				}

				const text = await response.text();
				if (!text.trim()) {
					continue;
				}

				return JSON.parse(text);
			} catch (_error) {
				// Try next URL.
			}
		}

		throw new Error("status JSON unavailable");
	}

	async function refreshStatuses() {
		try {
			const payload = await loadStatusPayload();
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
