# MRPL Sovereign On-Premise Agentic AI Workbench
### Smart India Hackathon Problem Statement: SIH26117
**Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL) — Ministry of Petroleum & Natural Gas (MoPNG)  
**Title:** Sovereign On-Premise Agentic AI Workbench using OpenWeight-Multimodal LLMs for Confidential Industrial Operations  
**GitHub Repository:** [https://github.com/Vinayak0928/odin.git](https://github.com/Vinayak0928/odin.git)

---

## 1. Executive Summary & Sovereignty Architecture

Refinery operations in Public Sector Undertakings (PSUs) like **MRPL** demand stringent data confidentiality, operational safety, and statutory compliance (OISD, IBR, CCOE, ASME). Commercial cloud AI systems (OpenAI, Anthropic, Copilot) pose severe data leakage risks for proprietary crude assays, P&ID schematics, turnaround blind schedules, and equipment health metrics.

This workbench is a **100% sovereign, air-gapped, on-premise industrial AI workbench** powered exclusively by **open-weight multimodal foundation models** running locally on Ollama, vLLM, and llama.cpp.

```
+-----------------------------------------------------------------------------------------+
|                  MRPL AIR-GAPPED BOUNDARY (0-WAN VERIFIED / NO INTERNET)                |
|                                                                                         |
|   +-------------------+   +-----------------------+   +-----------------------------+   |
|   |  Browser Web UI   |   |   FastAPI REST API    |   |  Open-Weight Model Engine   |   |
|   |  - P&ID Inspector |<->|  - API 510/570 Engine |<->|  - Qwen-2.5-VL (Vision)     |   |
|   |  - Merkle Audit   |   |  - Turnaround Planner |   |  - DeepSeek-R1 (Reasoning)  |   |
|   |  - Process Calcs  |   |  - Crude Distillation |   |  - Qwen-2.5-Coder (Code)    |   |
|   +-------------------+   +-----------------------+   +-----------------------------+   |
|                                       |                                                 |
|                                       v                                                 |
|                         +---------------------------+                                   |
|                         | Cryptographic Merkle DAG  |                                   |
|                         | Tamper-Evident Audit Log  |                                   |
|                         | (SHA-256 Chained Blocks)  |                                   |
|                         +---------------------------+                                   |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Core Industrial Intelligence Modules

### 2.1 API 510 Pressure Vessel Integrity & Remaining Life
- **Formulas:** ASME BPVC Section VIII Division 1 (UG-27) circumferential stress:
  $$t_{\text{min}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}$$
- Calculates corrosion rate (mpy), remaining corrosion allowance, remaining safe operating life, and statutory next inspection intervals.

### 2.2 API 570 Process Piping Inspection & Retirement Limits
- **Formulas:** ASME B31.3 Barlow circumferential pressure thickness:
  $$t_{\text{min}} = \frac{P \cdot D}{2(S \cdot E + P \cdot Y)}$$
- Automatically classifies refinery piping circuits (Class 1 high-sour/flammable, Class 2, Class 3) and enforces 5-year maximum inspection caps for Class 1 services.

### 2.3 API 610 Centrifugal Pump Hydraulics & Cavitation Prevention
- Evaluates fluid velocity, Reynolds number ($Re$), and Darcy-Weisbach friction head loss ($h_f$).
- Computes Net Positive Suction Head Available ($NPSH_a$) vs Required ($NPSH_r$) and enforces API 610 safety buffer margins ($\ge 1.1 \cdot NPSH_r$ or $+3\text{ ft}$).

### 2.4 TEMA / ASME Shell & Tube Heat Exchanger Rating
- Calculates thermal duty ($Q = \dot{m} \cdot C_p \cdot \Delta T$), counter-current Logarithmic Mean Temperature Difference (LMTD), and required heat transfer area ($A = \frac{Q}{U \cdot \text{LMTD}}$).
- Detects temperature crosses in crude preheat trains.

### 2.5 True Boiling Point (TBP) Distillation Yields & Crude Compatibility (CCI)
- Linear blending of API gravity, sulfur (wt%), and kinematic viscosity.
- True Boiling Point (TBP) cut predictions: LPG/Naphtha ($<150^\circ\text{C}$), Middle Distillates ($150-350^\circ\text{C}$), Vacuum Gas Oil ($350-540^\circ\text{C}$), and Vacuum Residue ($>540^\circ\text{C}$).
- Computes Crude Compatibility Index (CCI) to prevent asphaltene flocculation and heat exchanger fouling during crude switches (e.g. Arab Light vs Maya/Basrah blends).

### 2.6 OISD-105 Refinery Turnaround & Shutdown Planner
- Generates 7-phase statutory shutdown execution schedules (Preparation & De-inventorying, Nitrogen/Steam Purge & LEL Gas Testing, Mechanical Blinding, Equipment Internal Entry & Overhaul, Hydrotesting & Box-Up, De-blinding & Nitrogen Leak Test, Commissioning & Start-up).
- Generates battery-limit blind lists with Spectacle/Slip blind specs, tray inspection requirements, and statutory safety permit checklists under OISD-105, OISD-156, and Factories Act 1948 Section 36.

### 2.7 Scanned P&ID Drawing Inspection & HAZOP Audit
- High-resolution sliding-window tile decomposition ($1024\times 1024$ with 200px overlap) for A0/A1 refinery engineering drawings.
- ISA-5.1 instrument loop extraction (FT, FIC, FCV, PT, PIC, PCV, PSV, PRV, TT, TIC, LT, LIC).
- Automated HAZOP heuristics: detects unprotected pressure vessels lacking emergency PSVs, orphaned control valves lacking transmitter loops, and pump isolation deficiencies.

### 2.8 Cryptographic Merkle DAG Audit Trail
- Every industrial calculation, prompt, inspection, and turnaround plan is hashed with SHA-256 into a cryptographically linked DAG block:
  $$\text{Block Hash} = \text{SHA256}(\text{Index} \parallel \text{Timestamp} \parallel \text{Action} \parallel \text{User} \parallel \text{Dept} \parallel \text{Egress} \parallel \text{PrevHash} \parallel \text{Payload})$$
- Computes dynamic Merkle Root for non-repudiation and external compliance audits (OISD/PNGRB/CBI forensics).

---

## 3. Departmental Role-Based Access Control (RBAC)

| Department | Permitted Tools & APIs |
| :--- | :--- |
| **OPERATIONS_TAR** | `plan_refinery_turnaround`, `calc_pump_hydraulics`, `calc_heat_exchanger_duty`, `verify_audit_log` |
| **PROCESS_ENGINEERING** | `optimize_crude_blend`, `calc_heat_exchanger_duty`, `calc_pump_hydraulics`, `verify_audit_log` |
| **RELIABILITY_INSPECTION** | `calc_vessel_thickness_api510`, `calc_pipe_thickness_api570`, `calc_pump_hydraulics`, `inspect_pid_drawing` |
| **HSE_SAFETY** | `inspect_pid_drawing`, `verify_audit_log`, `calc_vessel_thickness_api510` |
| **EXECUTIVE_MANAGEMENT** | Complete refinery oversight, all industrial calculations & Merkle DAG audit verification |

---

## 4. Pruned Consumer Features (Strict Air-Gap Hardening)

To guarantee zero external attack surface and maintain focus on MRPL industrial workflows, the following personal/consumer modules were intentionally excised:
- **Email Subsystem:** IMAP/SMTP mail pollers, composer, accounts, and email inbox routes.
- **Personal Calendar:** CalDAV synchronizers and personal calendar modals.
- **CardDAV Address Book:** Personal contacts management and lookups.
- **Meme / Photo Editor:** Consumer canvas image manipulation tools.
- **Cloud OAuth Logins:** Device-flow logins to OpenAI, Microsoft Copilot, and Claude cloud subscriptions.

---

## 5. How to Run & Quick Start

**GitHub Repository:** [https://github.com/Vinayak0928/odin.git](https://github.com/Vinayak0928/odin.git)

### 5.1 Prerequisites
- **Operating System:** Linux (Ubuntu 20.04+ / RHEL 8+), Windows 10/11, or macOS (Apple Silicon / Intel).
- **Python:** Python 3.10 or 3.11+ installed.
- **Git:** Installed and available in PATH.
- **Local LLM Engine:** [Ollama](https://ollama.com/), [vLLM](https://github.com/vllm-project/vllm), or [llama.cpp](https://github.com/ggml-org/llama.cpp) running locally.
- *(Optional)* **Hardware Acceleration:** NVIDIA GPU (CUDA 12+) or AMD GPU (ROCm) for local multimodal reasoning (Qwen2.5-VL / DeepSeek-R1).
- *(Optional)* **Docker & Docker Compose:** If running in a containerized environment.

---

### 5.2 Method 1: Local Native Run (Recommended)

#### Step 1: Clone the Repository
```bash
git clone https://github.com/Vinayak0928/odin.git
cd odin
```

#### Step 2: Create & Activate a Virtual Environment
- **On Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On Windows (Command Prompt):**
  ```cmd
  python -m venv venv
  venv\Scripts\activate.bat
  ```

#### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Configure Environment Variables
Copy the sample environment file to `.env`:
- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```
- **Windows:**
  ```powershell
  copy .env.example .env
  ```

*(Optional)* Review `.env` to configure your preferred model endpoint and admin credentials:
```ini
# Primary local inference server (Ollama default)
LLM_HOST=localhost
OLLAMA_BASE_URL=http://localhost:11434/v1

# Optional: Seed initial admin credentials
ODYSSEUS_ADMIN_USER=admin
ODYSSEUS_ADMIN_PASSWORD=your_secure_password_here
```

#### Step 5: Initialize Application & Admin User
Run the setup script to create the local data directory, initialize SQLite tables, and set up your initial admin user:
```bash
python setup.py
```
> **Note:** If `ODYSSEUS_ADMIN_PASSWORD` is not set in `.env`, the script will prompt you to enter a password or generate a secure temporary password.

#### Step 6: Start Local Open-Weight LLMs (Ollama)
Ensure your local inference server is running and pull the models you wish to use:
```bash
# Vision & P&ID Drawing Inspection
ollama pull qwen2.5-vl

# Industrial Reasoning & Turnaround Planning
ollama pull deepseek-r1
```

#### Step 7: Launch the Application
Start the FastAPI server:
```bash
python app.py
```
*(Alternatively, run using Uvicorn directly)*:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 7000 --reload
```

#### Platform 1-Click Launchers
- **Windows:** Run the automated native launcher:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1
  ```
- **macOS:** Run the native launcher script:
  ```bash
  chmod +x ./start-macos.sh
  ./start-macos.sh
  ```

#### Step 8: Access the Web UI
Open your web browser and navigate to:
```
http://127.0.0.1:7000
```
Log in using your admin credentials created in Step 5.

---

### 5.3 Method 2: Running with Docker & Docker Compose

For containerized deployment, Docker Compose profiles are provided:

#### 1. Standard / CPU Deployment
```bash
# Clone and enter directory
git clone https://github.com/Vinayak0928/odin.git
cd odin

# Setup environment file
cp .env.example .env

# Build and start services
docker compose up -d --build
```

#### 2. NVIDIA GPU Acceleration
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu-nvidia.yml up -d --build
```

#### 3. AMD ROCm GPU Acceleration
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu-amd.yml up -d --build
```

#### Stopping Docker Containers
```bash
docker compose down
```

Access the application at `http://127.0.0.1:7000`.

---

### 5.4 Running Automated Verification Tests

Verify the sovereign modules, calculation engines, and cryptographic Merkle audit integrity:

```bash
# 1. Verify API 510/570, Pumps, Exchangers, TBP Crude Blending & OISD-105 Turnaround
python -m unittest tests/test_industrial_calc.py

# 2. Verify Cryptographic Merkle DAG Audit Trail
python -m unittest tests/test_audit_merkle.py
python -m unittest tests/test_audit_routes.py

# 3. Verify P&ID Drawing ISA-5.1 Inspector
python -m unittest tests/test_pid_inspector.py

# 4. Verify Departmental Industrial RBAC
python -m unittest tests/test_industrial_rbac.py

# Run all test suites
python -m unittest discover -s tests
```

---

## 6. Regulatory References
- **API 510:** Pressure Vessel Inspection Code: In-service Inspection, Rating, Repair, and Alteration
- **API 570:** Piping Inspection Code: In-service Inspection, Rating, Repair, and Alteration of Piping Systems
- **API 610 / ISO 13709:** Centrifugal Pumps for Petroleum, Petrochemical and Natural Gas Industries
- **ASME BPVC Section VIII Division 1:** Rules for Construction of Pressure Vessels
- **ASME B31.3:** Process Piping Design Code
- **OISD-STD-105:** Work Permit System for Petroleum Refineries & Oil/Gas Installations
- **ISA-5.1:** Instrumentation Symbols and Identification Standard

---
**SIH26117 — Mangalore Refinery and Petrochemicals Limited (MRPL)**  
*Sovereign On-Premise Agentic AI Workbench for Confidential Industrial Operations*
