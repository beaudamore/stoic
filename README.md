# Stoic Persona LoRA — Multi-Voice Philosophy Fine-Tuning

Three Stoic voices — **Seneca**, **Epictetus**, and **Marcus Aurelius** — trained into one
LoRA adapter so the model switches voice on the system prompt. Built from public-domain
translations, generated into persona-conditioned Q&A plus raw-text continuation data, then
trained in two stages (SFT, then DPO) with Unsloth QLoRA on an NVIDIA DGX Spark.

Sister project of the [biblical persona LoRA](https://github.com/beaudamore/biblical): same
pipeline, same quality gates, same three DPO rejection strategies. The adapters plug into the
[Circle of Speakers](https://github.com/beaudamore/circle-of-speakers-pipeline) multi-speaker
Open WebUI pipeline, which ships a `stoic_circle.py` for exactly this cast.

---

## What it demonstrates

| Area | Specifics |
| --- | --- |
| **Fine-tuning / PEFT** | Two-stage QLoRA (4-bit NF4): TRL `SFTTrainer` then `DPOTrainer` continuing the same adapter. r=32 / α=32 on all seven attention and MLP projections, 4096-token sequences, `adamw_8bit`, auto-resume from `checkpoint-*`. |
| **Synthetic data generation** | Persona-conditioned Q&A from sentence-aware 1,500-character chunks, 5 questions × 3 question angles per chunk, generated with Qwen3-235B via OpenRouter. Voice-differentiation quality gate before assembly. 60/40 blend of Q&A and raw-text continuation. |
| **Preference data** | DPO pairs built from the SFT set across three engineered failure modes: `voice_drift`, `source_fabrication`, `shallow_platitude`. Per-persona cap so Seneca's volume does not drown the others. |
| **Data engineering** | Idempotent per-author cleaner (`data/scripts/clean_source_data.py`), corpus audit with a costed roadmap, a persona-removal script that quarantines data rather than deleting it. |
| **Durability** | Streaming JSONL during generation, persistent DPO reference-logprob cache, `get_last_checkpoint` resume, cold-reload adapter verification, GGUF export cell. |

---

## Headline numbers

| Item | Value |
| --- | --- |
| **Personas** | 3 (Seneca, Epictetus, Marcus Aurelius) |
| **Source corpus** | 15 public-domain works (Project Gutenberg), see below |
| **Per-persona Q&A generated** | Seneca 39,538 · Epictetus 9,768 · Marcus Aurelius 7,614 rows |
| **SFT set (post-blend)** | 25,121 ShareGPT conversations: 15,067 Q&A + 10,054 continuation |
| **DPO set** | 1,791 preference pairs: 597 per rejection strategy |
| **Generator model** | `qwen/qwen3-235b-a22b-2507` (OpenRouter) for questions, answers and rejected answers |
| **Base model (shipped)** | `unsloth/Qwen3-14B-unsloth-bnb-4bit` |
| **Adapter shape** | LoRA r=32 / α=32, all attention + MLP projections, 490 MB fp32 |
| **Training hardware** | NVIDIA DGX Spark (GB10, 128 GB unified memory) |

---

## Shipped adapters

Both adapters live under `output/` (gitignored, generated locally). Values below are read from
`trainer_state.json` and `adapter_config.json`, not from the notebooks.

| Adapter | Date | Stage | Steps | Loss (first → last) | Notes |
| --- | --- | --- | --- | --- | --- |
| `stoic_qwen3_14b_sft_unsloth_bnb_4bit` | 2026-05-22 | SFT, 1 epoch | 116 | 2.70 → 1.47 | LR 2e-4, batch 2 × grad-accum 4, seq 4096 |
| `stoic_qwen3_14b_dpo_unsloth_bnb_4bit` | 2026-05-23 | DPO, 1 epoch | 225 | — | Continues the SFT adapter; single combined adapter for serving |

Both carry `persona_system_prompts.json` so the serving layer can load the exact prompts the
data was built with.

**Epicurus caveat.** These May adapters were trained when the dataset still included a fourth
voice, Epicurus. He was removed on 2026-08-24 (he is not a Stoic; see the roadmap) and his data
quarantined under `data/training-data/stoic_persona/_removed_epicurus_*/`. The current dataset
is three voices; the next training run will be too.

---

## Source corpus

| Author | Works in `data/source-raw/` |
| --- | --- |
| Seneca | *Moral Essays* (Minor Dialogues, On Clemency), *On Benefits*, *Morals of a Happy Life*, *Natural Questions* (Physical Science in the Time of Nero), *Apocolocyntosis*, the tragedies (*Medea*, *The Daughters of Troy*, *Octavia*, collected tragedies), *Between Heathenism and Christianity* |
| Epictetus | *The Discourses*, *The Enchiridion*, *The Golden Sayings* |
| Marcus Aurelius | *Meditations* (two translations) |
| Machiavelli | Seven works present in `source-raw/` but **excluded** from the dataset by design (roadmap §3) |
| Epicurus | *Letter to Menoeceus*, *Principal Doctrines* — **removed** 2026-08-24 |

Seneca is roughly 70% of the training data, and his most voice-defining work, the *Epistulae
Morales* (Letters to Lucilius), is **not** in the corpus. That is the first item on the
[augmentation roadmap](docs/augmentation-roadmap.md).

---

## Repo layout

```text
stoic/
├── README.md
├── docs/
│   ├── data-pipeline.md             Cleaner and datagen flow
│   └── augmentation-roadmap.md      2026-08-24 corpus audit: Seneca letters, Epicurus removal,
│                                    Machiavelli exclusion, Musonius Rufus as the next speaker
├── prompts/epictetus.md             Hand-written persona brief (notebook is source of truth)
├── data/                            (gitignored: regenerated locally)
│   ├── scripts/clean_source_data.py Idempotent per-author cleaner: source-raw -> source-clean
│   ├── scripts/remove_persona.py    Quarantines one persona's data with a manifest
│   ├── source-raw/<Author>/*.txt    Untouched Gutenberg originals
│   ├── source-clean/<Author>/*.txt  Headers, footers and boilerplate stripped
│   └── training-data/stoic_persona/
│       ├── per_persona/<persona>.jsonl           Pre-blend Q&A per voice
│       ├── augmented/continuation/*.jsonl        Raw-text completion tasks
│       ├── stoic_personas_sharegpt.jsonl         Q&A only
│       ├── stoic_personas_combined_sharegpt.jsonl  Final SFT mix (Q&A + continuation)
│       ├── stoic_dpo_pairs_raw.jsonl             Pre-gate DPO pairs
│       └── stoic_personas_dpo.jsonl              Final DPO pairs
├── notebooks/
│   ├── datagen/
│   │   ├── stoic_datagen_sft.ipynb               Q&A + continuation pipeline
│   │   └── stoic_datagen_dpo.ipynb               Three-strategy preference pairs
│   └── loras/
│       ├── qwen3-14b/  stoic_qwen3_14b_{sft,dpo}.ipynb      Produced the shipped adapters
│       ├── qwen3.8/    stoic_qwen38_27b_{sft,dpo}.ipynb     Current reference notebooks (see below)
│       ├── qwen35/     stoic_qwen35_9b_{sft,dpo}_unsloth_4bit.ipynb   Draft, not run
│       ├── qwen3.6/    stoic_qwen36_27b_{sft,dpo}.ipynb     Draft, not run
│       └── *.ipynb     Earlier experiments: Llama 3.1 8B/70B, Mistral 7B, Qwen2.5 14B,
│                       Gemma 3 12B, Augmentoolkit variants. Kept for reference.
└── output/<model_name>/{train,lora_adapters,gguf}/   (gitignored)
```

The `qwen3.8/` SFT notebook is the workspace's reference for VLM-safe LoRA scoping on a
multimodal base (vision and audio towers frozen explicitly, with an assertion that no adapter
leaked outside the language model). It has not yet produced a Stoic adapter. The `qwen3.6/`
pair was copied from the 9B notebooks and still carries the 9B base and output name; it needs
its configuration cell fixed before it is run.

---

## Running it

Notebooks run in JupyterLab inside the `unsloth-notebook` container (host port 8889), not on
the host. Paths in the notebooks resolve both ways.

```bash
# 1. Clean the corpus (host, seconds, no GPU). Wipes and rebuilds data/source-clean/.
python data/scripts/clean_source_data.py

# 2. Datagen. Needs OPENROUTER_API_KEY in the environment or a .env file.
#    notebooks/datagen/stoic_datagen_sft.ipynb   -> stoic_personas_combined_sharegpt.jsonl
#    notebooks/datagen/stoic_datagen_dpo.ipynb   -> stoic_personas_dpo.jsonl

# 3. Train. Check the GPU is free first: a serving container usually holds it.
docker ps                                       # stop any vllm-* / sglang-* first
#    notebooks/loras/qwen3-14b/stoic_qwen3_14b_sft.ipynb   then   ..._dpo.ipynb

# 4. Audit the adapter for module-scope leakage before shipping it
docker exec unsloth-notebook python /workspace/training/docs/audit_adapters.py stoic
```

`MODEL_NAME_BASE` in the SFT notebook is the contract with the DPO notebook, which resolves
the SFT adapter path from it. Change it in both places or not at all.

---

## Pipeline at a glance

```text
data/source-raw/<Author>/*.txt
  -> clean_source_data.py                     per-author boilerplate removal
  -> stoic_datagen_sft.ipynb                  sentence-aware chunks (1,500 chars)
       -> 3 rounds x 5 questions per chunk    Qwen3-235B via OpenRouter
       -> voice-differentiation quality gate  fails closed on template contamination
       -> per_persona/*.jsonl
       -> continuation chunks                 no API calls
       -> 60/40 blend                         stoic_personas_combined_sharegpt.jsonl
  -> stoic_datagen_dpo.ipynb                  voice_drift | source_fabrication | shallow_platitude
       -> stoic_personas_dpo.jsonl
  -> stoic_qwen3_14b_sft.ipynb                QLoRA r=32, 1 epoch
  -> stoic_qwen3_14b_dpo.ipynb                continues the same adapter
  -> output/<model>/lora_adapters/            served by vLLM with --enable-lora
```

---

## Status

- Pipeline is functional end to end on Qwen3-14B: cleaning → datagen → SFT → DPO → adapter.
- The dataset was regenerated with sentence-boundary chunking (2026-07-01) and had Epicurus
  removed (2026-08-24) after the shipped adapters were trained; a fresh Qwen3.8-27B run on the
  current three-voice set is the next training step.
- Highest-value data work, in order: add Seneca's *Epistulae Morales*, then Musonius Rufus as a
  fourth Stoic voice. Both need a datagen regeneration (API spend). Details and evidence in
  [docs/augmentation-roadmap.md](docs/augmentation-roadmap.md).

## Related

- [biblical](https://github.com/beaudamore/biblical) — the 26-voice sister project this pipeline was derived from
- [circle-of-speakers-pipeline](https://github.com/beaudamore/circle-of-speakers-pipeline) — the Open WebUI runtime that turns these adapters into a multi-speaker conversation
- [damore.ai/blog](https://www.damore.ai/blog) — writeups on the persona-LoRA approach
