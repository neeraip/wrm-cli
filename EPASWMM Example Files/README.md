# EPA SWMM Example Files

This folder contains **813 validated SWMM input files** ready to run on the NEER Water Resources Modeling API.

## 📊 Summary

| Folder | Files | Description |
|--------|-------|-------------|
| `SWMM5_NCIMM/` | 255 | NCIMM comprehensive test suite |
| `EPA/` | 132 | Official EPA SWMM examples and test cases |
| `Hydraulics/` | 113 | Hydraulic routing test models |
| `Hydrology/` | 75 | Hydrologic modeling examples |
| `OWA_EXTRAN/` | 67 | Open Water Analytics EXTRAN models |
| `Simon_EPA/` | 47 | Simon's EPA model collection |
| `Semi_Real_Models/` | 23 | Semi-realistic test scenarios |
| `Weirs/` | 22 | Weir and orifice test models |
| `LEW_CHI_SWMM5.2/` | 19 | LEW/CHI test models |
| `Orifices/` | 15 | Orifice configuration tests |
| `NCIMM_ROUTING/` | 15 | NCIMM routing examples |
| `Pumps/` | 9 | Pump station examples |
| `WQ/` | 5 | Water quality models |
| `XPSWMM/` | 5 | XPSWMM converted models |
| `OWA_ROUTING/` | 5 | OWA routing examples |
| `OWA_update_v5111/` | 2 | OWA version updates |
| `LID/` | 2 | Low Impact Development examples |
| `z1000Years/` | 1 | Long-term simulation example |
| `LEW_update_v5113/` | 1 | LEW version 5.1.13 models |
| **Total** | **813** | |

## 🚀 Running Examples

```bash
# From the project root directory

# Run Example1 - basic SWMM model
python wrapi.py run "EPASWMM Example Files/EPA/Example1.inp" --type swmm --wait

# Run a hydraulics test
python wrapi.py run "EPASWMM Example Files/Hydraulics/extran1.inp" --type swmm --wait

# Run a LID example
python wrapi.py run "EPASWMM Example Files/LID/LID_Model.inp" --type swmm --wait
```

## 📁 Folder Structure

```
EPASWMM Example Files/
├── EPA/                    # Official EPA examples
├── Hydraulics/             # Hydraulic routing tests
├── Hydrology/              # Runoff and infiltration tests
├── LID/                    # Low Impact Development
├── SWMM5_NCIMM/           # NCIMM test suite
│   ├── Conduit_OWA_...
│   ├── Pump_...
│   └── ...
├── OWA_EXTRAN/            # Dynamic wave routing
├── OWA_ROUTING/           # Kinematic wave routing
├── Orifices/              # Orifice configurations
├── Pumps/                 # Pump station models
├── Semi_Real_Models/      # Realistic scenarios
├── Simon_EPA/             # Community contributed
├── Weirs/                 # Weir structures
├── WQ/                    # Water quality
└── XPSWMM/                # Converted models
```

## 📚 Model Categories

### Hydraulics Models
Test dynamic wave routing, pipe flow, surcharging, and pressure flow conditions.

### Hydrology Models  
Test runoff generation, infiltration methods (HORTON, GREEN_AMPT, CURVE_NUMBER), and hydrograph routing.

### LID Models
Low Impact Development practices: rain gardens, green roofs, permeable pavement, bioretention.

### Water Quality Models
Pollutant buildup, washoff, treatment, and water quality routing.

## ⚠️ Validation Notes

- All files validated to run without missing external file dependencies
- Files with minor validation warnings (IMD values) are included but may produce warnings
- Hydraulics-only models (no subcatchments) are included for routing tests

## 📚 Data Sources

These files were collected and validated from:

- [SWMMEnablement 1729-SWMM5-Models](https://github.com/SWMMEnablement/1729-SWMM5-Models)
- Official EPA SWMM distribution
- Open Water Analytics (OWA) test suite

## 📖 Learn More

- [SWMM User Manual](https://www.epa.gov/water-research/storm-water-management-model-swmm)
- [Knowledge Base](../docs/KNOWLEDGE_BASE.md) - Error codes and troubleshooting
- [NEER swmm-utils Library](https://github.com/neeraip/swmm-utils) - Python tools for SWMM
