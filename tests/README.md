# tests

## Unit test (nessun modello necessario)

```bash
python3 -m unittest discover -s tests -v
```

`test_router.py` copre registro, decisioni del router, e soprattutto le regole
del composer sulla cache KV: prefisso identico tra turni, add-on mai scaricati,
retry identico, nuova conversazione pulita, contenuti multi-part, e il proxy
(inoltro, header `X-Router-*`, pass-through degli altri endpoint) contro un
finto llama-server.

## Test con modelli reali

```bash
./ai test                 # skill + config + registro + smoke test per ruolo
./ai test --skills-only   # solo controlli statici
./ai route-eval -v        # accuratezza del router su router/examples/smoke.jsonl
```

`./ai test` avvia llama-server su una porta privata (8091) e manda un prompt
anche attraverso il router: non tocca uno stack già avviato. Usa lo stesso
`--chat-template-file` di `./ai start` e verifica il **tool calling**: un
modello che non emette `tool_calls` è un FAIL (l'agente `ai` e gli MCP server
non funzionerebbero).
