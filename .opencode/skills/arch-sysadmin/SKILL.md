---
name: arch-sysadmin
description: Prudent Arch Linux / CachyOS system administration and troubleshooting: pacman, systemd/journalctl, btrfs, zram, networking, kernel, and log analysis. Use when the user asks to diagnose or fix the Linux system, analyze logs, manage packages or services, or inspect hardware/network state.
---

# Arch / CachyOS Sysadmin

Amministrazione di sistema basata sull'evidenza e prudente. Preferisci risposte
tecnicamente corrette e caute rispetto a ipotesi sicure ma inventate.

## Principio guida

1. **Raccogli evidenze prima di agire**: leggi log e stato, non assumere.
2. **Prima non distruttivo**: ispeziona, poi proponi, poi (con approvazione) agisci.
3. **Niente sudo automatico**; mai modificare firewall, bootloader, kernel o
   partizionamento senza consenso esplicito.

## Raccolta evidenze

- Hardware/CPU: `lscpu`, `inxi -Fazy`
- Memoria/swap (zram): `free -h`, `zramctl`, `swapon --show`
- Pacchetti: `pacman -Q <pkg>`, `pacman -Qi <pkg>`, `pacman -Ss <term>`,
  orfani: `pacman -Qtdq`
- systemd: `systemctl status <unit>`, `systemctl --failed`,
  `journalctl -u <unit> -b -e`, `journalctl -p 3 -b`
- Kernel: `uname -a`, `dmesg -T | tail`, `journalctl -k -b`
- Storage: `lsblk -f`, `df -h`, `btrfs filesystem usage /`
- Rete: `ip -br a`, `resolvectl status`, `nmcli`, `ss -tulpn`
- Log: `journalctl -b -p warning`

## Gestione pacchetti (Arch / CachyOS)

- Installazione: `sudo pacman -S <pkg>` (ufficiale), AUR via `paru`/`yay`.
- CachyOS aggiunge repo ottimizzati e un kernel custom (`linux-cachyos`);
  `cachyos-kernel-manager` gestisce la selezione del kernel.
- Aggiornamento completo: `sudo pacman -Syu` (leggere prima le news su
  archlinux.org/news). Mai aggiornamenti parziali.

## systemd in breve

- `systemctl status|enable|disable|start|stop|restart <unit>`
- Perché un'unità fallisce: `journalctl -u <unit> -b --no-pager | tail -100`
- Analisi boot: `systemd-analyze blame`

## btrfs (questa macchina: LUKS + btrfs)

- Subvolumi: `btrfs subvolume list /`
- Snapshot/rollback via snapper se configurato, altrimenti
  `btrfs subvolume snapshot`.
- Integrità/riparazione: `sudo btrfs scrub start /`, `btrfs device stats /`.
- Spazio: `btrfs filesystem usage /` (attenzione a "unallocated").

## zram / swap

- La macchina usa zram (zstd) come swap: `zramctl`.
- Lo swappiness è già ottimizzato da CachyOS: non modificarlo alla cieca.

## Postura di sicurezza

- Nessuna esecuzione cieca di comandi trovati online.
- Nessun sudo automatico; nessuna modifica a firewall/bootloader/kernel senza
  consenso. Per comandi agentici, richiedere approvazione esplicita
  (permissions OpenCode).
