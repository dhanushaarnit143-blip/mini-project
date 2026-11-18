# MPF-PD Evaluation Panel & Guide FAQ

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Document Purpose:** Direct, authoritative, and scientifically rigorous answers to questions frequently asked by project guides, academic supervisors, and evaluation panels.

---

### Q1: How is this different from existing Parkinson's detection systems?
**Answer:**  
Existing computer-aided Parkinson's systems predominantly suffer from two key limitations:
1. **Targeting Manifest, Post-Diagnosis Disease:** Most literature classifies patients who already have clinical motor Parkinson's (e.g. comparing advanced Hoehn & Yahr stage 2/3 patients against healthy controls using gait or voice). By that stage, over 60% of dopaminergic neurons are permanently lost.
2. **Narrow Modality Combinations:** The vast majority of published models combine only voice and gait, or focus on a single sensor.

**Our Difference:**  
MPF-PD targets the **prodromal stage** (years before motor diagnosis) by fusing **retinal microvascular biomarkers** with **prodromal non-motor markers** (olfactory testing and REM sleep behavior disorder) and digital motor/voice signals into a single unified architecture. Furthermore, we design specifically for **non-specialist, distributed deployment**—allowing primary care clinics, community optometry practices, and smartphones to act as an accessible screening funnel.

---

### Q2: Can this system actually diagnose Parkinson's disease?
**Answer:**  
**Emphatically, no.** MPF-PD is an **investigational research prototype for risk pattern estimation**, not a medical diagnostic device. 

In clinical neurology, a diagnosis of Parkinson's disease can only be established by a qualified movement disorder specialist following formal criteria (such as the MDS Clinical Diagnostic Criteria), which require neurological examination, exclusion of atypical parkinsonisms, and evaluation of levodopa responsiveness. Our tool provides a calibrated, non-diagnostic risk signal indicating whether a participant exhibits a multimodal constellation of symptoms warranting specialist referral.

---

