# Scelta dei modelli

Criterio: 16 GB RAM (budget modello ~8–10 GB), CPU-only AVX2, **un solo modello
sempre caricato**, tool calling nativo, italiano, licenze permissive.

## Modello base

**Qwen3.5-9B Q4_K_M** (Apache 2.0, GGUF Unsloth, 5,68 GB) — candidato principale.

- Generalista recente con tool calling nativo e buon italiano: deve coprire
  coding, sysadmin e chat insieme, con la specializzazione data dagli add-on.
- **Thinking spento** di default (`BASE_REASONING="off"` in `roles.conf`): su CPU
  i token di ragionamento costano troppo per l'uso quotidiano.
- Da **confermare con benchmark** sulla CPU di destinazione:
  `./ai benchmark base "4 6 8"`.

## Alternative (al posto di `base`, mai insieme)

- **`lite` — Qwen3.5-4B Q4_K_M** (2,74 GB): stessa famiglia, ~2× più veloce.
  Per macchine più deboli o se il 9B risulta troppo lento.
- **`ctf` — WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B Q4_K_M** (4,68 GB): l'unica
  eccezione al modello unico. Fine-tune di sicurezza per CTF/pentesting
  autorizzato, avviato esplicitamente (`./ai start ctf`) nei casi rari.

## Modelli rimossi nel passaggio al modello unico

Prima c'erano sei ruoli con cambio di modello (`coder` Qwen2.5-Coder-7B,
`general` Qwen3-8B, `fast` Qwen3.5-4B, `sysadmin` Qwen2.5-7B, `sysadmin-heavy`
Gemma 3 12B, `ctf`). La specializzazione per compito ora la danno gli add-on;
`fast` è diventato `lite`, `ctf` è rimasto come eccezione.

## Perché NON altri runtime

- **vLLM**: orientato GPU, inefficace su CPU.
- **Ollama**: daemon persistente e gestione del contesto meno controllabile.
- **LM Studio / KoboldCpp**: GUI non richieste.
- **Unsloth Studio**: su CPU il motore è comunque llama.cpp; i suoi GGUF dinamici
  (UD-*) restano un'opzione (qualità per bit, non velocità).
- Modelli > 12B: non stanno nel budget RAM senza swap massiccio.

## Stime di velocità (da verificare con benchmark reale)

Generazione memory-bound: t/s ≈ banda RAM effettiva / dimensione del modello.
Con DDR4 dual-channel (~27–30 GB/s): 9B-Q4 ≈ 4–5 t/s, 4B-Q4 ≈ 9–11 t/s. Con
DDR5/LPDDR5 (es. Core Ultra) circa il doppio.
Il prefill su contesti grandi resta la parte lenta: proprio per questo il
router non deve mai invalidare la cache KV.
