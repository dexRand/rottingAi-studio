---
name: docker
description: Docker / Docker Compose administration and debugging: build images, manage containers/networks/volumes, read logs, troubleshoot, and apply security best practices. Use when the user asks about containers, docker, compose, or a service running in Docker.
---

# Docker / Compose

Amministrazione di container basata sull'evidenza e prudente.

## Principio guida

1. **Ispeziona prima di agire**: `docker ps`, `docker logs`, `docker inspect`.
2. **Prima non distruttivo**; mai `docker system prune`/`volume rm` senza consenso.
3. **Mai montare il socket Docker** (`/var/run/docker.sock`) in container non fidati
   (specie container AI/agenti).

## Raccolta evidenze

- `docker ps -a`, `docker images`, `docker stats`
- `docker logs --tail 200 <nome>`, `docker inspect <nome>`
- `docker compose ps`, `docker compose logs`, `docker compose config -q`
- `docker system df` (spazio), `docker network ls`, `docker volume ls`

## Build e run

- Build: `docker build -t <tag> .` (multi-stage, ordine dei layer, cache).
- Run: `docker run --rm -it <img>`; mappare le porte solo su `127.0.0.1` se locale.
- Compose: `docker compose up -d`, `down`, `restart`, `logs -f`, `config -q`.

## Troubleshooting

- Container che esce subito: `docker logs` + `docker inspect --format '{{.State.ExitCode}}'`.
- "cannot connect to daemon": `docker info` (daemon attivo? permessi?).
- Lento/OOM: `docker stats`, limiti `--memory`/`--cpus`, `docker system df`.

## Sicurezza

- Niente `USER root` nell'immagine; tag immagine esatti (non `latest`).
- Volumi a privilegio minimo; scan con `trivy`; nessun mount della root host.
- Reti isolate (`docker network create`), niente porte esposte senza motivo.
