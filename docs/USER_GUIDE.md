# EpiSwarm Studio: User Guide & Getting Started

This guide walks you through setting up EpiSwarm Studio, configuring optional API keys, running simulations in the web application, and understanding key epidemiological terms.

---

## 1. Quickstart & API Key Setup (Windows PowerShell)

You do **NOT** need paid API keys to run EpiSwarm Studio. By default, the system runs 100% offline using deterministic rule policies or your local Ollama installation.

### Step 1: Where to Get Optional API Keys
- **Google Gemini API Key (Recommended)**:
  - Visit [Google AI Studio](https://aistudio.google.com/).
  - Click **Get API key**, sign in with your Google account, and copy your key. (Gemini has a generous free tier).
- **Free Local LLM (Ollama - Already Installed on your machine)**:
  - If you run Ollama, models like `qwen3:4b` or `llama3.2` run completely free and private on your machine.
- **TypeSafe AI Jev (Optional paid service)**:
  - Visit [TypeSafe AI](https://typesafe.ai/) if you have a developer account.

### Step 2: Configure Keys Locally
Never paste API keys into chat or share them. Configure them locally using the interactive hidden setup tool:
```powershell
python scripts/setup_keys.py
```
*Prompt instructions:*
1. Enter your Gemini API key (characters will be hidden as you type).
2. For Local LLM URL, press Enter to keep the default `http://localhost:11434`.
3. For Jev, press Enter to skip if you do not have a paid key.
4. Your settings will be safely saved to your local `.env` file (which is git-ignored).

### Step 3: Check API Status & Connectivity
Verify that your local and cloud endpoints are reachable:
```powershell
python scripts/check_apis.py
```
This prints a status table showing latency and connection health without ever revealing your secret keys.

---

## 2. Launching EpiSwarm Studio Web Dashboard

Launch the interactive web app in your browser:
```powershell
streamlit run src/episwarm/app/streamlit_app.py
```

### Step-by-Step Workflow inside the Studio

1. **Step 1: Region & Population**:
   - Select the pre-configured `example_synthetic` pack, or use the **Quick Region (L0) Builder** to create a custom city by specifying total population and hospital beds per 1,000 residents.
   - Choose your agent scale (5,000 for quick testing; 50,000 for standard analysis) and click **Build Synthetic Population**.
2. **Step 2: Disease State Graph**:
   - Inspect the disease parameters. You can select `respiratory_generic.yaml` or `influenza_generic.yaml`. Notice how latent periods, basic reproduction number ($R_0$), and hospital overflow multipliers differ.
3. **Step 3: Healthcare & Capacity**:
   - View nominal general and ICU beds across facilities.
4. **Step 4: Interventions & Scenario**:
   - Review planned policy actions (e.g. school closure from Day 15 to Day 45).
5. **Step 5: Simulation Engine**:
   - Set the simulation horizon (e.g. 45 days) and click **Execute Outbreak Simulation**. Watch the epidemic curves progress day by day.
6. **Step 6: Analysis & Equity**:
   - Examine attack rates across administrative areas.
   - Click **Compute Spatial Spread Matrix** to see the order in which areas are hit and the mean arrival delay between zones.
7. **Step 7: Policy Advisor & Optimizer**:
   - Click **Run Advisor Agent** to let the automated planner evaluate candidate measures and recommend the most effective interventions.
   - Click **Search Optimal Policy Trade-offs** to view the Optuna NSGA-II Pareto frontier.
8. **Step 8: Export Audit Report**:
   - Download a self-contained HTML audit report summarizing all findings, assumptions, and provenance.

---

## 3. Glossary of Key Concepts

- **$R_0$ (Basic Reproduction Number)**: The average number of secondary infections produced by a single infected individual in a completely susceptible population without interventions. An $R_0 > 1.0$ means the epidemic grows; $R_0 < 1.0$ means it declines.
- **Attack Rate**: The cumulative percentage of the total population that contracts the disease over the course of the simulation.
- **Structure-of-Arrays (SoA)**: A high-performance computing technique where data is stored in contiguous column arrays rather than individual Python object instances. This allows EpiSwarm to simulate 100,000 agents in under 160 MB of memory.
- **Spectral Radius ($\Upsilon(M)$)**: The dominant eigenvalue of the social contact matrix $M$. It mathematically governs the transmission rate $\beta = \frac{R_0 \cdot \gamma}{\Upsilon(M)}$ as established in Libin et al. (2020).
- **Healthcare Overflow**: When hospital admissions exceed available configured clinical resources. Patients who cannot receive care experience amplified mortality multipliers.
- **Spread Matrix**: A table showing the transmission delays between administrative areas. It tells decision-makers which neighboring areas are at immediate risk when an outbreak starts in a specific zone.
- **Pareto Frontier**: A set of optimal policies where no single goal (e.g., saving lives) can be improved without sacrificing another goal (e.g., economic disruption cost).
- **Provenance (Honesty Standards)**:
  - `user_supplied`: Directly uploaded by the user.
  - `sourced`: Backed by a verified peer-reviewed scientific citation.
  - `assumed`: A default estimated parameter listed in `ASSUMPTIONS.md`.
  - `synthetic`: Artificial fixture data for software testing only.
