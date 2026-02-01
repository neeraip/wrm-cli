# EPANET Example Files

This folder contains **188 validated EPANET input files** ready to run on the NEER Water Resources Modeling API.

## 📊 Summary

| Source | Files | Description |
|--------|-------|-------------|
| `asce-tf-wdst/` | 31 | ASCE Task Force on Water Distribution System Testbeds benchmarks |
| `collect-epanet-inp/` | 112 | Community contributed models from KIOS Research |
| `epanet-desktop/` | 2 | Official EPANET desktop examples (Net1, Net3) |
| `epanet-example-networks/` | 42 | EPANET test suite models |
| `L-Town/` | 1 | L-Town benchmark network |
| **Total** | **188** | |

## 🚀 Running Examples

```bash
# From the project root directory

# Run Net1 example
python wrapi.py run "EPANET Example Files/epanet-desktop/Net1/Net1.inp" --type epanet --wait

# Run L-Town benchmark
python wrapi.py run "EPANET Example Files/L-Town/L-TOWN.inp" --type epanet --wait

# Run Anytown benchmark
python wrapi.py run "EPANET Example Files/asce-tf-wdst/Anytown/Anytown.inp" --type epanet --wait
```

## 📁 Folder Structure

```
EPANET Example Files/
├── asce-tf-wdst/                    # ASCE benchmark networks
│   ├── Anytown/
│   ├── Balerma/
│   ├── Battle of the Calibration Networks System/
│   ├── Battle of the Water Sensor Networks/
│   ├── exnet/
│   ├── Extended Hanoi/
│   ├── Hanoi/
│   ├── ky1/ through ky15/           # Kentucky networks
│   └── ...
├── collect-epanet-inp/              # Community models
├── epanet-desktop/                  # Official examples
│   ├── Net1/
│   └── Net3/
├── epanet-example-networks/         # Test suite
│   └── epanet-tests/
└── L-Town/                          # L-Town benchmark
```

## 📚 Data Sources

These files were collected and validated from:

- [KIOS Research EPANET Benchmarks](https://github.com/KIOS-Research/EPANET-Benchmarks)
- [ASCE Task Force on Water Distribution System Testbeds](https://www.asce.org/)
- Official EPA EPANET distribution

## ⚠️ Notes

- All files have been validated to run without external file dependencies
- Files with `[BACKDROP]` section references to image files are included (backdrop images are optional for simulation)
- Some models may take longer to run depending on network size and simulation duration

## 📖 Learn More

- [EPANET User Manual](https://www.epa.gov/water-research/epanet)
- [Knowledge Base](../docs/KNOWLEDGE_BASE.md) - Error codes and troubleshooting
- [NEER swmm-utils Library](https://github.com/neeraip/swmm-utils) - Python tools for SWMM/EPANET