# Stoic Data Pipeline

This project now follows the same broad layout as the Biblical training repo:

```text
stoic/
├── data/
│   ├── source-raw/                 Untouched originals
│   ├── source-clean/               Rebuilt by the cleaner
│   ├── scripts/clean_source_data.py
│   └── training-data/stoic_persona/
├── notebooks/
│   ├── datagen/                    Dataset generation notebooks
│   └── loras/                      Training notebooks
├── prompts/                        Persona prompt seeds
└── output/                         Generated run artifacts
```

Run the cleaner from the repo root:

```sh
python data/scripts/clean_source_data.py
```

The cleaner is idempotent: it deletes and rebuilds `data/source-clean/` from `data/source-raw/` while preserving the author/title directory structure.

The starter SFT notebook writes ShareGPT-style JSONL files to `data/training-data/stoic_persona/`. The starter DPO notebook reads that SFT data and emits simple preference pairs that can later be replaced with model-generated rejected answers.