# MPF-PD Live Demonstration Script & Protocol

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Document Purpose:** Exact click-by-click instructions, script prompts, test data values, and talking points for conducting an error-free live demonstration before an evaluation committee or project guide.  
**Demonstration Length:** 5 to 7 minutes.  
**Mandatory Setup Status:** FastAPI backend running on port `8000`, React frontend running on port `5173`.

---

## Pre-Demo Checklist (Do 5 Minutes Before Presentation)

1. **Terminal 1 (Backend API):**
   ```bash
   # From project root with venv active
   uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *Verify:* Visit `http://localhost:8000/api/health` in browser — ensure `"status": "ok"` and all 7 models return `true`.

2. **Terminal 2 (Frontend Dashboard):**
   ```bash
   cd dashboard/frontend
   npm run dev
   ```
   *Verify:* Visit `http://localhost:5173` — ensure the React UI loads smoothly without console errors.

3. **Browser Setup:**
   - Open Chrome or Edge to `http://localhost:5173`.
   - Set zoom level to 100% or 90% so all panels and charts fit comfortably on screen.
   - Have a sample audio `.wav` file ready in your Downloads folder (or use synthetic voice entry).

---

## Live Demo Walkthrough (Step-by-Step)

### Phase 1: Context & Disclaimer (30 Seconds)

**Action:** Display the dashboard home screen. Point your cursor to the yellow warning banner at the top of the screen.

**Presenter Talking Points:**
> *"Before I begin, I want to highlight the prominent research disclaimer displayed at the top of the interface. MPF-PD is an **investigational research prototype for multimodal risk pattern estimation**. It is **not a diagnostic medical device**. Its purpose is to explore how non-specialist community screenings—such as optometry fundus photography, smell tests, and mobile tasks—can identify early risk patterns years before motor disability occurs."*

---

### Phase 2: Scenario 1 — Elevated Risk Prodromal Profile with Missing Modality (3 Minutes)

**Demonstration Goal:** Show how the system handles a realistic prodromal participant with partial, incomplete data (missing retinal camera) and produces a calibrated, explainable risk score.

#### Step 1: Input Participant Demographics
- **Action:** In the left panel under **"Participant Profile"**:
  - Participant ID: `PROD-2026-081`
  - Age: `68`
  - Biological Sex: Select `Male`

**Talking Point:**
> *"We provide participant demographics. Age and biological sex are critical because our olfactory module adjusts for physiological age-related decline (presbyosmia). An abnormal score for a 40-year-old is not judged by the same threshold as a 70-year-old."*

#### Step 2: Input Olfactory (Smell Test) Data
- **Action:** Under **"Olfactory Assessment (UPSIT)"**:
  - Toggle: `Available / Present`
  - Total Score: Enter `18` (out of 40)

**Talking Point:**
> *"The University of Pennsylvania Smell Identification Test (UPSIT) has a normal benchmark of greater than 34. A score of 18 represents pronounced hyposmia, one of the earliest prodromal hallmarks of synucleinopathy."*

#### Step 3: Input Sleep / RBD Screening Data
- **Action:** Under **"RBD Screening Questionnaire (RBDSQ)"**:
  - Toggle: `Available / Present`
  - Check the boxes for:
    - *Item 1: Vivid, action-packed dreams*
    - *Item 2: Aggressive dream content*
    - *Item 5: Nocturnal limb jerking/movements*
    - *Item 10: Awakening self or bed partner through vocalization/thrashing*
  - Total Score: Shows `7` (cut-off is $\ge 5$).

**Talking Point:**
> *"REM Sleep Behavior Disorder involves loss of normal muscle atonia during REM sleep. When a participant scores 5 or higher on the RBDSQ, longitudinal studies show a high rate of phenoconversion to Parkinsonian disorders over 10 to 12 years."*

#### Step 4: Digital Voice & Motor Inputs
- **Action:** Under **"Voice Phonation"**:
  - Toggle: `Available`
  - Choose sample voice file (or enter Jitter: `0.021`, Shimmer: `0.048`, HNR: `14.2 dB`).
- **Action:** Under **"Motor / Gait Dynamics"**:
  - Toggle: `Available`
  - Enter Cadence: `96.4 steps/min` (slightly reduced from normal ~112).

#### Step 5: Deliberately Leave Retinal Modality Missing
- **Action:** Under **"Retinal Fundus Image"**:
  - Toggle: **Uncheck / Mark as Missing**

