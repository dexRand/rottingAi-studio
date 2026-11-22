# services/rag — knowledge base locale (SPEC)

Knowledge base locale per la documentazione Arch / CachyOS / Proxmox / Docker / Linux,
interrogabile dal modello base tramite un tool. **Non implementato in questa fase.**

## Decisione

| Aspetto | Scelta | Motivo |
|---|---|---|
| Backend | SQLite **FTS5** (BM25), nativo con `sqlite3` della stdlib | il corpus è un insieme modesto di documenti; su CPU e 16 GB basta, senza dipendenze né server |
| Embedding | **nessuno in v1**, solo keyword/BM25 | la ricerca lessicale copre il corpus; `bge-small` (~130 MB) resta l'upgrade se il recall misurato non basta |
| Ingestion | **drop di `.md`/`.txt`** in una cartella + **re-index esplicito** | semplice e prevedibile: nessun crawler, nessun watch, nessuna rete |
| Accesso del modello | **tool `kb_search`** (function calling) | il modello chiede la documentazione solo quando serve; i top-k entrano nel turno corrente, non nel contesto sempre attivo (la cache KV resta piccola) |
| Nativo o container | **nativo**: modulo Python stdlib, niente Docker | coerente con "llama.cpp nativo, non Docker"; Docker resta per ausiliari opzionali e il profilo `rag` del compose era aspirazionale |

## Come funziona (schema)

```
services/rag/docs/*.md|*.txt        (l'utente copia qui i documenti)
          │  re-index esplicito
          ▼
indice FTS5 in un file SQLite locale
          │  kb_search(query)  ← tool del modello base
          ▼
top-k frammenti + file di origine → iniettati nel turno corrente
```

Contratto del tool:

| Campo | Valore |
|---|---|
| nome | `kb_search` |
| input | `query` (stringa) |
| output | top-k frammenti con il `file` di origine |
| effetti | **sola lettura**: nessuna scrittura, nessun comando |

Va registrato come gli altri tool in `agent/tools.py` (`SPECS`, schema JSON) e passa dal
template di tool-calling (`config/llama.cpp/qwen3.5-kv-stable.jinja`); nessun contesto
sempre attivo.

## Non in v1

- Niente crawler né download: i documenti li mette l'utente.
- Niente ricerca semantica / embedding (solo BM25).
- Niente multi-tenant né auth: servizio solo su localhost, uso personale.
- Niente re-index automatico continuo (niente watch/inotify).
- Niente container `profile rag`: il blocco commentato in `docker-compose.yml` si toglie
  quando si implementa.

## Criterio di fatto

1. Si copia un `.md` in `services/rag/docs/` e si lancia il re-index.
2. Si pone al modello una domanda di documentazione (es. una direttiva di systemd, un
   comando `pacman`).
3. Il modello usa `kb_search` e risponde citando il file di origine, con contenuto
   corrispondente al documento.

**Stato:** SPEC, non implementato in questa fase.
