# MRPL Sovereign Industrial AI Workbench — Roadmap

**Smart India Hackathon Problem Statement: SIH26117**  
**Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL) — MoPNG  
**Project:** Sovereign On-Premise Agentic AI Workbench using OpenWeight-Multimodal LLMs for Confidential Industrial Operations

---

## 1. High Priority Milestones (Q3–Q4 2026)

### 1.1 Air-Gapped Foundation & Edge Acceleration
- **Zero-WAN Verification:** Guarantee complete offline operation with 0-WAN egress enforcement and socket-level packet blocking for untrusted destinations.
- **Local Multimodal Engine:** Optimize Qwen-2.5-VL and DeepSeek-R1 inference on local vLLM, llama.cpp, and Ollama clusters.
- **Dynamic Speculative Decoding:** Deploy local draft models to reduce wall-clock turnaround time for complex HAZOP reasoning chains.

### 1.2 Mechanical Integrity & Engineering Engines
- **API 510 Pressure Vessel Module:** Complete automated circumferential and longitudinal stress calculations (ASME BPVC Sec VIII Div 1 UG-27) with remaining corrosion allowance forecasts.
- **API 570 Process Piping Module:** Barlow-formula retirement thickness verification, Class 1/2/3 circuit categorization, and automated 5-year statutory inspection cap alerting.
- **API 610 Centrifugal Pump Hydraulics:** Automated NPSH available vs required calculations with API 610 safety buffer enforcement ($\ge 1.1 \cdot NPSH_r$).
- **TEMA / ASME Heat Exchanger Duty:** LMTD and heat transfer area rating with automatic temperature-cross warnings across crude preheat trains.

### 1.3 Process Optimization & Refinery Operations
- **True Boiling Point (TBP) Distillation Engine:** Cut predictions for LPG/Naphtha, Middle Distillates, VGO, and Vacuum Residue from blended assays.
- **Crude Compatibility Index (CCI):** Automated compatibility scoring to eliminate asphaltene flocculation during crude switchovers.
- **OISD-105 Turnaround & Shutdown Planner:** 7-phase statutory shutdown sequencing, battery-limit blind list generation, and safety permit compliance under OISD-105 and Factories Act 1948.

### 1.4 Computer Vision & Engineering Drawings
- **ISA-5.1 Instrument Loop Extraction:** High-resolution tile decomposition ($1024\times 1024$) for A0/A1 scanned P&ID schematics.
- **Automated HAZOP Heuristics:** Real-time flagging of unisolated vessels, unlinked control valves, and missing safety valves (PSVs/PRVs).

### 1.5 Enterprise Compliance & Security
- **Cryptographic Merkle DAG Audit Trail:** Real-time SHA-256 block linking for every industrial tool invocation, parameter update, and calculation run.
- **Industrial RBAC:** Strict departmental access enforcement (`OPERATIONS_TAR`, `PROCESS_ENGINEERING`, `RELIABILITY_INSPECTION`, `HSE_SAFETY`, `EXECUTIVE_MANAGEMENT`).
- **Forensic Export:** Signed Merkle root verification bundles for statutory compliance audits (OISD / PNGRB / CCOE).

---

## 2. Platform Architecture & Hardening

- **Microservices Isolation:** Hardened containerization with local SQLite/PostgreSQL, local vector store (ChromaDB), and air-gapped search.
- **Prompt Injection Defense:** Strict separation of untrusted telemetry, scanned documents, and industrial system prompt instructions.
- **High-Availability Clustering:** Multi-node load balancing for local LLM inference engines across industrial control network zones.
