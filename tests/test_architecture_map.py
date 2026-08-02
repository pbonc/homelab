from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "docker" / "architecture-map"


class ArchitectureMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = json.loads(
            (APP / "model" / "architecture.json").read_text(encoding="utf-8")
        )

    def test_model_references_existing_nodes_and_boundaries(self) -> None:
        node_ids = {node["id"] for node in self.model["nodes"]}
        boundary_ids = {boundary["id"] for boundary in self.model["boundaries"]}
        self.assertEqual(len(node_ids), len(self.model["nodes"]))
        self.assertTrue(all(node["boundary"] in boundary_ids for node in self.model["nodes"]))
        self.assertTrue(all(flow["from"] in node_ids and flow["to"] in node_ids for flow in self.model["flows"]))

    def test_model_covers_deployed_data_platforms(self) -> None:
        node_ids = {node["id"] for node in self.model["nodes"]}
        self.assertTrue({"homepage", "collector", "influx", "grafana", "prometheus", "loki", "ntfy", "inventory"} <= node_ids)
        self.assertEqual(self.model["schema_version"], "1.0.0")

    def test_site_has_filters_selection_and_accessible_flow_list(self) -> None:
        index = (APP / "static" / "index.html").read_text(encoding="utf-8")
        script = (APP / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Data Flow Explorer", index)
        self.assertIn('id="text-flows"', index)
        self.assertIn("filteredFlows", script)
        self.assertIn("state.selected", script)
        self.assertIn("state.hovered", script)
        self.assertIn("updateTrace", script)
        self.assertIn("renderFocus", script)
        self.assertIn("overviewFlows", script)
        self.assertIn("context.lineTo(laneX,y2)", script)
        self.assertIn("inboundArrow", script)
        self.assertIn("outboundArrow", script)
        self.assertIn('selectedHeading.textContent="Selected"', script)
        self.assertIn("[hidden] { display:none !important; }", (APP / "static" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn('id="focus-view"', index)
        self.assertIn('/api/model', script)

    def test_compose_is_lan_bound_and_constrained(self) -> None:
        compose = (APP / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('"192.168.1.23:8040:8040"', compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("cap_drop:", compose)
        self.assertIn("/api/health", compose)

    def test_homepage_links_to_architecture_map(self) -> None:
        services = (ROOT / "docker" / "homepage" / "config" / "services.yaml").read_text(encoding="utf-8")
        self.assertIn("Architecture Map:", services)
        self.assertIn("http://192.168.1.23:8040/api/health", services)


if __name__ == "__main__":
    unittest.main()
