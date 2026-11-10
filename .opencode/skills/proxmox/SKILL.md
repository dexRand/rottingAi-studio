---
name: proxmox
description: Proxmox VE administration and troubleshooting: storage, networking, LXC/VMs, backup (vzdump/PBS), cluster/HA. Use when the user asks about Proxmox, a VM or container, or a virtualization/backup issue.
---

# Proxmox VE

Amministrazione di Proxmox basata sull'evidenza e prudente. Preferisci risposte
tecnicamente corrette a ipotesi sicure ma inventate.

## Raccolta evidenze

- `pvesm status`, `pveversion`, `pct list`, `qm list`
- `pct config <id>`, `qm config <id>`, `pct status <id>`
- `journalctl -u pve-cluster`, log in `/var/log/pve/`, `dmesg`
- Rete: `ip -br a`, bridge in `/etc/network/interfaces`

## Storage

- Tipi: `directory` (semplice), `lvm-thin` (thin provisioning + snapshot),
  `zfspool` (integrità/compressione), NFS/CIFS, Ceph/RBD.
- Spazio: `pvesm status` (attenzione alle unità).
- Storage `inactive` = non montato/raggiungibile: controlla rete, mount, credenziali.

## VM e container

- LXC: `pct create/start/stop/enter <id>`; log: `pct log <id>`, `/var/log/pve/lxc/`.
- VM: `qm start/stop/monitor <id>`; log: `/var/log/pve/qemu-server/<id>.log`.
- Lento/OOM: host `free -h`, `iostat`, ballooning, limiti RAM della VM.

## Backup

- `vzdump`: backup a file (vma/tar), pianificazione via GUI o cron.
- PBS (Proxmox Backup Server): dedup, verifica, restore granulare.

## Cluster / HA

- Quorum = maggioranza dei voti; **3 nodi** raccomandati (o 2 + QDevice).
- HA richiede storage condiviso + fencing (watchdog).
- `pvecm status`, `ha-manager status`.

## Sicurezza

- Nessuna operazione distruttiva senza approvazione esplicita
  (`pct destroy`/`qm destroy` mai "alla cieca").
- Backup prima di operazioni rischiose.
