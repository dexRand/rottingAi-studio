# Architettura

## Idea: un modello, tanti add-on

Cambiare modello su CPU costa due volte: il tempo di caricamento e, soprattutto,
la **perdita della cache KV** — tutta la conversazione va rielaborata (prefill),
e su CPU il prefill di qualche migliaio di token richiede decine di secondi.

Quindi: **un solo modello base sempre caricato** e, davanti, un **router** che per
ogni richiesta sceglie quali add-on servono e li aggiunge **in fondo** al contesto.

```
client (OpenCode / web UI / curl)
   │  API OpenAI  http://127.0.0.1:8080/v1
   ▼
router proxy  (router/proxy.py, solo libreria standard)
   │  1. legge gli ultimi N messaggi utente (history_messages)
   │  2. Magika: linguaggio di file allegati / blocchi di codice
   │  3. classificatore di intento: categoria + add-on (sì/no, una passata)
   │  4. soglia: sotto -> nessuna ipotesi, nessun add-on
   │  5. composer: add-on nel turno utente corrente, PRIMA del prompt intatto
   ▼
llama-server  http://127.0.0.1:8081  (interno, un solo GGUF, --jinja)
```

## Perché gli add-on non rompono la cache KV

llama-server riusa la cache KV per il **prefisso comune** tra una richiesta e la
successiva. Il composer (`router/compose.py`) garantisce che il prefisso non cambi:

- un add-on viene inserito **una volta sola**, nel messaggio utente in cui serve;
- nelle richieste successive viene reinserito **identico, nella stessa posizione**
  (i client OpenAI sono stateless e rimandano tutta la storia: il composer
  ricorda, per conversazione, a quale indice di messaggio sta ogni add-on);
- **non si scarica mai** un add-on a metà conversazione: si ripulisce solo con
  una nuova conversazione (primo messaggio utente diverso);
- un retry dello stesso turno non viene riclassificato: stessa richiesta, stessi byte.

Perché nel turno utente e non come messaggio `system`? I template chat di Qwen
rifiutano un messaggio di sistema che non sia il primo. Il blocco è delimitato
da intestazione e chiusura esplicite, e il testo dell'utente segue intatto.

### Il template di Qwen3.5 rompeva la cache tra un turno e l'altro

Il template originale rende le risposte del modello con il loro `<think>…</think>`
solo se vengono DOPO l'ultimo messaggio utente; quelle precedenti perdono il
blocco. Quindi a ogni nuovo messaggio utente tutte le risposte del turno prima
cambiano forma e la cache va buttata da lì in poi (misurato: 4179 token
rielaborati per "ora sposta il file in home"; succede anche col think spento,
perché il blocco vuoto `<think></think>` sparisce comunque).

