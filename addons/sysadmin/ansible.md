# Add-on: Ansible (sysadmin)

Apply everything below unless the user asks otherwise.

## Structure
- Inventory groups hosts in `inventory.ini` (`[web]`, `[db:vars]`) or `inventory.yml`; `ansible.cfg` sets `inventory`, `roles_path`, `host_key_checking`. Layout: `site.yml` + `inventory/` + `group_vars/` + `host_vars/` + `roles/`.
- A playbook is a YAML list of plays (`hosts`, `become`, `vars`, `roles`, `tasks`). Roles live in `roles/<name>/` (`tasks/`, `handlers/`, `templates/`, `defaults/`, `files/`, `meta/`); one concern per role.

## YAML
- 2-space indent, no tabs, start with `---`. Quote values with `{{ }}` or `: `. Check with `yamllint` and `ansible-playbook --syntax-check`.

## Idempotency
- Every task safe to re-run: `state: present|absent|started`, `creates:`/`removes:` for commands. Preview with `--check --diff`.
- Use `changed_when`/`failed_when`; `notify` a handler only on real change.

## Common modules
- `apt`/`dnf` (packages, `update_cache`), `copy`, `template`, `service` (start/enable), `file` (`state: directory|link|absent`, `mode`, `owner`), `command`/`shell`.

## Variables, facts, handlers, tags
- Precedence: `defaults/` < `group_vars` < `host_vars` < extra vars. Facts via `ansible_facts`, not deprecated `ansible_*`.
- Handlers run once at the end, triggered by `notify: Restart nginx`. Tags: `tags: [nginx]`, run with `--tags`/`--skip-tags`.

## CLI
- `ansible all -m ping`; `ansible-playbook -i inventory site.yml --check --diff`, `-l host`, `-K`, `-v`.
- `ansible-galaxy init role`, `ansible-galaxy install -r requirements.yml`; `ansible-vault create|edit|view` with `--ask-vault-pass`/`--vault-password-file`.

## Best practice
- Prefer modules over `shell`/`command`; when unavoidable add `creates`/`removes`, `changed_when`, full path. Never `ignore_errors` to hide bugs. Secrets in Vault.
