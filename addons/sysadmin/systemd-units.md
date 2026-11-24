# Add-on: systemd units (sysadmin)

Apply everything below unless the user asks otherwise.

## Unit files
- INI with optional `[Unit]`, `[Service]`, `[Install]`; suffix `.service` or `.timer`.
- Local units in `/etc/systemd/system/`; `/usr/lib/systemd/system/` is package-owned.
- `[Unit]`: `Description=`, `After=network-online.target`, `Wants=`, `Requires=`.

## [Service]
- `Type=simple|oneshot|forking`; `ExecStart=/usr/bin/app --flag` (absolute, one line), `ExecStop=`.
- `Restart=on-failure`, `RestartSec=5`, `User=app`, `WorkingDirectory=/srv/app`.
- `Environment=KEY=value`, `EnvironmentFile=/etc/app.env`; no secrets in the unit.
- `[Install]` `WantedBy=multi-user.target`.

## Hardening
- `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=true`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=AF_INET AF_INET6`, `LockPersonality=true`, `MemoryDenyWriteExecute=true`.

## Timers
- `<name>.timer` starts `<name>.service` (service needs no `[Install]`).
- `OnCalendar=daily`/`*-*-* 03:00:00`, `OnBootSec=15min`, `OnUnitActiveSec=1h`, `Persistent=true`; timer needs `WantedBy=timers.target`.

## Apply
- Edit, `systemctl daemon-reload`, `systemctl enable --now <name>.service|.timer`; debug: `systemctl status`, `journalctl -u <name> -e`.
