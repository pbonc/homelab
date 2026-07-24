from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = ROOT / "ansible"


class AnsibleLayoutTests(unittest.TestCase):
    def test_secure_connection_defaults_are_enabled(self):
        config = (ANSIBLE / "ansible.cfg").read_text(encoding="utf-8")
        self.assertIn("host_key_checking = True", config)
        self.assertNotIn("host_key_checking = False", config)

    def test_playbooks_use_explicit_fact_access(self):
        connectivity = (ANSIBLE / "playbooks" / "connectivity.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('ansible_facts["system"]', connectivity)
        self.assertNotIn("ansible_system", connectivity)

    def test_verified_nodes_are_active_inventory_hosts(self):
        inventory = (
            ANSIBLE / "inventories" / "production" / "hosts.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("brain:", inventory)
        self.assertIn("ansible_host: 192.168.1.23", inventory)
        self.assertIn("piaware:", inventory)
        self.assertIn("ansible_host: 192.168.1.27", inventory)
        self.assertRegex(inventory, r"piaware:\n\s+ansible_host: 192\.168\.1\.27\n\s+ansible_user: dar")

    def test_inventory_does_not_embed_credentials_or_private_keys(self):
        inventory_root = ANSIBLE / "inventories"
        contents = "\n".join(
            path.read_text(encoding="utf-8")
            for path in inventory_root.rglob("*.yml")
            if path.name != "vault.yml"
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

    def test_runtime_vault_is_ignored_and_example_contains_no_value(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        example = (ANSIBLE / "examples" / "vault-variables.yml.example").read_text(
            encoding="utf-8"
        )
        self.assertIn("ansible/inventories/*/group_vars/all/vault.yml", ignore)
        self.assertIn("vault_example_service_token", example)
        self.assertIn("REPLACE_INSIDE_ENCRYPTED_VAULT", example)
        self.assertNotIn("$ANSIBLE_VAULT;", example)

    def test_baseline_requires_runtime_public_key_and_preserves_password_access(self):
        defaults = (ANSIBLE / "roles" / "node_baseline" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        tasks = (ANSIBLE / "roles" / "node_baseline" / "tasks" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("HOMELAB_ADMIN_PUBLIC_KEY", defaults)
        self.assertIn("homelab_admin_public_key_normalized", defaults)
        self.assertNotIn("ssh-ed25519 AAAA", defaults)
        self.assertIn('homelab_admin_public_key_normalized.startswith("ssh-ed25519 ")', tasks)
        self.assertIn("| regex_escape", tasks)
        self.assertNotIn("ssh-keygen", tasks)
        self.assertIn('ansible_facts["os_family"]', tasks)
        self.assertNotIn("ansible_os_family", tasks)
        self.assertNotIn("PasswordAuthentication", tasks)
        self.assertNotIn("state: absent", tasks)
        self.assertIn("validate: /usr/sbin/visudo -cf %s", tasks)
        self.assertIn("homelab_admin_passwordless_sudo: true", defaults)
        self.assertIn("}}ALL\\n\"", tasks)

    def test_docker_is_opt_in_for_the_baseline(self):
        defaults = (ANSIBLE / "roles" / "node_baseline" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("homelab_install_docker: false", defaults)

    def test_piaware_preserves_its_existing_time_provider(self):
        defaults = (ANSIBLE / "roles" / "node_baseline" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        piaware = (
            ANSIBLE / "inventories" / "production" / "host_vars" / "piaware.yml"
        ).read_text(encoding="utf-8")
        tasks = (ANSIBLE / "roles" / "node_baseline" / "tasks" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("  - systemd-timesyncd", defaults)
        self.assertIn("homelab_time_service: ntpsec", piaware)
        self.assertIn("Verify the selected time provider exists", tasks)

    def test_first_run_check_mode_defers_new_user_owned_paths(self):
        tasks = (ANSIBLE / "roles" / "node_baseline" / "tasks" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("Check whether the administrator already exists", tasks)
        self.assertGreaterEqual(
            tasks.count("not ansible_check_mode or homelab_admin_before.rc == 0"),
            2,
        )
        self.assertIn("Explain first-run check-mode deferral", tasks)

    def test_break_glass_runbook_preserves_security_boundaries(self):
        runbook = (
            ROOT / "docs" / "runbooks" / "ansible-break-glass.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Do not accept it or delete the old entry", runbook)
        self.assertIn("physical console", runbook)
        self.assertIn("sudo visudo -cf /etc/sudoers", runbook)
        self.assertIn("changed=0", runbook)
        self.assertNotIn("StrictHostKeyChecking=no", runbook)
        self.assertNotIn("flightaware", runbook.lower())

    def test_backup_job_encrypts_before_windows_storage(self):
        script = (ROOT / "scripts" / "homelab_backup.sh").read_text(encoding="utf-8")
        scheduler = (
            ROOT / "scripts" / "install_backup_task.ps1"
        ).read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "backups.md").read_text(encoding="utf-8")
        self.assertIn("/mnt/c/Users/darji/HomelabBackups/restic", script)
        self.assertIn("restic backup", script)
        self.assertIn("influx backup", script)
        self.assertIn("/api/progress/export", script)
        self.assertIn("restore-test", script)
        self.assertIn("restic restore latest", script)
        self.assertIn(
            "http://192.168.1.23:8020/api/progress/export",
            script,
        )
        self.assertIn("var/cache/piaware/feeder_id", script)
        self.assertIn("--keep-daily 7", script)
        self.assertNotIn("StrictHostKeyChecking=no", script)
        self.assertNotIn("RESTIC_PASSWORD=", script)
        self.assertIn("No plaintext database export", docs)
        self.assertIn("New-ScheduledTaskTrigger -Daily", scheduler)
        self.assertIn("StartWhenAvailable", scheduler)
        self.assertIn("make backup-run", scheduler)
        self.assertIn("Interactive", scheduler)


if __name__ == "__main__":
    unittest.main()
