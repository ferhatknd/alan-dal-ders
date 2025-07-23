# Turkish BERT Text Correction Setup Guide

## Prerequisites

Install the required Python packages:
```bash
pip install -r requirements.txt
```

## First-time Setup

Run the setup script to download NLTK data:
```bash
python setup_bert_dependencies.py
```

## Model Download (Optional)

The Turkish BERT model will be downloaded automatically on first use.
This may take several minutes and requires an internet connection.

Model used: `dbmdz/bert-base-turkish-cased`

## Hardware Optimization

- **Apple Silicon Macs**: Automatically uses MPS (Metal Performance Shaders) for GPU acceleration
- **NVIDIA GPUs**: Automatically uses CUDA if available
- **CPU Only**: Falls back to CPU processing

## Usage

The text correction is automatically integrated into `extract_olcme.py`.
When processing PDFs, the system will:

1. Apply Turkish character normalization
2. Use BERT for context-aware correction (if available)
3. Apply fuzzy matching for validation
4. Apply rule-based post-processing

## Performance Notes

- First run: Slower due to model download and initialization
- Subsequent runs: Faster due to model caching
- Processing time: < 300ms per sentence (after initialization)
- Memory usage: < 1GB

## Fallback Behavior

If BERT model is not available:
- System falls back to rule-based correction
- Still provides basic punctuation and spacing fixes
- No error is thrown, processing continues normally

## Testing

Run the integration test:
```bash
python test_bert_integration.py
```
