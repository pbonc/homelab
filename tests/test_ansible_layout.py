from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = ROOT / "ansible"


class AnsibleLayoutTests(unittest.TestCase):
    def test_secure_connection_defaults_are_enabled(self):
        config = (ANSIBLE / "ansible.cfg").read_text(encoding="utf-8")
        self.assertIn("host_key_checking = True", config)
        self.assertNotIn("host_key_checking = False", config)

    def test_verified_nodes_are_active_inventory_hosts(self):
        inventory = (
            ANSIBLE / "inventories" / "production" / "hosts.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("brain:", inventory)
        self.assertIn("ansible_host: 192.168.1.23", inventory)
        self.assertIn("piaware:", inventory)
        self.assertIn("ansible_host: 192.168.1.27", inventory)

    def test_inventory_does_not_embed_credentials_or_private_keys(self):
        inventory_root = ANSIBLE / "inventories"
        contents = "\n".join(
            path.read_text(encoding="utf-8")
            for path in inventory_root.rglob("*.yml")
        ).lower()
        forbidden = (
            "ansible_password",
            "ansible_become_password",
            "ansible_private_key_file",
            "private_key",
            "client_secret",
            "api_token",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, contents)

    def test_baseline_requires_runtime_public_key_and_preserves_password_access(self):
        defaults = (ANSIBLE / "roles" / "node_baseline" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        tasks = (ANSIBLE / "roles" / "node_baseline" / "tasks" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("HOMELAB_ADMIN_PUBLIC_KEY", defaults)
        self.assertNotIn("ssh-ed25519 AAAA", defaults)
        self.assertNotIn("PasswordAuthentication", tasks)
        self.assertNotIn("state: absent", tasks)
        self.assertIn("validate: /usr/sbin/visudo -cf %s", tasks)
        self.assertIn("homelab_admin_passwordless_sudo: true", defaults)

    def test_docker_is_opt_in_for_the_baseline(self):
        defaults = (ANSIBLE / "roles" / "node_baseline" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("homelab_install_docker: false", defaults)


if __name__ == "__main__":
    unittest.main()
