# Progetto: modello unico + router + add-on (IA locale su CPU)

## Obiettivo
Stack di IA locale **senza cambio di modello**: un solo modello base sempre caricato,
più add-on attivati da un router piccolo e veloce in base alla richiesta.
Motivo: cambiare modello costa tempo e, soprattutto, fa perdere il contesto
(cache KV) e obbliga a rielaborare tutta la conversazione su CPU.

Base di partenza: fork di https://github.com/dexRand/rottingAi-studio (licenza MIT).
Da riusare: script di avvio/arresto di `llama-server`, skill in `.opencode/skills/`.
Da cambiare: `config/llama.cpp/roles.conf` → un solo modello; skill riorganizzate per categoria.

## Hardware di riferimento
- PC Linux, max 16 GB di RAM, CPU di fascia media, nessuna GPU.
- Budget per il modello: circa 8–10 GB (il resto va a sistema e applicazioni).
- Sviluppo sul PC di Matteo: Debian 13, ~32 GB RAM, NVMe.

## Architettura
```
Utente ──> Router (classificatori, NON un LLM) ──> Modello base (sempre caricato)
                │                                         ▲
                └── sceglie categoria + add-on ───────────┘ (add-on aggiunti IN FONDO al contesto)
```
1. Il prompt dell'utente resta **intatto**.
2. Il router produce solo flag sì/no (classificazione multi-label, un solo passaggio):
   - **Magika** (Google, ~1 MB, ~5 ms su CPU): linguaggio del codice o del file allegato.
   - **Classificatore di intento**: categoria e add-on di compito.
     Prototipo: GLiClass zero-shot (`pip install gliclass`; addestrato in inglese, da verificare in italiano).
     Versione finale: mmBERT-small o SetFit addestrati sugli esempi italiani.
3. Gli add-on scelti vengono aggiunti in fondo al contesto, poi il prompt originale va al modello base.

## Regole sugli add-on
- Tipi, dal più economico al più costoso: system prompt/istruzioni → skill (testo) → tool → LoRA (solo se misurato necessario).
- Caricare **solo in fondo** al contesto, per non invalidare la cache KV.
- **Non scaricare** add-on né cambiare LoRA a metà conversazione: si puliscono solo a inizio sessione o nuovo compito.
- Soglia di confidenza: sotto soglia nessuna ipotesi; si attiva un set generale oppure si chiede all'utente.
- Ripiego: il modello base può richiedere un add-on mancante tramite tool.
- Il router deve vedere anche gli ultimi messaggi, non solo l'ultimo prompt.
- Gruppo di add-on condivisi tra categorie (es. git, docker, file).
- Limite noto di Magika: un solo tipo per file. Il codice misto (es. Python con SQL) va coperto
  dal classificatore di intento o da controlli su parole chiave.

## Modello base (da confermare con benchmark)
- Candidato principale: **Qwen3.5-9B** Q4_K_M (~6 GB), thinking spento di default.
- Alternativa più veloce: **Qwen3.5-4B** (~3 GB).
- Verificare con `llama-bench` / `./ai benchmark` sulla CPU di destinazione.
- Eventuale eccezione: modello specializzato (es. CTF) caricato solo nei casi rari.

## Dati ancora mancanti (chiedere a Matteo, non inventare)
- Elenco definitivo di categorie e add-on.
- 5–10 richieste di esempio reali per ogni categoria.
- Modello esatto della CPU di destinazione; risposte in italiano sì/no.
- Se il progetto è per Mingo (IA locale per lavoratori non esperti) o per uso personale.
- "ponytail": skill o strumento citato da Matteo, sconosciuto; chiedere il link.

## Primo passo proposto
Prototipo del router in Python: Magika + GLiClass, che riceve un testo (+ file
opzionale) e stampa categoria e add-on con i punteggi. Test su esempi reali
prima di collegarlo a `llama-server`.

## Stato (2026-11-20)
Fatto:
- `roles.conf` → un modello: `base` (Qwen3.5-9B, thinking off), alternative `lite` (4B) e `ctf` (eccezione).
- Categorie `coding` e `sysadmin` + gruppo `shared`; add-on in `addons/` (registro: `addons/registry.toml`):
  `python`, `linux-commands`, più le skill piccole `arch-sysadmin`, `proxmox`, `docker`.
  Le skill grandi restano a OpenCode, catalogate per categoria nel `[catalog]` del registro.
- Router in `router/` (solo libreria standard; Magika opzionale): `./ai route "testo" --show`.
- Proxy OpenAI-compatibile su :8080 davanti a `llama-server` (interno su :8081): aggiunge gli add-on
  nel turno utente corrente, prima del prompt intatto, e li reinserisce identici nei turni successivi
  (cache KV valida). Coperto da `tests/test_router.py`.
- `./ai route-eval` misura l'accuratezza su `router/examples/*.jsonl`.

Misurato: GLiClass zero-shot NON funziona in italiano (edge 1/8, base 5/8, modern-base 2/8 su 8 prompt;
"altro argomento" mai riconosciuto). Default quindi = backend `keywords`; GLiClass resta sperimentale.
`router/examples/smoke.jsonl` l'ho scritto io: NON sono esempi reali e il 100% delle keyword su quel
file non dimostra nulla.

Aggiunto dopo la prova dal vivo (Qwen3.5-9B su Core Ultra 7 255U: prefill ~21 t/s, generazione ~4,5 t/s):
- Agente da terminale `ai` (`agent/`, symlink `~/.local/bin/ai`): chat stile Claude Code nella cartella
  corrente, strumenti run_command/read_file/write_file/edit_file con approvazione, think visibile.
  Prova: ha corretto i 3 bug di un file di test (facile/medio/difficile) e li ha verificati eseguendolo.
- Il template Qwen3.5 originale buttava la cache a ogni nuovo messaggio utente (toglie i <think> dei turni
  precedenti): sostituito con `config/llama.cpp/qwen3.5-kv-stable.jinja`. Vedi docs/architecture.md.
- llama-server: `--parallel 1 --cache-ram 1024`. I default (4 slot, cache prompt 8 GB) occupavano 8 GB e
  facevano rileggere i pesi dal disco: 1,1 -> 5,5 t/s in generazione.
- Agente: `write_file` rifiutato sui file esistenti (salvo "riscrivi"): ora corregge con 3 edit_file mirati;
  `ai -a` = auto mode; `ai` apre una nuova finestra di terminale (kitty), `--here` resta nella shell.
- Router: l'ultimo messaggio decide, lo storico pesa 0,6 (prima "sposta il file in home" dopo un messaggio
  su un .py restava su coding); aggiunte parole chiave sysadmin per le operazioni sui file.

Da fare:
- Esempi reali per categoria → classificatore addestrato (mmBERT-small / SetFit) come nuovo backend.
- Tool di ripiego per chiedere un add-on mancante; LoRA solo se misurato necessario.
- Benchmark di Qwen3.5-9B vs 4B sulla CPU di destinazione; prova end-to-end con il modello vero.