`config/llama.cpp/qwen3.5-kv-stable.jinja` è il template del GGUF con una sola
modifica: ogni risposta tiene sempre il suo `<think>`. Misurato dopo la modifica:
al secondo turno 23 token nuovi, 186–215 dalla cache. Costo: i ragionamenti
restano nel contesto (si riempie un po' prima). L'agente `ai` rimanda il
`reasoning_content` nello storico apposta.

I test in `tests/test_router.py` verificano proprio questo (prefisso identico tra
turni, niente scaricamento, retry identico, nuova conversazione pulita).

## Il router

| Componente | File | Note |
|---|---|---|
| Registro | `addons/registry.toml`, `router/registry.py` | categorie, add-on, catalogo skill |
| Impostazioni | `config/router.toml` | backend, soglia, storico, budget token |
| Magika | `router/detect.py` | opzionale; un solo tipo per input |
| Intento | `router/intent.py` | `keywords` (default), `gliclass` (sperimentale), `tfidf` (sklearn, categoria only) |
| Decisione | `router/router.py` | categoria + add-on, budget, soglia |
| Iniezione | `router/compose.py` | stabilità del prefisso, sessioni |
| Proxy | `router/proxy.py` | streaming SSE, header `X-Router-*`, `/router/status` |

Regole della decisione:

- **L'ultimo messaggio decide.** Lo storico (ultimi `history_messages`) conta
  con peso `history_weight` (0,6), così un cambio di argomento vince su una
  parola chiave vecchia; se l'ultimo messaggio non ha nessun indizio ("e adesso?")
  lo storico conta pieno.

- **Magika** → add-on con quell'etichetta (es. `python`, `shell`) + punteggio alla sua categoria.
- **Categoria** = punteggio più alto, se ≥ `threshold`; altrimenti nessuna.
- **Add-on** della categoria scelta (o del gruppo `shared`) con punteggio ≥ soglia,
  più i `default_addons` della categoria.
- Già caricati in questa conversazione → esclusi. Oltre `max_addon_tokens` → saltati e loggati.
- Limite noto di Magika: un tipo per file. Il codice misto (Python con SQL)
  lo copre il classificatore di intento / le parole chiave.

### Backend di intento: stato misurato

Il 2026-11-20, su 8 prompt italiani (programmazione / sysadmin / altro):

| Modello GLiClass zero-shot | Corretti |
|---|---|
| `gliclass-edge-v3.0` | 1/8 |
| `gliclass-base-v3.0` | 5/8 |
| `gliclass-modern-base-v3.0` | 2/8 |

Nessuno riconosce "altro argomento" (un libro, il meteo → sysadmin a 0,6–0,9).
Per questo il default è `keywords`, prevedibile e senza dipendenze. La versione
finale prevista è un classificatore piccolo **addestrato su esempi italiani
reali** (mmBERT-small o SetFit), da confrontare con `./ai route-eval`.

## Add-on e skill

- **Add-on** (`addons/`): testi brevi e densi, pensati per essere iniettati.
- **Skill di OpenCode** (`.opencode/skills/`): le piccole (docker, arch-sysadmin,
  proxmox, ~350–600 token) sono anche add-on; le grandi (2.500–10.000 token) no,
  le carica OpenCode su richiesta col suo tool skill. Tutte sono raggruppate per
  categoria nel `[catalog]` del registro.

## Decisione: llama.cpp nativo, non Docker

Per l'**inferenza** Docker non porta benefici su questa macchina: nessuna GPU,
un solo binario, mmap diretto dei GGUF, controllo semplice di thread/memoria.
Docker resta **solo** per servizi ausiliari opzionali (Open WebUI, `profile gui`).

## Budget RAM (16 GB)

**Misurato il 2026-11-20**: con i default di llama-server (4 slot da 16K, cache dei
prompt fino a 8 GB) le sue allocazioni arrivavano a 8,1 GB e i pesi del modello
(mmap) venivano scaricati dalla RAM e riletti dal disco a ogni token: generazione
1,1 t/s. Con `--parallel 1 --cache-ram 1024` (default in `start.sh`, regolabili
con `LLAMA_PARALLEL` / `LLAMA_CACHE_RAM`): 3,5 GB allocati, pesi residenti,
**5,5 t/s**, 4,8 GB di RAM ancora disponibili con il browser aperto.

| Scenario | RAM usata (stima) |
|---|---|
| Idle (nessun modello) | ~4,5 GB |
| `base` Qwen3.5-9B Q4_K_M, ctx 16K | ~11–12 GB (da misurare) |
| `lite` Qwen3.5-4B Q4_K_M | ~8 GB |
| Router (keywords, stdlib) | ~20 MB; con Magika ~100 MB |

Il router con GLiClass carica PyTorch (~1 GB in più): un motivo in più per
tenerlo sperimentale.

## Sicurezza e accesso API

- `llama-server` è **sempre** su `127.0.0.1:8081`; l'unico punto d'ingresso è il router.
- Esposizione LAN: `ROUTER_HOST=0.0.0.0` in `.env`; con `LLAMA_API_KEY` il router
  inoltra l'header `Authorization` e la verifica la fa llama-server.
- Gli endpoint di debug `/router/*` rispondono solo da localhost.
- Nessun socket Docker ai container AI, nessun mount della root, nessun sudo automatico.

## Prossimi passi (da CLAUDE.md)

- Categorie e add-on definitivi + 5–10 richieste reali per categoria → dataset
  in `router/examples/` e classificatore addestrato.
- Ripiego: tool con cui il modello base chiede un add-on mancante.
- LoRA come add-on, solo se misurato necessario (cambiarle invalida la cache KV:
  solo a inizio sessione).
- Benchmark di Qwen3.5-9B vs 4B sulla CPU di destinazione.