### Q3: What datasets did you use, and is same-participant multimodal data available?
**Answer:**  
We utilized public retrospective datasets cataloged by modality:
- **Olfactory & Sleep (RBD):** Clinical protocols and feature distributions derived from the **PPMI** (Parkinson's Progression Markers Initiative) prodromal cohort.
- **Voice:** The **UCI Parkinson's Telemonitoring Dataset** for sustained phonation acoustic features.
- **Motor / Gait:** The **PhysioNet Gait in Parkinson's Disease** dataset (vertical ground reaction force recordings).
- **Retina:** Public fundus datasets (**DRIVE**, **STARE**, **EyePACS**) for pretraining vessel segmentation and topological morphometry.

**Important Data Reality Notice:**  
Truly synchronized, same-participant public datasets containing all five modalities (retinal imaging, voice recordings, sensor gait, olfactory scratch cards, and sleep questionnaires) from the same individuals do not exist in unrestricted open-access repositories due to privacy regulations and data governance. Therefore, our active fusion experiment runs on an **aligned synthetic clinical fixture (`Category E`)** calibrated to published clinical distributions. It evaluates **software pipeline correctness, attention gating dynamics, and architectural feasibility**, but does not constitute clinical validation.

---

### Q4: Why did you choose XGBoost over a deep neural network for the final classifier?
**Answer:**  
We chose XGBoost as the final decision layer following the neural gated fusion encoder for four specific reasons:
1. **Sample Efficiency on Tabular Biomedical Data:** Tree-based gradient boosting consistently matches or outperforms deep neural networks on tabular and structured physiological features when sample sizes are moderate.
2. **Probability Calibration:** XGBoost, coupled with sigmoid/logistic objectives, produces well-calibrated posterior probabilities (evidenced by our Brier score of 0.0031).
3. **Robustness to Extreme Values:** Decision trees are invariant to monotonic feature scaling and handle outlier physiological readings gracefully without exploding gradients.
4. **Exact Shapley Explainability:** XGBoost natively supports exact polynomial-time SHAP computations (`TreeExplainer`), guaranteeing consistent, non-approximate feature attributions for clinical interpretability.

*Note:* Deep learning is still utilized where appropriate—namely, a PyTorch U-Net for retinal vessel segmentation and a PyTorch neural attention network for the gated fusion layer.

---

### Q5: How does the system handle missing modalities? Does it penalize the participant?
**Answer:**  
The system uses a **Dynamic Neural Attention Gating mechanism with presence masking**:
- Each modality's feature embedding is accompanied by a binary presence flag $m_i \in \{0, 1\}$.
- When an input modality is omitted (e.g. a participant does not have access to a retinal camera or voice recorder), its presence flag is set to $0$.
- The gating network calculates raw attention scores, applies the presence mask, and re-normalizes attention weights across the *active* modalities using a masked softmax function:
  $$\alpha_i = \frac{m_i \cdot \exp(g_i)}{\sum_{j=1}^M m_j \cdot \exp(g_j) + \epsilon}$$
- Missing features are replaced by neutral baseline imputations that are zeroed out by the gate.
- Consequently, a participant's risk score is calculated **exclusively from their available data**. The system exhibits graceful degradation down to a single modality, though our validation recommends a minimum of 2 active modalities for high confidence.

---

### Q6: What is the retinal component actually doing? Can a smartphone front camera capture retinal images?
**Answer:**  
The retinal modality analyzes **fundus photography** captured by standard ophthalmic fundus cameras (such as those routinely used during annual diabetic eye screenings or standard optometry exams). 

**The Pipeline:**
1. Preprocesses the fundus image (green-channel contrast enhancement, CLAHE).
2. Uses a PyTorch U-Net to segment the retinal microvasculature.
3. Computes quantitative morphometric parameters: vessel area density, fractal branching dimension ($D_f$), average vessel tortuosity, and foveal avascular zone (FAZ) contour.
4. Extracts a 16-dimensional CNN latent spatial embedding.

**Critical Clarification:**  
A smartphone front camera **CANNOT** capture retinal fundus images. In our mobile extension, the smartphone front camera is used strictly for **visual psychomotor reaction time and saccadic latency tasks**, never for retinal imaging. Retinal images must originate from clinical fundus photography.

---

### Q7: How do you ensure patient data privacy and ethical compliance?
**Answer:**  
MPF-PD implements a defense-in-depth privacy architecture:
1. **Zero Raw Audio / Image Retention on Backend:** In the FastAPI service, uploaded voice audio files and retinal images are processed in volatile temporary memory (`tempfile.mkdtemp`) and **scrubbed immediately upon feature extraction**, in a mandatory `finally` execution block.
2. **Pseudonymous Participant Identifiers:** No personally identifiable information (PII) such as names, social security numbers, or addresses is ingested; participants are assigned random UUIDs.
3. **Database Security (Supabase):** Row-Level Security (RLS) policies restrict participant data access exclusively to authenticated owners.
4. **Consent & Revocation Flow:** The database schema (`006_data_retention.sql`) supports immediate consent revocation, executing automated purge routines that permanently delete all associated sensor features upon request.

---

### Q8: What would be required to move this system toward real clinical deployment?
**Answer:**  
Transitioning from a research prototype to a clinical medical device requires several mandatory milestones:
1. **Prospective Clinical Trial:** An IRB-approved prospective study evaluating diverse prodromal participants over a 5+ year longitudinal period to track actual motor phenoconversion.
2. **Regulatory Clearance:** Certification as Software as a Medical Device (SaMD) under FDA 510(k) / De Novo pathways in the US or CE-mark under EU MDR (Class IIa or IIb).
3. **Demographic & Multi-Center Calibration:** Testing across multi-ethnic cohorts to account for variations in retinal fundus pigmentation, vocal acoustics across accents, and gait across footwear.
4. **Clinical Workflow Integration:** Direct FHIR / HL7 interface integration with hospital Electronic Health Record (EHR) systems.
5. **Specialist Oversight:** Structuring the software as a triaging aid that requires review by a board-certified neurologist before any clinical action is taken.

---

### Q9: What is the mobile extension, and does it retrain the core machine learning models?
**Answer:**  
The mobile extension is a **longitudinal digital biomarker collection module** designed for daily at-home monitoring (capturing keystroke dynamics, tap intervals, vocal stability, and sleep regularity).

**Crucially, the mobile extension does NOT retrain or fine-tune the core MPF model.**  
Instead, it utilizes a dedicated **`MPFAdapter`** (`src/mobile/mpf_adapter.py`):
- Daily mobile sensor features are aggregated over rolling 7-day or 14-day windows.
- The adapter normalizes these longitudinal metrics against the participant's own 14-day baseline.
- It transforms the aggregated features into the standardized input vector expected by the frozen, pre-trained MPF multimodal pipeline.
- This decoupling ensures that model behavior remains strictly audited, deterministic, and free from catastrophic forgetting or drift.

---

### Q10: What are the three biggest limitations of the current implementation?
**Answer:**  
1. **Absence of Prospective Clinical Validation:** The system has been validated on retrospective public datasets and synthetic fixtures, but not on prospective human patients entering clinical practices.
2. **Lack of Synchronized Multimodal Datasets:** Due to data sharing restrictions, public datasets do not provide synchronized 5-modality measurements from the same individuals, requiring reliance on aligned simulation fixtures for fusion validation.
3. **Non-PD Retinal Pretraining:** Open fundus datasets (e.g. DRIVE, EyePACS) are annotated for diabetic retinopathy, not idiopathic Parkinson's disease. Retinal embeddings capture microvascular morphology, but their specificity for Parkinson's requires dedicated clinical validation.

---

### Q11: How do you address demographic bias and age adjustment?
**Answer:**  
- **Olfactory:** Olfactory sensitivity naturally declines with normal aging (presbyosmia) and varies between biological sexes. Our olfactory pipeline maps raw UPSIT scores to age- and sex-stratified normative percentile tables derived from established clinical literature (Doty et al.), ensuring an 80-year-old is not flagged as hyposmic based on a 25-year-old's benchmark.
- **Demographic Inputs:** Participant age and sex are directly provided to the model preprocessor.
- **Future Validation:** We explicitly list demographic calibration across diverse racial and ethnic populations as an essential prerequisite prior to any real-world deployment.

---

### Q12: How is class imbalance handled during model training?
**Answer:**  
Prodromal Parkinson's is a low-prevalence condition in the general population (~1–2% over age 65). During training:
- We utilize **Stratified K-Fold cross-validation** ($k=5$) to preserve minority class ratios across splits.
- In tree-based models (XGBoost), we tune `scale_pos_weight` to counter class imbalance.
- We evaluate performance using **F1-score, Precision-Recall curves, and Brier calibration scores** rather than relying on raw classification accuracy, which can be misleading in imbalanced settings.

---
*End of Panel FAQ Document.*
