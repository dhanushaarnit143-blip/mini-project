import React, { useState } from 'react';
import {
  computeSleepScore,
  SLEEP_LABELS,
  MOVEMENT_RESPONSES,
  QUESTIONNAIRE_VERSION,
} from './sleepScorer.js';
import { SleepSessionModel } from './sleepSessionModel.js';

/**
 * MPF Mobile Extension — Daily Sleep & RBD Questionnaire Screen (Phase 8)
 *
 * A concise (3-5 question) daily sleep assessment capturing subjective sleep
 * duration, quality, dream-enacting movements (prodromal RBD survey), and
 * optional medication alterations.
 *
 * STRICT RESEARCH COMPLIANCE:
 * - "Self-reported sleep behavior" & "Questionnaire-based indicator"
 * - NOT equivalent to polysomnography or clinical diagnosis.
 * - Zero diagnostic language.
 */
export function SleepQuestionnaireScreen({
  participantId = '00000000-0000-0000-0000-000000000001',
  supabaseClient = null,
  onComplete = () => {},
  showWeeklyMedication = true,
}) {
  // Questionnaire responses state
  const [sleepDuration, setSleepDuration] = useState(7.5);
  const [sleepQuality, setSleepQuality] = useState(4);
  const [movementResponse, setMovementResponse] = useState(MOVEMENT_RESPONSES.NO);
  const [daytimeSleepiness, setDaytimeSleepiness] = useState(1);
  const [medicationChange, setMedicationChange] = useState(null);
  const [medicationDetails, setMedicationDetails] = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const QUALITY_LABELS = {
    1: '1 - Very Poor',
    2: '2 - Poor',
    3: '3 - Fair',
    4: '4 - Good',
    5: '5 - Excellent',
  };

  const SLEEPINESS_LABELS = {
    1: '1 - Not at all',
    2: '2 - Slightly',
    3: '3 - Moderately',
    4: '4 - Very',
    5: '5 - Extremely',
  };

  const handleDurationChange = (e) => {
    const val = parseFloat(e.target.value);
    if (!isNaN(val)) {
      setSleepDuration(Math.max(0, Math.min(14, val)));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const session = SleepSessionModel.fromQuestionnaire({
        participantId,
        sleepDuration,
        sleepQuality,
        movementResponse,
        daytimeSleepiness,
        medicationChange,
        medicationDetails: medicationChange ? medicationDetails : null,
      });

      let syncSuccess = false;
      let syncError = null;

      if (supabaseClient) {
        const syncRes = await session.syncToSupabase(supabaseClient);
        syncSuccess = syncRes.success;
        syncError = syncRes.error;
      }

      const scoreData = computeSleepScore({
        sleepDuration,
        sleepQuality,
        unusualMovement: movementResponse,
        daytimeSleepiness,
      });

      const outcome = {
        session,
        scoreData,
        syncSuccess,
        syncError,
      };

      setResult(outcome);
      onComplete(outcome);
    } catch (err) {
      setErrorMsg(err.message || 'An error occurred during submission.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setErrorMsg(null);
    setSleepDuration(7.5);
    setSleepQuality(4);
    setMovementResponse(MOVEMENT_RESPONSES.NO);
    setDaytimeSleepiness(1);
    setMedicationChange(null);
    setMedicationDetails('');
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.badge}>DAILY PROTOCOL • PHASE 8</div>
        <h2 style={styles.title}>Daily Sleep Questionnaire</h2>
        <p style={styles.subtitle}>
          Short 4-question check-in to track subjective sleep patterns and baseline variation.
        </p>
        <div style={styles.disclaimerBanner}>
          <span style={styles.infoIcon}>ℹ️</span>
          <span>
            <strong>Research Screening Indicator:</strong> Self-reported data only.
            Not equivalent to polysomnography or clinical diagnostic evaluation.
          </span>
        </div>
      </div>

      {errorMsg && (
        <div style={styles.errorBox}>
          <strong>Notice:</strong> {errorMsg}
        </div>
      )}

      {/* Completion View */}
      {result ? (
        <div style={styles.resultCard}>
          <div style={styles.scoreCircle}>
            <span style={styles.scoreValue}>{result.scoreData.score}</span>
            <span style={styles.scoreMax}>/ 100</span>
          </div>

          <h3 style={styles.resultHeading}>Sleep Score Calculated</h3>
          <p style={styles.resultProvenance}>
            Category: <strong>{SLEEP_LABELS.PROVENANCE}</strong>
          </p>

          <div style={styles.breakdownGrid}>
            <div style={styles.breakdownItem}>
              <span style={styles.breakdownLabel}>Duration Subscore</span>
              <span style={styles.breakdownVal}>{result.scoreData.breakdown.duration_score} / 30</span>
            </div>
            <div style={styles.breakdownItem}>
              <span style={styles.breakdownLabel}>Quality Subscore</span>
              <span style={styles.breakdownVal}>{result.scoreData.breakdown.quality_score} / 30</span>
            </div>
            <div style={styles.breakdownItem}>
              <span style={styles.breakdownLabel}>Movement Subscore</span>
              <span style={styles.breakdownVal}>{result.scoreData.breakdown.movement_score} / 25</span>
            </div>
            <div style={styles.breakdownItem}>
              <span style={styles.breakdownLabel}>Alertness Subscore</span>
              <span style={styles.breakdownVal}>{result.scoreData.breakdown.sleepiness_score} / 15</span>
            </div>
          </div>

          {movementResponse === MOVEMENT_RESPONSES.YES && (
            <div style={styles.movementNotice}>
              <strong>Note:</strong> Unusual dream-enacting movements or sleep vocalizations were self-reported.
              Consistent reports over multiple days will be monitored as:
              <div style={styles.flagLabel}>"{SLEEP_LABELS.MOVEMENT_NOTED}"</div>
            </div>
          )}

          <div style={styles.disclaimerText}>
            {SLEEP_LABELS.RESEARCH_DISCLAIMER}. Your measurements will be compared against your personal 14-day baseline.
          </div>

          <button onClick={handleReset} style={styles.secondaryButton}>
            Record Another Entry
          </button>
        </div>
      ) : (
        /* Form View */
        <form onSubmit={handleSubmit} style={styles.form}>
          {/* Q1: Sleep Duration */}
          <div style={styles.questionCard}>
            <label style={styles.questionLabel}>
              <span style={styles.qNumber}>Q1</span>
              How many hours did you sleep last night?
            </label>
            <div style={styles.durationInputWrapper}>
              <input
                type="range"
                min="0"
                max="14"
                step="0.5"
                value={sleepDuration}
                onChange={handleDurationChange}
                style={styles.slider}
              />
              <div style={styles.durationDisplay}>
                <span style={styles.durationNumber}>{sleepDuration}</span>
                <span style={styles.durationUnit}>hours</span>
              </div>
            </div>
            <div style={styles.rangeLabels}>
              <span>0h</span>
              <span>7-9h (Typical)</span>
              <span>14h</span>
            </div>
          </div>

          {/* Q2: Sleep Quality */}
          <div style={styles.questionCard}>
            <label style={styles.questionLabel}>
              <span style={styles.qNumber}>Q2</span>
              How would you rate your sleep quality?
            </label>
            <div style={styles.optionButtonGroup}>
              {[1, 2, 3, 4, 5].map((level) => (
                <button
                  type="button"
                  key={level}
                  onClick={() => setSleepQuality(level)}
                  style={{
                    ...styles.qualityButton,
                    ...(sleepQuality === level ? styles.qualityButtonActive : {}),
                  }}
                >
                  <span style={styles.qualityStar}>{'★'.repeat(level)}</span>
                  <span>{QUALITY_LABELS[level]}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Q3: Unusual Movements / Dream Enactment */}
          <div style={styles.questionCard}>
            <label style={styles.questionLabel}>
              <span style={styles.qNumber}>Q3</span>
              Did you or your bed partner notice any unusual movements, talking, shouting, or acting out dreams during sleep last night?
            </label>
            <div style={styles.radioGroup}>
              {[
                { value: MOVEMENT_RESPONSES.NO, label: 'No' },
                { value: MOVEMENT_RESPONSES.YES, label: 'Yes' },
                { value: MOVEMENT_RESPONSES.NOT_SURE, label: 'Not sure' },
                { value: MOVEMENT_RESPONSES.DONT_KNOW, label: "I don't know" },
              ].map((opt) => (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => setMovementResponse(opt.value)}
                  style={{
                    ...styles.choiceButton,
                    ...(movementResponse === opt.value ? styles.choiceButtonActive : {}),
                  }}
                >
                  <span style={styles.radioCircle}>
                    {movementResponse === opt.value ? '●' : '○'}
                  </span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
            <p style={styles.questionHint}>
              * Screens for self-reported dream enactments. Does NOT provide a clinical diagnosis of RBD.
            </p>
          </div>

          {/* Q4: Daytime Sleepiness */}
          <div style={styles.questionCard}>
            <label style={styles.questionLabel}>
              <span style={styles.qNumber}>Q4</span>
              How sleepy do you feel during the day?
            </label>
            <div style={styles.optionButtonGroup}>
              {[1, 2, 3, 4, 5].map((level) => (
                <button
                  type="button"
                  key={level}
                  onClick={() => setDaytimeSleepiness(level)}
                  style={{
                    ...styles.qualityButton,
                    ...(daytimeSleepiness === level ? styles.qualityButtonActive : {}),
                  }}
                >
                  <span>{SLEEPINESS_LABELS[level]}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Q5: Optional Weekly Medication Change */}
          {showWeeklyMedication && (
            <div style={styles.questionCard}>
              <div style={styles.optionalHeader}>
                <label style={styles.questionLabel}>
                  <span style={styles.qNumber}>Q5</span>
                  Have there been any changes to your medication this week?
                </label>
                <span style={styles.optionalTag}>Optional Weekly</span>
              </div>
              <div style={styles.medToggleGroup}>
                <button
                  type="button"
                  onClick={() => setMedicationChange(false)}
                  style={{
                    ...styles.choiceButtonSmall,
                    ...(medicationChange === false ? styles.choiceButtonActive : {}),
                  }}
                >
                  No changes
                </button>
                <button
                  type="button"
                  onClick={() => setMedicationChange(true)}
                  style={{
                    ...styles.choiceButtonSmall,
                    ...(medicationChange === true ? styles.choiceButtonActive : {}),
                  }}
                >
                  Yes, changes occurred
                </button>
                <button
                  type="button"
                  onClick={() => setMedicationChange(null)}
                  style={{
                    ...styles.choiceButtonSmall,
                    ...(medicationChange === null ? styles.choiceButtonActive : {}),
                  }}
                >
                  Prefer not to say
                </button>
              </div>

              {medicationChange === true && (
                <div style={styles.medDetailsWrapper}>
                  <label style={styles.subLabel}>Optional Details (e.g. dosage adjustment):</label>
                  <textarea
                    rows={2}
                    value={medicationDetails}
                    onChange={(e) => setMedicationDetails(e.target.value)}
                    placeholder="Describe changes if comfortable (no specific drug names required)..."
                    style={styles.textarea}
                  />
                </div>
              )}
            </div>
          )}

          {/* Submit Action */}
          <div style={styles.actionContainer}>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                ...styles.primaryButton,
                ...(isSubmitting ? styles.buttonDisabled : {}),
              }}
            >
              {isSubmitting ? 'Recording Entry...' : 'Complete Daily Sleep Log'}
            </button>
          </div>
        </form>
      )}

      {/* Footer Info */}
      <div style={styles.footer}>
        <span>Protocol Version: {QUESTIONNAIRE_VERSION}</span>
        <span>•</span>
        <span>Baseline Centric Tracking</span>
      </div>
    </div>
  );
}

// ── Styles (Rich Dark Theme) ──────────────────────────────────────────────────
const styles = {
  container: {
    maxWidth: '580px',
    margin: '0 auto',
    padding: '24px 16px',
    backgroundColor: '#0d1117',
    color: '#e6edf3',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    borderRadius: '16px',
    minHeight: '100vh',
    boxSizing: 'border-box',
  },
  header: {
    marginBottom: '24px',
    textAlign: 'center',
  },
  badge: {
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: '700',
    letterSpacing: '1px',
    padding: '4px 10px',
    borderRadius: '20px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    marginBottom: '10px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#f0f6fc',
    margin: '0 0 8px 0',
  },
  subtitle: {
    fontSize: '14px',
    color: '#8b949e',
    margin: '0 0 16px 0',
    lineHeight: 1.5,
  },
  disclaimerBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#c9d1d9',
    lineHeight: 1.4,
    textAlign: 'left',
  },
  infoIcon: {
    fontSize: '16px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  questionCard: {
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '12px',
    padding: '18px',
  },
  questionLabel: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    fontSize: '15px',
    fontWeight: '600',
    color: '#f0f6fc',
    marginBottom: '16px',
    lineHeight: 1.4,
  },
  qNumber: {
    backgroundColor: '#21262d',
    color: '#58a6ff',
    fontSize: '12px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '6px',
    flexShrink: 0,
  },
  durationInputWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '8px',
  },
  slider: {
    flex: 1,
    accentColor: '#38bdf8',
    height: '6px',
    cursor: 'pointer',
  },
  durationDisplay: {
    backgroundColor: '#21262d',
    padding: '8px 14px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'baseline',
    gap: '4px',
    minWidth: '90px',
    justifyContent: 'center',
    border: '1px solid #30363d',
  },
  durationNumber: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#38bdf8',
  },
  durationUnit: {
    fontSize: '12px',
    color: '#8b949e',
  },
  rangeLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    color: '#8b949e',
  },
  optionButtonGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  qualityButton: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 14px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '8px',
    color: '#c9d1d9',
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  qualityButtonActive: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    fontWeight: '600',
  },
  qualityStar: {
    color: '#e3b341',
    letterSpacing: '2px',
    fontSize: '12px',
  },
  radioGroup: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
  },
  choiceButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '8px',
    color: '#c9d1d9',
    fontSize: '13px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  choiceButtonActive: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    fontWeight: '600',
  },
  radioCircle: {
    fontSize: '14px',
  },
  questionHint: {
    fontSize: '11px',
    color: '#8b949e',
    margin: '10px 0 0 0',
    fontStyle: 'italic',
  },
  optionalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  optionalTag: {
    fontSize: '10px',
    textTransform: 'uppercase',
    padding: '3px 8px',
    borderRadius: '12px',
    backgroundColor: '#21262d',
    color: '#8b949e',
    letterSpacing: '0.5px',
  },
  medToggleGroup: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  choiceButtonSmall: {
    flex: '1 1 auto',
    padding: '8px 12px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '8px',
    color: '#c9d1d9',
    fontSize: '12px',
    cursor: 'pointer',
  },
  medDetailsWrapper: {
    marginTop: '12px',
  },
  subLabel: {
    display: 'block',
    fontSize: '12px',
    color: '#8b949e',
    marginBottom: '6px',
  },
  textarea: {
    width: '100%',
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '10px',
    color: '#f0f6fc',
    fontSize: '13px',
    resize: 'vertical',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
  },
  actionContainer: {
    marginTop: '10px',
  },
  primaryButton: {
    width: '100%',
    padding: '14px',
    backgroundColor: '#238636',
    border: 'none',
    borderRadius: '10px',
    color: '#ffffff',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  resultCard: {
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '14px',
    padding: '28px 20px',
    textAlign: 'center',
  },
  scoreCircle: {
    width: '110px',
    height: '110px',
    borderRadius: '50%',
    border: '4px solid #38bdf8',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    margin: '0 auto 16px auto',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
  },
  scoreValue: {
    fontSize: '32px',
    fontWeight: '800',
    color: '#f0f6fc',
    lineHeight: 1,
  },
  scoreMax: {
    fontSize: '12px',
    color: '#8b949e',
    marginTop: '2px',
  },
  resultHeading: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#f0f6fc',
    margin: '0 0 6px 0',
  },
  resultProvenance: {
    fontSize: '13px',
    color: '#8b949e',
    margin: '0 0 20px 0',
  },
  breakdownGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
    marginBottom: '20px',
    textAlign: 'left',
  },
  breakdownItem: {
    backgroundColor: '#0d1117',
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #21262d',
  },
  breakdownLabel: {
    display: 'block',
    fontSize: '11px',
    color: '#8b949e',
    marginBottom: '4px',
  },
  breakdownVal: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#58a6ff',
  },
  movementNotice: {
    backgroundColor: 'rgba(234, 179, 8, 0.12)',
    border: '1px solid rgba(234, 179, 8, 0.4)',
    borderRadius: '8px',
    padding: '12px',
    fontSize: '12px',
    color: '#fde047',
    lineHeight: 1.4,
    marginBottom: '18px',
    textAlign: 'left',
  },
  flagLabel: {
    marginTop: '4px',
    fontWeight: '700',
    color: '#fef08a',
  },
  disclaimerText: {
    fontSize: '11px',
    color: '#8b949e',
    lineHeight: 1.4,
    marginBottom: '20px',
  },
  secondaryButton: {
    padding: '10px 18px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    borderRadius: '8px',
    color: '#c9d1d9',
    fontSize: '13px',
    cursor: 'pointer',
  },
  errorBox: {
    backgroundColor: 'rgba(248, 81, 73, 0.15)',
    border: '1px solid #f85149',
    color: '#ff7b72',
    padding: '12px',
    borderRadius: '8px',
    fontSize: '13px',
    marginBottom: '16px',
  },
  footer: {
    marginTop: '24px',
    display: 'flex',
    justifyContent: 'center',
    gap: '8px',
    fontSize: '11px',
    color: '#484f58',
  },
};