**Talking Point:**
> *"Notice that I have deliberately marked the retinal image as missing. In community screenings, a patient might visit a clinic that lacks a fundus camera. In typical machine learning pipelines, missing an input crashes the model or introduces severe imputation bias. Watch how our gated architecture handles this."*

#### Step 6: Execute Multimodal Inference
- **Action:** Click the large blue button: **"Run Risk Pattern Analysis"**.
- *(The button shows a brief loading spinner for ~400ms, then renders the results panel).*

---

### Phase 3: Interpreting Results & Explainability (2 Minutes)

#### Component 1: Calibrated Risk Gauge
- **Action:** Point to the circular risk meter at the top of the results panel.
- **Observed Result:** Risk Score: `0.84` | Badge: `Elevated Risk Pattern`.

**Talking Point:**
> *"The system estimates a calibrated risk score of 0.84, categorized as an 'Elevated Risk Pattern'. Notice the phrasing: we state 'Elevated Risk Pattern', never 'Parkinson's Detected', because this is a decision-support indicator."*

#### Component 2: Attention Gate Weights
- **Action:** Point to the horizontal Recharts bar chart titled **"Neural Gating Allocations"**.
- **Observed Result:** 
  - Olfactory Gate: `~38%`
  - RBD Gate: `~34%`
  - Voice Gate: `~16%`
  - Motor Gate: `~12%`
  - Retinal Gate: `0.0% (Masked)`

**Talking Point:**
> *"Here is our gated fusion in action: the retinal presence flag was zero, so the network masked its gate to 0.0% and automatically re-normalized the remaining 100% of attention across the available olfactory, sleep, voice, and motor signals. The participant is not penalized for not having an eye scan."*

#### Component 3: Local SHAP Feature Explanations
- **Action:** Scroll down to the **"Top Risk Contributors (SHAP Values)"** chart.
- **Observed Result:**
  - Red positive bars: `UPSIT Total Score: 18 (+0.31)` and `RBDSQ Motor Score (+0.26)`.
  - Blue negative bar: `Motor Regularity Index (-0.08)`.

**Talking Point:**
> *"Black-box algorithms are unacceptable in healthcare. Using SHAP (Shapley Additive exPlanations), the model transparently explains why this score was generated: hyposmia and violent dream enactment strongly drove the risk estimate upwards, while relatively preserved gait regularity provided a modest mitigating counter-signal."*

#### Component 4: Exporting Audit Report
- **Action:** Click **"Download JSON Summary"**.
- **Action:** Show the downloaded JSON file in your browser downloads or text editor.
- **Content:** Highlight the timestamp, model version `0.8.0`, feature vector, gate weights, and the embedded `disclaimer` field.

---

### Phase 4: Scenario 2 — Healthy Low-Risk Profile (1 Minute)

**Demonstration Goal:** Prove that the model does not simply produce high risk scores by default, demonstrating specificity.

**Action:**
1. Click **"Reset Form"** or modify fields:
   - Age: `62`, Female
   - UPSIT Score: `37` (Normal / Normosmic)
   - RBDSQ Score: `1` (Normal sleep)
   - Voice: Jitter `0.0035`, Shimmer `0.012`, HNR `24.5 dB` (All within healthy acoustic ranges)
   - Motor: Cadence `114 steps/min` (Normal)
2. Click **"Run Risk Pattern Analysis"**.
3. **Observed Result:** Risk Score: `0.08` | Badge: `Low Risk Pattern`.
4. **SHAP Chart:** Shows predominantly green/blue bars demonstrating that normal olfaction and sleep significantly suppress the risk estimate.

**Talking Point:**
> *"When physiological inputs are within normal ranges, the model correctly outputs a low risk score of 0.08, confirming that the network does not suffer from positive false-alarm bias."*

---

### Phase 5: Concluding Statement to Panel (30 Seconds)

**Presenter Talking Points:**
> *"To summarize: We have shown an end-to-end working system that integrates five distinct prodromal biomarkers. We demonstrated graceful degradation under missing modalities, real-time SHAP explainability, and verifiable safety disclaimers. All of this is backed by an automated test suite of over 238 unit assertions and zero train-test data leakage.*
> 
> *Thank you. We welcome your questions."*

---
*End of Live Demonstration Protocol.*
