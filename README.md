<div align="center">

# 🌊 WRM-CLI

### Water Resources Modeling CLI

**Run EPA SWMM & EPANET simulations in the cloud**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![API Docs](https://img.shields.io/badge/API-docs.wrm.neer.io-orange.svg)](https://docs.wrm.neer.io/)

[Getting Started](#-quick-start) •
[Documentation](#-documentation) •
[Example Files](#-example-files) •
[API Reference](#-api-reference)

</div>

---

## 🎯 Overview

WRM-CLI is a command-line tool for running water resources simulations via the [NEER Water Resources Modeling API](https://docs.wrm.neer.io/). Run SWMM and EPANET models in the cloud without installing simulation engines locally.

### Features

- 🚀 **Cloud Simulation** - Run SWMM 5.2 and EPANET 2.3 in the cloud
- 📦 **Auto-packaging** - Automatically bundle auxiliary files (rainfall, temperature data)
- ⏳ **Real-time Tracking** - Monitor simulation progress with live log updates
- 📁 **Result Download** - Easily retrieve output files, reports, and logs
- 🔐 **Secure** - API key authentication with support for environment variables

### Supported Simulation Types

| Type | Description | Version |
|------|-------------|---------|
| `swmm` | EPA Storm Water Management Model | 5.2.4 |
| `epanet` | EPA Water Distribution Network Model | 2.3.3 |
| `hec_ras` | HEC-RAS River Analysis | Coming Soon |

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/neeraip/wrm-cli.git
cd wrm-cli

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Get your API key from:
- **Personal**: https://aip.neer.ai/user/keys
- **Team**: https://aip.neer.ai/teams/?tab=keys

```bash
# Option 1: Create .env file (recommended)
cp env.example .env
# Edit .env and add your token

# Option 2: Set environment variable
export WRAPI_TOKEN="your-api-token-here"

# Option 3: Use config command
python wrapi.py config --token "your-api-token-here"
```

### 3. Run Your First Simulation

```bash
# Run a SWMM model and wait for results
python wrapi.py run "EPASWMM Example Files/EPA/Example1.inp" --type swmm --wait

# Run an EPANET model
python wrapi.py run "EPANET Example Files/epanet-desktop/Net1/Net1.inp" --type epanet --wait
```

---

## 📖 Documentation

### Running Simulations

```bash
# Basic run (local file)
python wrapi.py run model.inp --type swmm --label "My Model"

# Run from URL
python wrapi.py run https://example.com/model.inp --type swmm

# Run with auxiliary files (rainfall, temperature data)
python wrapi.py run model.inp --type swmm --aux rainfall.dat temperature.dat

# Wait for completion (polls logs every 15 seconds)
python wrapi.py run model.inp --type swmm --wait --timeout 600
```

### Checking Status & Results

```bash
# Check simulation status
python wrapi.py status <simulation-id>

# View simulation logs
python wrapi.py logs <simulation-id>

# Get result files
python wrapi.py files <simulation-id>

# Download results to local directory
python wrapi.py files <simulation-id> --download ./results

# List recent simulations
python wrapi.py list --type swmm --limit 20
```

### ⚠️ Important: Auxiliary Files

If your model references external data files (rainfall, temperature, etc.), you **must** include them:

```bash
# Package model with auxiliary files
python wrapi.py run model.inp --type swmm --aux rainfall.dat temperature.dat
```

The tool automatically creates a ZIP file containing all files. Make sure your `.inp` file uses **relative paths** (just the filename).

```ini
# ✅ Correct - relative path
[RAINGAGES]
RG1  VOLUME  0:15  1.0  FILE  "rainfall.dat"  RG1  IN

# ❌ Wrong - absolute path won't work in cloud
[RAINGAGES]
RG1  VOLUME  0:15  1.0  FILE  "C:\Data\rainfall.dat"  RG1  IN
```

---

## 📂 Example Files

This repository includes validated and tested example files ready to run:

### EPANET Examples (182 files)

```
EPANET Example Files/
├── asce-tf-wdst/          # ASCE Task Force benchmarks (30 files)
├── collect-epanet-inp/    # Community contributed models (107 files)
├── epanet-desktop/        # Official EPANET examples (2 files)
├── epanet-example-networks/  # EPANET test suite (42 files)
└── L-Town/                # L-Town benchmark network (1 file)
```

### SWMM Examples (813 files)

All files have been validated and tested via API simulations. Source: [SWMMEnablement/1729-SWMM5-Models](https://github.com/SWMMEnablement/1729-SWMM5-Models) repository (~1300 files initially validated, 813 verified working).

```
EPASWMM Example Files/
├── SWMM5_NCIMM/          # NCIMM test suite (255 files)
├── EPA/                   # Official EPA examples (132 files)
├── Hydraulics/            # Hydraulic model tests (113 files)
├── Hydrology/             # Hydrology model tests (75 files)
├── OWA_EXTRAN/           # Open Water Analytics EXTRAN (67 files)
├── Simon_EPA/             # Community contributed (47 files)
├── LID/                   # Low Impact Development (2 files)
└── ...                    # More categories (122 files)
```

**Run any example:**

```bash
# EPANET example
python wrapi.py run "EPANET Example Files/epanet-desktop/Net1/Net1.inp" --type epanet --wait

# SWMM example
python wrapi.py run "EPASWMM Example Files/EPA/Example1.inp" --type swmm --wait
```

---

## 📚 API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |
| `/simulations` | POST | Create simulation |
| `/simulations` | GET | List simulations |
| `/simulations/{id}` | GET | Get simulation details |
| `/simulations/{id}/files` | GET | List result files |
| `/simulations/{id}/logs` | GET | Get simulation logs |

### Simulation Status

| Status | Description |
|--------|-------------|
| `pending` | Created, waiting to start |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Encountered errors |

### Result File Types

| Type | Description |
|------|-------------|
| `input` | Original input file (.inp) |
| `output` | Binary output file (.out) |
| `report` | Text report file (.rpt) |

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required: API token
WRAPI_TOKEN=your-api-token-here

# Optional: API URL (default: https://wrm.neer.ai)
WRAPI_URL=https://wrm.neer.ai
```

### Config File

Alternatively, use `~/.wrapi_config.json`:

```json
{
  "token": "your-api-token",
  "url": "https://wrm.neer.ai"
}
```

---

## 🔧 Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot open rainfall data file` | Missing auxiliary file | Include with `--aux` flag |
| `ERROR 235: invalid infiltration` | IMD > 1.0 for GREEN_AMPT | IMD must be 0-1 |
| `ERROR 209: undefined object` | Missing object definition | Define before referencing |
| `Convergence failure` | Network issues | Check connectivity |

### Debug Steps

```bash
# 1. Check API health
curl https://wrm.neer.ai/health

# 2. Verify your token
python wrapi.py config --show

# 3. View simulation logs
python wrapi.py logs <simulation-id>

# 4. Download report for errors
python wrapi.py files <simulation-id> --download ./debug
grep -i error ./debug/*.rpt
```

---

## 📚 Resources

- **[Knowledge Base](docs/KNOWLEDGE_BASE.md)** - Error codes, parameter ranges, troubleshooting
- **[API Documentation](https://docs.wrm.neer.io/)** - Full API reference
- **[EPA SWMM Manual](https://www.epa.gov/water-research/storm-water-management-model-swmm)** - Official EPA documentation
- **[EPA EPANET Manual](https://www.epa.gov/water-research/epanet)** - Official EPA documentation

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Support

- **API Issues**: support@neer.ai
- **Documentation**: https://docs.wrm.neer.io/
- **GitHub Issues**: Report bugs and feature requests

---

<div align="center">

**Built with ❤️ by [NEER AIP](https://neer.ai)**

[GitHub](https://github.com/neeraip) • [API Docs](https://docs.wrm.neer.io/) • [Support](mailto:support@neer.ai)

</div>
