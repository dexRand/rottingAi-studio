# Scelta dei modelli

Criterio: 16 GB RAM, CPU-only AVX2, reattività del desktop prioritaria,
tool calling nativo, italiano, licenze permissive.

## Vincitori

1. **Coding — Qwen2.5-Coder-7B-Instruct** (Apache 2.0). Specialista coding
   (Bash, Python, C/C++, JS/TS, YAML, Docker), FIM, tool calling nativo.
   È il backend raccomandato per OpenCode.
2. **General / Italiano — Qwen3-8B** (Apache 2.0). Miglior piccolo generalista
   2026: 100+ lingue (italiano ottimo), ragionamento ibrido, tool calling tra i
   migliori della categoria.
3. **Sysadmin — Qwen2.5-7B-Instruct Q5_K_M** (Apache 2.0). Tecnico e reattivo
   (~6-7 t/s). Scelto come default dopo che il 12B è risultato troppo lento su
   questa CPU (~2,3 t/s misurati).
   - Opzionale "pesante": **Gemma 3 12B** (contesto 128K per log lunghi), se la
     profondità conta più della velocità.

## Perché NON altri runtime/modelli

- **Unsloth Studio**: GUI desktop + training; su CPU non dà vantaggi (il motore
  è comunque llama.cpp). Scartato come runtime. I suoi GGUF dinamici restano
  opzionali.
- **vLLM**: orientato GPU, inefficace su CPU.
- **LM Studio / KoboldCpp**: GUI/web non richieste, overhead non necessario.
- **Ollama**: comodo ma daemon persistente → contro il requisito "zero servizi
  a riposo".
- Modelli >12B (Qwen3-Coder 30B-A3B, Qwen3.8-27B, ecc.): non stanno in RAM
  senza swap massiccio.

## Stime di velocità (da verificare con benchmark reale)

Banda DDR4-2400 dual-channel ≈ 27-30 GB/s effettivi. Limite teorico
memory-bound: 7B-Q4 ≈ 5-7 t/s, 8B-Q4 ≈ 5-6 t/s, 12B-Q4 ≈ 3-4 t/s.
Il *prompt processing* (prefill) su contesti grandi è la parte lenta in
scenari agentici: aspettarsi decine di secondi prima del primo token su
contesti di 2-4k token.
