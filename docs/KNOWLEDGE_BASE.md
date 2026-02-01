# Water Resources Modeling Knowledge Base

A comprehensive reference for EPA SWMM and EPANET simulations, including error codes, parameter ranges, and troubleshooting guides.

**Official Documentation:**
- [EPA SWMM](https://www.epa.gov/water-research/storm-water-management-model-swmm)
- [EPA EPANET](https://www.epa.gov/water-research/epanet)
- [EPANET 2.2 User Manual](https://usepa.github.io/EPANET2.2/)
- [OWA-EPANET Wiki](https://github.com/openwateranalytics/epanet/wiki)

---

## Table of Contents

1. [SWMM Overview](#swmm-overview)
2. [SWMM Error Codes](#swmm-error-codes)
3. [SWMM Parameter Ranges](#swmm-parameter-ranges)
4. [EPANET Overview](#epanet-overview)
5. [EPANET Error Codes](#epanet-error-codes)
6. [EPANET Parameter Ranges](#epanet-parameter-ranges)
7. [Common Troubleshooting](#common-troubleshooting)
8. [Input File Section Order](#input-file-section-order)

---

## SWMM Overview

EPA's Storm Water Management Model (SWMM) is used for planning, analysis, and design related to:
- Stormwater runoff
- Combined sewer systems
- Sanitary sewers
- Drainage systems
- Green infrastructure

**Current Version:** 5.2.4 (August 2023)

### Capabilities
- Hydrologic modeling (rainfall-runoff)
- Hydraulic routing (pipes, channels, storage)
- Water quality simulation
- LID/Green infrastructure controls
- Real-time control simulation

---

## SWMM Error Codes

### Input File Errors (100-199)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| 101 | Memory allocation error | Insufficient memory | Reduce model size or increase system memory |
| 103 | Cannot solve KW equations | Kinematic wave routing failed | Check conduit slopes and roughness |
| 105 | Cannot open ODE solver | Differential equation solver error | Reinstall SWMM |
| 107 | Cannot compute conduit slope | Invalid conduit geometry | Verify inlet/outlet elevations |
| 108 | Cannot compute time step | Routing timestep calculation failed | Adjust routing timestep |
| 109 | Cannot open scratch file | Disk access error | Check disk space and permissions |
| 110 | Cannot open rainfall file | External rainfall data file missing | Verify file path or include in ZIP |
| 111 | Cannot open runoff file | Runoff interface file error | Check file permissions |
| 113 | Cannot open routing file | Routing interface file error | Check file permissions |
| 114 | Cannot open report file | Report output file error | Check output directory |
| 115 | Cannot open output file | Binary output file error | Check disk space |
| 117 | Cannot open climate file | Temperature/evaporation file missing | Include file in ZIP package |

### Data Errors (200-299)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| **200** | One or more errors in input file | General input parsing error | Check .rpt file for specific line |
| **201** | Too few items | Missing required parameters | Add missing values |
| **203** | Invalid keyword | Unknown section or parameter | Check spelling and SWMM version |
| **205** | Invalid number | Non-numeric where number expected | Fix data format |
| **207** | Invalid ID name | Object name contains invalid characters | Use alphanumeric names only |
| **209** | Undefined object | Reference to non-existent object | Define object before referencing |
| **211** | Invalid number of items | Wrong parameter count | Check section format |
| **213** | Duplicate ID name | Object defined twice | Remove duplicate |
| **215** | Invalid date | Date format error | Use MM/DD/YYYY |
| **217** | Invalid time | Time format error | Use HH:MM:SS |
| **219** | Undefined curve | Missing curve definition | Add [CURVES] entry |
| **221** | Invalid curve data | Curve has errors | Check X-Y pairs |
| **223** | Undefined time series | Missing timeseries | Add [TIMESERIES] entry |
| **225** | Mismatching number of items | Section data mismatch | Verify column count |
| **227** | Invalid inlet type | Unknown inlet definition | Check [INLETS] section |
| **229** | Undefined inlet | Reference to missing inlet | Define inlet first |
| **231** | Undefined aquifer | Missing aquifer definition | Add [AQUIFERS] entry |
| **233** | Invalid infiltration method | Unknown infiltration type | Use HORTON, GREEN_AMPT, or CURVE_NUMBER |
| **235** | Invalid infiltration parameters | Parameter values out of range | **See table below** |
| **237** | Invalid aquifer parameters | Aquifer data errors | Check parameter ranges |
| **239** | Invalid groundwater parameters | GW equation errors | Verify coefficients |
| **241** | Invalid exfiltration parameters | LID exfiltration errors | Check LID definition |

### Infiltration Parameter Errors (ERROR 235)

| Method | Parameters | Valid Ranges |
|--------|------------|--------------|
| **HORTON** | MaxRate, MinRate, Decay, DryTime, MaxInfil | MaxRate > MinRate; Decay > 0; DryTime ≥ 0 |
| **GREEN_AMPT** | Suction, Ksat, IMD | Suction > 0; Ksat > 0; **IMD: 0-1** |
| **CURVE_NUMBER** | CurveNumber, Ksat, DryTime | CN: 0-100; Ksat ≥ 0 |

### File Reference Errors (300-399)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| **317** | Cannot open rainfall data file | External .dat file not found | Include file in ZIP or use TIMESERIES |
| **319** | Cannot open RDII file | RDII data file missing | Check path or include in package |
| **321** | Cannot open routing interface file | Routing file not found | Verify file location |
| **323** | Cannot open runoff interface file | Runoff file not found | Verify file location |
| **325** | Cannot open hot start file | Hot start file missing | Check file path |
| **327** | Cannot open outflows file | External outflow file missing | Verify file location |
| **329** | Invalid pollutant name | Unknown pollutant reference | Define in [POLLUTANTS] |
| **331** | Cannot open rain gage file | Rain gage external file missing | Include in ZIP package |
| **333** | Cannot read rain gage data | Rain file format error | Check data format |
| **335** | Invalid format for rain gage data | Wrong data columns | Verify format matches gage type |
| **337** | Cannot open climate file | Temperature/wind file missing | Include in ZIP package |
| **339** | Cannot open snow melt file | Snow data file missing | Include in ZIP package |

### Runtime Errors (400-499)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| 401 | General system error | Memory or I/O failure | Restart simulation |
| 402 | Cannot open report file | Write permission denied | Check file permissions |
| 403 | Cannot open binary output file | Disk full or permission error | Free disk space |
| 405 | Memory allocation error | Out of memory | Reduce model complexity |
| 407 | Cannot open scratch file | Temp file creation failed | Check temp directory |
| 409 | Cannot read from scratch file | Disk error | Check disk health |
| 411 | Cannot write to scratch file | Disk full | Free disk space |

---

## SWMM Parameter Ranges

### [OPTIONS] Section

| Parameter | Valid Values | Default | Description |
|-----------|--------------|---------|-------------|
| FLOW_UNITS | CFS, GPM, MGD, CMS, LPS, MLD | CFS | Flow rate units |
| INFILTRATION | HORTON, GREEN_AMPT, CURVE_NUMBER | HORTON | Infiltration model |
| FLOW_ROUTING | STEADY, KINWAVE, DYNWAVE | DYNWAVE | Routing method |
| LINK_OFFSETS | DEPTH, ELEVATION | DEPTH | Offset reference |
| FORCE_MAIN_EQUATION | H-W, D-W | H-W | Hazen-Williams or Darcy-Weisbach |
| MIN_SLOPE | ≥ 0 | 0 | Minimum conduit slope (%) |
| ALLOW_PONDING | YES, NO | NO | Surface ponding allowed |
| MIN_SURFAREA | ≥ 0 | 12.566 | Minimum node surface area (ft²) |
| MIN_ROUTE_STEP | 0.001-10 | 0.5 | Minimum routing step (sec) |
| LENGTHENING_STEP | 0-3600 | 0 | Conduit lengthening step (sec) |
| VARIABLE_STEP | 0-1 | 0.75 | Time step safety factor |

### [SUBCATCHMENTS] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Area | > 0 | acres or hectares | Subcatchment area |
| Width | > 0 | ft or m | Characteristic width |
| %Slope | 0-100 | % | Average surface slope |
| %Imperv | 0-100 | % | Percent impervious |
| N-Imperv | 0.001-1.0 | - | Manning's N for impervious |
| N-Perv | 0.001-1.0 | - | Manning's N for pervious |
| S-Imperv | 0-10 | in or mm | Depression storage (imperv) |
| S-Perv | 0-10 | in or mm | Depression storage (perv) |

### [JUNCTIONS] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Elevation | any | ft or m | Invert elevation |
| MaxDepth | ≥ 0 | ft or m | Max water depth (0 = unlimited) |
| InitDepth | ≥ 0 | ft or m | Initial water depth |
| SurDepth | ≥ 0 | ft or m | Surcharge depth |
| Aponded | ≥ 0 | ft² or m² | Ponded area |

### [CONDUITS] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Length | > 0 | ft or m | Conduit length |
| Roughness | 0.001-1.0 | - | Manning's roughness |
| InOffset | ≥ 0 | ft or m | Inlet offset |
| OutOffset | ≥ 0 | ft or m | Outlet offset |
| InitFlow | ≥ 0 | flow units | Initial flow |
| MaxFlow | ≥ 0 | flow units | Maximum flow (0 = unlimited) |

### Infiltration Parameters

#### HORTON Method
| Parameter | Valid Range | Typical Values |
|-----------|-------------|----------------|
| MaxRate | 0-100 in/hr | 3.0 in/hr |
| MinRate | 0-MaxRate | 0.5 in/hr |
| Decay | 0-10 1/hr | 4.0 1/hr |
| DryTime | 0-30 days | 7 days |
| MaxInfil | 0-100 in | 0 (unlimited) |

#### GREEN_AMPT Method
| Parameter | Valid Range | Typical Values |
|-----------|-------------|----------------|
| Suction | 0-20 in | 4.0 in (clay) - 2.0 in (sand) |
| Ksat | 0-10 in/hr | 0.01-1.0 in/hr |
| **IMD** | **0-1** | **0.1-0.3** |

#### CURVE_NUMBER Method
| Parameter | Valid Range | Typical Values |
|-----------|-------------|----------------|
| CurveNumber | 0-100 | 70-90 (urban) |
| Ksat | 0-10 in/hr | 0 = calculated |
| DryTime | 0-30 days | 7 days |

---

## EPANET Overview

EPANET is a software application for modeling water distribution piping systems. It performs:
- Extended period simulation
- Hydraulic analysis (flow, pressure, head)
- Water quality modeling (chlorine, age, source tracing)

**Current Version:** 2.2 / 2.3.3

### Components Modeled
- Pipes (any material/diameter)
- Nodes (junctions)
- Pumps (constant/variable speed)
- Valves (PRV, PSV, FCV, TCV, GPV, PBV)
- Tanks and Reservoirs
- Controls and Rules

---

## EPANET Error Codes

### Input File Errors (200-299)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| 200 | One or more errors in input file | Parsing failed | Check line numbers in message |
| 201 | Syntax error in input file | Invalid format | Fix line syntax |
| 202 | Illegal numeric value | Number out of range | Check parameter limits |
| 203 | Undefined node | Reference to unknown node | Define node first |
| 204 | Undefined link | Reference to unknown link | Define link first |
| 205 | Undefined time pattern | Missing pattern | Add [PATTERNS] entry |
| 206 | Undefined curve | Missing curve | Add [CURVES] entry |
| 207 | Attempt to control CV | Check valve control error | Remove invalid control |
| 208 | Illegal PDA pressure limits | Invalid pressure bounds | Fix pressure limits |
| 209 | Illegal node property | Invalid node parameter | Check valid ranges |
| 210 | Illegal link property | Invalid link parameter | Check valid ranges |
| 211 | Undefined source node | Source at unknown node | Define node first |
| 212 | Undefined trace node | Trace at unknown node | Define node first |
| 213 | Invalid option value | Bad [OPTIONS] value | Check valid values |
| 214 | Too many characters | Line too long | Split into multiple lines |
| 215 | Duplicate ID | Object defined twice | Remove duplicate |
| 216 | Cannot read file | File access error | Check permissions |
| 217 | Invalid demand category | Bad demand type | Use JUNCTION, TANK, etc. |
| 219 | Illegal valve connection | Valve topology error | Check valve placement |
| 220 | Illegal pump connection | Pump topology error | Check pump placement |
| 223 | Not enough nodes | Network too small | Add more nodes |
| 224 | No tanks or reservoirs | No fixed grade nodes | Add tank or reservoir |
| 225 | Invalid lower/upper levels | Tank level error | Lower < Init < Upper |
| 226 | No pump curve | Pump missing curve | Add pump curve |
| 227 | Invalid pump curve | Bad pump curve data | Check flow-head pairs |

### Hydraulic Solver Errors (100-199)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| 101 | Memory allocation error | Out of memory | Reduce network size |
| 102 | No network data | Empty input file | Add network elements |
| 104 | Unconnected node | Isolated node | Connect to network |
| 106 | Pump cannot deliver head | Pump curve exceeded | Check pump curve |
| 110 | Cannot solve hydraulic equations | Convergence failure | Check network connectivity |
| 120 | Cannot solve water quality equations | WQ solver failed | Check reaction rates |

### File Errors (300-309)

| Code | Message | Description | Solution |
|------|---------|-------------|----------|
| 301 | Same input/output file | File conflict | Use different names |
| 302 | Cannot open input file | File not found | Check file path |
| 303 | Cannot open report file | Write error | Check permissions |
| 304 | Cannot open binary file | Output file error | Check disk space |
| 305 | Cannot open hydraulics file | HYD file error | Check file path |
| 306 | Hydraulics file version mismatch | Wrong file version | Regenerate file |
| 307 | Cannot read hydraulics file | File corrupted | Regenerate file |
| 308 | Cannot save results | Output error | Check disk space |
| 309 | Cannot write report file | Write failed | Check permissions |

---

## EPANET Parameter Ranges

### [JUNCTIONS] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Elevation | any | ft or m | Node elevation |
| Demand | any | flow units | Base demand |
| Pattern | - | - | Demand pattern ID |

### [TANKS] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Elevation | any | ft or m | Bottom elevation |
| InitLevel | ≥ 0 | ft or m | Initial water level |
| MinLevel | ≥ 0 | ft or m | Minimum level |
| MaxLevel | > MinLevel | ft or m | Maximum level |
| Diameter | > 0 | ft or m | Tank diameter |
| MinVol | ≥ 0 | volume units | Minimum volume |

### [PIPES] Section

| Parameter | Valid Range | Units | Description |
|-----------|-------------|-------|-------------|
| Length | > 0 | ft or m | Pipe length |
| Diameter | > 0 | in or mm | Pipe diameter |
| Roughness | > 0 | - | Roughness coefficient |
| MinorLoss | ≥ 0 | - | Minor loss coefficient |
| Status | OPEN, CLOSED, CV | - | Initial status |

### Roughness Coefficients

#### Hazen-Williams C (HEADLOSS = H-W)
| Pipe Material | C Value Range |
|---------------|---------------|
| PVC | 140-150 |
| New cast iron | 130-140 |
| 10-year cast iron | 100-110 |
| 20-year cast iron | 80-90 |
| Concrete | 120-140 |
| Steel | 140-150 |

#### Darcy-Weisbach ε (HEADLOSS = D-W)
| Pipe Material | ε (mm) |
|---------------|--------|
| PVC/Plastic | 0.0015 |
| Copper | 0.0015 |
| Steel | 0.045 |
| Cast iron | 0.26 |
| Concrete | 0.3-3.0 |
| Riveted steel | 0.9-9.0 |

### [PUMPS] Section

| Parameter | Valid Range | Description |
|-----------|-------------|-------------|
| HEAD curve | Required | Head-flow curve ID |
| SPEED | 0-2 | Relative speed (1=nominal) |
| PATTERN | Optional | Speed pattern ID |
| POWER | > 0 | Constant power (kW or hp) |

### [VALVES] Section

| Type | Setting Parameter | Valid Range |
|------|-------------------|-------------|
| PRV (Pressure Reducing) | Pressure | ≥ 0 psi/m |
| PSV (Pressure Sustaining) | Pressure | ≥ 0 psi/m |
| PBV (Pressure Breaker) | Pressure | ≥ 0 psi/m |
| FCV (Flow Control) | Flow | ≥ 0 flow units |
| TCV (Throttle Control) | Loss Coeff | ≥ 0 |
| GPV (General Purpose) | Curve ID | Headloss curve |

---

## Common Troubleshooting

### SWMM Issues

#### "Cannot open rainfall data file"
```
ERROR 317: cannot open rainfall data file C:\path\to\file.dat
```
**Solutions:**
1. Include the .dat file in your ZIP package
2. Update path in .inp to relative: `FILE "rainfall.dat"`
3. Convert to inline TIMESERIES

#### "Invalid infiltration parameters" (ERROR 235)
```
ERROR 235: invalid infiltration parameters at line XXX
```
**Common causes:**
- IMD (Initial Moisture Deficit) > 1 for GREEN_AMPT
- MaxRate < MinRate for HORTON
- Negative values

**Fix:** Check parameter ranges above

#### "Undefined object" (ERROR 209)
```
ERROR 209: undefined object TIMESERIES_NAME
```
**Solutions:**
1. Define the object before referencing it
2. Check section order (TIMESERIES before RAINGAGES)
3. Verify spelling matches exactly (case-sensitive)

#### Section Order Issues
SWMM requires certain sections before others:
- [TIMESERIES] must come before [RAINGAGES] if gages reference timeseries
- [CURVES] must come before [PUMPS] if pumps reference curves
- [PATTERNS] must come before objects using patterns

### EPANET Issues

#### "Cannot solve hydraulic equations" (ERROR 110)
**Possible causes:**
1. Disconnected network
2. All pumps/valves closed
3. No pressure source (tank/reservoir)
4. Negative pressures with DDA

**Solutions:**
- Check network connectivity
- Verify at least one tank/reservoir exists
- Enable pressure-dependent demands (PDA)

#### "Pump cannot deliver head" (ERROR 106)
**Cause:** Required head exceeds pump curve capacity

**Solutions:**
- Check pump curve head-flow data
- Verify system head requirements
- Consider multiple pumps in series

#### Negative Pressures
**Solutions:**
1. Lower junction elevations
2. Increase tank/reservoir head
3. Use pressure-dependent demand analysis (PDA)
4. Add pumping capacity

---

## Input File Section Order

### SWMM Recommended Order
```
[TITLE]
[OPTIONS]
[EVAPORATION]
[TEMPERATURE]          ← Before RAINGAGES if using external file
[RAINGAGES]
[TIMESERIES]           ← Should be before RAINGAGES if gages use timeseries
[PATTERNS]
[CURVES]
[SUBCATCHMENTS]
[SUBAREAS]
[INFILTRATION]
[AQUIFERS]
[GROUNDWATER]
[LID_CONTROLS]
[LID_USAGE]
[JUNCTIONS]
[OUTFALLS]
[DIVIDERS]
[STORAGE]
[CONDUITS]
[PUMPS]
[ORIFICES]
[WEIRS]
[OUTLETS]
[XSECTIONS]
[TRANSECTS]
[CONTROLS]
[INFLOWS]
[DWF]
[RDII]
[LOADINGS]
[TREATMENT]
[REPORT]
[TAGS]
[MAP]
[COORDINATES]
[VERTICES]
[POLYGONS]
[SYMBOLS]
[LABELS]
[BACKDROP]
```

### EPANET Recommended Order
```
[TITLE]
[JUNCTIONS]
[RESERVOIRS]
[TANKS]
[PIPES]
[PUMPS]
[VALVES]
[TAGS]
[DEMANDS]
[STATUS]
[PATTERNS]
[CURVES]
[CONTROLS]
[RULES]
[ENERGY]
[EMITTERS]
[QUALITY]
[SOURCES]
[REACTIONS]
[MIXING]
[TIMES]
[REPORT]
[OPTIONS]
[COORDINATES]
[VERTICES]
[LABELS]
[BACKDROP]
```

---

## Additional Resources

### Official Documentation
- [SWMM 5.2 User's Manual (PDF)](https://www.epa.gov/system/files/documents/2022-04/swmm-users-manual-version-5.2.pdf)
- [SWMM Reference Manual - Hydrology](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100NYRA.TXT)
- [EPANET 2.2 User Manual](https://usepa.github.io/EPANET2.2/)

### Community Resources
- [Open EPANET Knowledge Base](https://www.openepanet.org)
- [SWMM Users Listserv](mailto:listserv@listserv.uoguelph.ca) - Subscribe with "subscribe swmm-users"
- [OWA-EPANET GitHub](https://github.com/openwateranalytics/epanet)

### Python Library
- [**swmm-utils**](https://github.com/neeraip/swmm-utils) - NEER's Python library for SWMM file parsing

---

## NEER swmm-utils Library

**Repository:** [github.com/neeraip/swmm-utils](https://github.com/neeraip/swmm-utils)

A Python library for interpreting EPA SWMM input (.inp), report (.rpt), and output (.out) files.

### Installation

```bash
pip install swmm-utils
```

### Features

- **Decode .inp files** → Python dict, JSON, or Parquet
- **Encode to .inp files** ← from dict, JSON, or Parquet
- **Parse .rpt files** → Extract simulation results
- **Read .out files** → Time series data with pandas DataFrames
- **Round-trip conversion** - Full data preservation

### Quick Examples

#### Read and Modify Input File
```python
from swmm_utils import SwmmInput

# Load and inspect
with SwmmInput("model.inp") as model:
    print(f"Junctions: {len(model.junctions)}")
    print(f"Conduits: {len(model.conduits)}")
    
    # Modify parameters
    for junction in model.junctions:
        junction['max_depth'] = 10.0
    
    # Save changes
    model.save("modified_model.inp")
```

#### Parse Simulation Report
```python
from swmm_utils import SwmmReport

with SwmmReport("results.rpt") as report:
    # Get simulation summary
    print(f"Duration: {report.analysis_options.get('total_duration')}")
    print(f"Continuity Error: {report.runoff_quantity.get('continuity_error')}%")
    
    # Check for flooding
    if report.node_flooding:
        for node in report.node_flooding:
            print(f"Node {node['node']}: {node['hours_flooded']} hrs flooded")
```

#### Export Time Series from Output File
```python
from swmm_utils import SwmmOutput

output = SwmmOutput("simulation.out", load_time_series=True)

# Get link flow time series
link_df = output.to_dataframe('links', 'Conduit1')
print(link_df.head())

# Export to CSV
link_df.to_csv("conduit1_flow.csv")
```

#### Convert Formats
```python
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder

decoder = SwmmInputDecoder()
encoder = SwmmInputEncoder()

# .inp → JSON
model = decoder.decode_file("model.inp")
encoder.encode_to_json(model, "model.json", pretty=True)

# JSON → Parquet
json_model = decoder.decode_json("model.json")
encoder.encode_to_parquet(json_model, "model.parquet")

# Parquet → .inp (round-trip)
parquet_model = decoder.decode_parquet("model.parquet")
encoder.encode_to_inp_file(parquet_model, "restored.inp")
```

### Report Sections Available

| Section | Description |
|---------|-------------|
| `analysis_options` | Simulation settings |
| `runoff_quantity` | Rainfall/runoff summary |
| `runoff_quality` | Pollutant loading summary |
| `groundwater_summary` | GW flow statistics |
| `node_depth` | Max depth at nodes |
| `node_inflow` | Max inflow at nodes |
| `node_flooding` | Flooding statistics |
| `node_surcharge` | Surcharge statistics |
| `outfall_loading` | Outfall pollutant loads |
| `link_flow` | Max flow in links |
| `conduit_surcharge` | Surcharge in conduits |
| `pumping_summary` | Pump performance |
| `lid_performance` | LID control effectiveness |

### Documentation

- [SWMM Input File Reference](https://github.com/neeraip/swmm-utils/blob/main/docs/SWMM_INPUT_FILE.md)
- [SWMM Report File Reference](https://github.com/neeraip/swmm-utils/blob/main/docs/SWMM_REPORT_FILE.md)
- [SWMM Output File Reference](https://github.com/neeraip/swmm-utils/blob/main/docs/SWMM_OUTPUT_FILE.md)

---

## Quick Reference Card

### SWMM Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| ERROR 235 (infiltration) | IMD must be 0-1 for GREEN_AMPT |
| ERROR 209 (undefined) | Define object before referencing |
| ERROR 317 (rainfall file) | Include .dat in ZIP, use relative path |
| ERROR 337 (climate file) | Include .dat in ZIP, use relative path |

### EPANET Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| ERROR 110 (convergence) | Check network connectivity |
| ERROR 106 (pump head) | Verify pump curve capacity |
| ERROR 203 (undefined node) | Define node before using |
| ERROR 224 (no tanks) | Add at least one tank/reservoir |

---

*Last updated: January 2026*
*SWMM Version: 5.2.4 | EPANET Version: 2.2/2.3.3*
