# Skills

Skill per OpenCode (formato `.opencode/skills/<id>/SKILL.md`, auto-rilevate).
Tutte le skill qui sotto sono vendored (copia locale) per funzionare **offline**.

## Origine e licenze

| Skill | Origine | Licenza |
|---|---|---|
| `find-skills` | [vercel-labs/skills](https://github.com/vercel-labs/skills/tree/main/skills/find-skills) | MIT |
| le altre 25 (dev) | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | MIT (© 2025 Addy Osmani) |

## Elenco skill

### Custom di questo progetto
- **local-ai** — come operare il runtime locale (`./ai`, ruoli, modelli, RAM, OpenCode)
- **arch-sysadmin** — amministrazione prudente Arch/CachyOS (pacman, systemd, btrfs, zram, rete)

### Scoperta skill
- **find-skills** — cerca e installa nuove skill dall'ecosistema `skills.sh` (`npx skills`).

### Sviluppo (addyosmani/agent-skills)
- **api-and-interface-design** — progettazione API/interfacce
- **browser-testing-with-devtools** — test browser con DevTools
- **ci-cd-and-automation** — CI/CD e automazione
- **code-review-and-quality** — review multi-asse (correctness/readability/architecture/security/performance)
- **code-simplification** — semplificazione del codice
- **constraint-driven-development** — sviluppo guidato da vincoli/quality gate
- **context-engineering** — gestione del contesto
- **debugging-and-error-recovery** — debugging e recovery
- **deprecation-and-migration** — deprecazione e migrazioni
- **documentation-and-adrs** — documentazione e ADR
- **doubt-driven-development** — sviluppo "dubbio-guidato"
- **frontend-ui-engineering** — UI engineering frontend
- **git-workflow-and-versioning** — workflow git e versioning
- **idea-refine** — raffinamento idee
- **incremental-implementation** — implementazione incrementale
- **interview-me** — intervista/esame tecnico
- **observability-and-instrumentation** — osservabilità e instrumentation
- **performance-optimization** — ottimizzazione performance
- **planning-and-task-breakdown** — pianificazione e scomposizione task
- **security-and-hardening** — sicurezza e hardening
- **shipping-and-launch** — release e lancio
- **source-driven-development** — sviluppo guidato dal sorgente
- **spec-driven-development** — sviluppo guidato da spec
- **test-driven-development** — TDD
- **using-agent-skills** — come usare le skill stesse

## Struttura

```
.opencode/
├── skills/          # 28 skill (SKILL.md + references/scripts locali)
│   ├── find-skills/
│   ├── code-review-and-quality/
│   └── ...
└── references/      # checklist condivise (security, performance, ...)
                     # referenziate da alcune skill come ../../references/*.md
```

## Aggiungere nuove skill

1. Via ecosistema (richiede rete): `npx skills add <owner/repo@skill>` — vedi `find-skills`.
2. Manuale: crea `.opencode/skills/<id>/SKILL.md` con frontmatter `name` + `description`.
3. Aggiornamento vendored: ri-clonare `addyosmani/agent-skills` e ricopiare `skills/` + `references/`.
