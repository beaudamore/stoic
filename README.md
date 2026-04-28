# Stoic Philosophy Model Training on NVIDIA DGX

Complete pipeline for fine-tuning Mistral-7B on Stoic philosophy texts, optimized for NVIDIA GB10 (119.7 GB VRAM).

## 🚀 Quick Start

### 1. Activate Virtual Environment
```bash
cd ~/projects/stoic
source venv/bin/activate
```

### 2. Ensure Google Drive is Mounted
```bash
# Check if mounted
ls ~/gdrive/"Colab Notebooks"/stoic/

# If not mounted, run:
rclone mount gdrive: ~/gdrive --vfs-cache-mode writes --daemon
```

### 3. Open Notebook
```bash
# In VS Code, open:
# ~/gdrive/Colab Notebooks/stoic/stoic_mistral_unsloth_colab.ipynb
```

### 4. Run Training Pipeline
Execute cells in order:
- **Cells 1-4**: Setup and GPU verification
- **Cell 5**: Load training data
- **Cells 6-8**: Load model and prepare dataset
- **Cells 9-10**: Train with auto-checkpointing
- **Cell 11b**: Merge LoRA adapters
- **Cell 12**: Convert to GGUF

## 📁 Directory Structure

```
~/projects/stoic/
├── venv/                          # Virtual environment
├── cache/                         # Fast local model cache
├── llama.cpp/                     # GGUF conversion tools
└── train_stoic.sh                 # Quick launcher

~/gdrive/Colab Notebooks/stoic/
├── mlx_format/
│   └── train.jsonl               # Training data
├── checkpoints/                   # Training checkpoints (auto-resume)
├── models_trained/                # Final LoRA adapters
├── models_merged/                 # Merged full model
└── gguf/                         # GGUF files for Ollama
    ├── stoic-mistral-q4_k_m.gguf  # Recommended (3.5GB)
    ├── stoic-mistral-q5_k_m.gguf  # Better quality (4.3GB)
    └── stoic-mistral-q8_0.gguf    # Best quality (7GB)
```

## 🛡️ Bulletproof Features

### Automatic Checkpoint Resumption
- Saves checkpoints every 100 training steps
- If training is interrupted, just re-run Cell 10
- Automatically resumes from the last checkpoint
- Keeps last 5 checkpoints for safety

### Completion Markers
Each stage creates a marker file when complete:
- `TRAINING_COMPLETE.txt` - Training finished
- `MERGE_COMPLETE.txt` - Merge finished
- `CONVERSION_COMPLETE.txt` - GGUF conversion finished

### Google Drive Sync
All outputs automatically save to Google Drive for backup.

## 🎯 Performance on GB10

- **Training Time**: ~30-45 minutes
- **Batch Size**: 16 (optimized for 119GB VRAM)
- **Precision**: bf16 (full precision, no quantization!)
- **Total Pipeline**: ~1 hour (train + merge + GGUF)

## 🔧 Common Operations

### Check Training Status
```bash
# List checkpoints
ls -lh ~/gdrive/"Colab Notebooks"/stoic/checkpoints/

# Check if training completed
cat ~/gdrive/"Colab Notebooks"/stoic/models_trained/stoic-mistral-7b-lora/TRAINING_COMPLETE.txt
```

### Resume Interrupted Training
```python
# Just re-run Cell 10 in the notebook
# It will automatically detect and resume from the last checkpoint
```

### Start Fresh Training
```bash
# Remove existing checkpoints
rm -rf ~/gdrive/"Colab Notebooks"/stoic/checkpoints/*

# Then re-run Cell 10
```

### Re-convert to GGUF
```bash
# Remove completion marker
rm ~/gdrive/"Colab Notebooks"/stoic/gguf/CONVERSION_COMPLETE.txt

# Then re-run Cell 12
```

## 🎨 Using the Trained Model

### Import to Ollama
```bash
cd ~/gdrive/"Colab Notebooks"/stoic/gguf

ollama create stoic -f <(echo 'FROM "./stoic-mistral-q4_k_m.gguf"
TEMPLATE """[INST] {{ .Prompt }} [/INST]"""
PARAMETER temperature 0.7
PARAMETER top_p 0.9')
```

### Test the Model
```bash
ollama run stoic "What did Marcus Aurelius teach about virtue?"
ollama run stoic "Explain Epictetus's view on what is within our control"
ollama run stoic "How do the Stoics define living well?"
```

## 📊 Output Files

### LoRA Adapters (~100MB)
```
~/gdrive/Colab Notebooks/stoic/models_trained/stoic-mistral-7b-lora/
├── adapter_config.json
├── adapter_model.safetensors
└── tokenizer files
```

### Merged Model (~14GB)
```
~/gdrive/Colab Notebooks/stoic/models_merged/stoic-mistral-merged-f16/
├── model-00001-of-00003.safetensors
├── model-00002-of-00003.safetensors
├── model-00003-of-00003.safetensors
├── config.json
└── tokenizer files
```

### GGUF Files
```
~/gdrive/Colab Notebooks/stoic/gguf/
├── stoic-mistral-f16.gguf      (14GB - source)
├── stoic-mistral-q4_k_m.gguf   (3.5GB - recommended)
├── stoic-mistral-q5_k_m.gguf   (4.3GB - better quality)
└── stoic-mistral-q8_0.gguf     (7GB - best quality)
```

## 🆘 Troubleshooting

### GPU Not Detected
```bash
# Check CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# If False, ensure PyTorch CUDA is installed:
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130
```

### Drive Not Mounted
```bash
# Check mount
ls ~/gdrive

# Remount
rclone mount gdrive: ~/gdrive --vfs-cache-mode writes --daemon
```

### Out of Memory
The code auto-detects GPU VRAM and adjusts batch sizes. But if you hit OOM:
- GB10 (119GB): Should never OOM with batch_size=16
- If it does, reduce batch size in Cell 9

### Dependencies Missing
```bash
source ~/projects/stoic/venv/bin/activate
pip install -r requirements.txt  # If you create one
# Or re-run Cell 3 in the notebook
```

## 📝 Notes

- **Virtual Environment**: Always activate before running the notebook
- **Checkpoints**: Saved to Google Drive, can take a moment to sync
- **GGUF Conversion**: Builds llama.cpp locally with CUDA support for fast conversion
- **Recommended GGUF**: q4_k_m for best speed/quality balance

## 🎯 Optimizations Applied

1. **Full Precision**: No 4-bit quantization needed with 119GB VRAM
2. **Large Batches**: batch_size=16 for faster training
3. **Local Cache**: Models cached locally for fast loading
4. **CUDA GGUF**: llama.cpp built with CUDA for fast conversion
5. **Auto-Resume**: Never lose training progress
6. **Multi-Format**: Creates q4, q5, q8 GGUF variants automatically
