# services/web-search — ricerca web (SPEC)

MCP server di ricerca web, attivo **solo su richiesta esplicita** dell'utente.
**Non implementato in questa fase.**

## Decisione

| Aspetto | Scelta | Motivo |
|---|---|---|
| Motore | **SearXNG self-hosted** (container opzionale, `profile web-search`) | nessuna API key né account, nessun provider unico che registra le query; coerente con "offline after first download". **Onesto:** SearXNG è un metasearch e inoltra la query ai motori upstream (Google/Bing/DuckDuckGo…), quindi il servizio è **online-only e opt-in**. Alternative scartate: **Tavily** (cloud + API key, già usata dalla skill `ctf-similar-search`) e **DuckDuckGo** (senza key ma rate-limited e vincoli TOS). |
| Accesso del modello | **tool MCP `web_search`**, come il server `stegsuite` in `config/opencode/opencode.jsonc` (`type: "remote"`, `url`, `oauth: false`, `codemode: false`) | il modello lo chiama solo quando la richiesta implica il web; i top-N entrano nel turno corrente, non in un contesto sempre attivo. Mai automatico. |
| Rete | timeout di esecuzione **~5 s** (stesso spirito dei 3 s di startup di StegSuite); **cache TTL in memoria** per non ripetere query identiche; si rispettano i rate limit della JSON API di SearXNG | niente attese lunghe su CPU; meno traffico verso SearXNG. **Senza rete** o motore irraggiungibile: errore chiaro, il modello risponde con la propria conoscenza e dichiara che la ricerca non è disponibile — **mai inventare risultati**. |
| Privacy | **opt-in stretto**: servizio spento di default (`profile web-search` non avviato), il tool non viene mai chiamato da solo; esce dalla macchina **solo la query derivata**, mai conversazione o cronologia; **nessun log** di query o conversazioni, nessuna esfiltrazione | l'utente decide quando e cosa cercare. |

## Come funziona (schema)

```
richiesta utente ──> il modello decide di cercare
                          │  web_search(query)   ← tool MCP, come `stegsuite`
                          ▼
                     SearXNG (profile web-search, localhost)
                          │  JSON API (timeout ~5 s, cache TTL)
                          ▼
         top-N risultati (titolo + URL + snippet) → testo nel turno corrente
```

Contratto del tool:

| Campo | Valore |
|---|---|
| nome | `web_search` |
| input | `query` (stringa) |
| output | top-N risultati: `titolo`, `url`, `snippet` |
| effetti | **sola lettura**: nessuna scrittura, nessun comando |
| rete | **richiesta**; senza rete il tool fallisce con un errore chiaro |

Nessuna indicizzazione: SearXNG interroga i motori al momento della chiamata.

## Non in v1

- Niente scraping proprio né crawler: solo l'API di SearXNG.
- Niente risultati sempre attivi (nessun contesto web precaricato).
- Niente indicizzazione locale né archivio delle ricerche.
- Niente ricerca senza richiesta esplicita: il tool non è mai chiamato in automatico.
- Niente multi-tenant né auth: servizio solo su localhost, uso personale.

## Criterio di fatto

1. Si avvia SearXNG con `profile web-search` e si configura il server MCP.
2. Si chiede qualcosa che richiede il web (es. una notizia o una versione recente).
3. Il modello chiama `web_search` e risponde citando le fonti (titolo + URL).
4. Senza rete risponde con la propria conoscenza e segnala che la ricerca non è disponibile.

**Stato:** SPEC, non implementato in questa fase.
