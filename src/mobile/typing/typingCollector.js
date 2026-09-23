/**
 * MPF Mobile Extension — Typing Collector
 * 
 * Captures keystroke timing kinematics during a controlled phrase task.
 * 
 * STRICT PRIVACY GUARANTEE:
 * - NO character text, key labels, or key codes are ever stored.
 * - Only timestamps (ms), hold durations, inter-key intervals, and a binary correction flag are recorded.
 * - Confined strictly to the active in-app controlled phrase task.
 * - No background listening, no global keyboard hooks, no OS accessibility service abuse.
 */

export const TARGET_PHRASE = "The quick brown fox jumps over the lazy dog.";

export class TypingCollector {
  constructor() {
    this.sessionId = null;
    this.participantId = null;
    this.targetPhrase = TARGET_PHRASE;
    this.isCollecting = false;
    this.startTime = null;
    this.endTime = null;
    
    // Internal timing storage (TIMING ONLY - NO TEXT CHARACTERS)
    this.timingEvents = [];
    this.pendingPresses = new Map(); // tracks key down time by an anonymous index/identifier
    this.lastPressTimestamp = null;
    this.activeKeyCounter = 0;
  }

  /**
   * Initializes a new controlled typing session.
   * @param {string} participantId - UUID of the participant
   * @param {string} [customSessionId] - Optional client-generated UUID
   */
  startSession(participantId, customSessionId = null) {
    if (!participantId) {
      throw new Error("Participant ID is required to start a typing session.");
    }

    this.participantId = participantId;
    this.sessionId = customSessionId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : this._generateUUID());
    this.isCollecting = true;
    this.startTime = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    this.endTime = null;
    this.timingEvents = [];
    this.pendingPresses.clear();
    this.lastPressTimestamp = null;
    this.activeKeyCounter = 0;

    return {
      sessionId: this.sessionId,
      participantId: this.participantId,
      startTime: this.startTime,
      targetPhrase: this.targetPhrase
    };
  }

  /**
   * Records a key press event.
   * Extracts ONLY timing and whether the key represents a correction/backspace.
   * Discards the key character immediately.
   * @param {KeyboardEvent|Object} event - Browser or synthetic keyboard event
   * @returns {number|null} internal press handle
   */
  recordKeyDown(event) {
    if (!this.isCollecting) return null;

    const currentTimestamp = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    const isCorrection = event.key === 'Backspace' || event.key === 'Delete' || event.isCorrection === true;
    
    // Inter-key interval (ms) relative to previous press
    const interKeyInterval = this.lastPressTimestamp !== null 
      ? Math.max(0, currentTimestamp - this.lastPressTimestamp)
      : 0;

    this.lastPressTimestamp = currentTimestamp;
    const pressId = ++this.activeKeyCounter;

    this.pendingPresses.set(pressId, {
      pressTime: currentTimestamp,
      interKeyInterval,
      isCorrection: Boolean(isCorrection)
    });

    return pressId;
  }

  /**
   * Records a key release event.
   * Calculates hold duration and pushes the completed timing event.
   * @param {number|KeyboardEvent|Object} pressIdOrEvent - Press ID from keyDown or event
   */
  recordKeyUp(pressIdOrEvent) {
    if (!this.isCollecting) return null;

    const currentTimestamp = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    
    // Resolve press record
    let pressId = typeof pressIdOrEvent === 'number' ? pressIdOrEvent : null;
    if (pressId === null) {
      // If called with event, resolve the earliest unresolved press
      const keys = Array.from(this.pendingPresses.keys());
      if (keys.length > 0) {
        pressId = keys[0];
      }
    }

    const pending = pressId ? this.pendingPresses.get(pressId) : null;
    if (!pending) return null;

    const holdDuration = Math.max(0, currentTimestamp - pending.pressTime);

    // Record timing kinematics tuple ONLY
    const timingRecord = {
      eventIndex: this.timingEvents.length + 1,
      pressTime: pending.pressTime,
      releaseTime: currentTimestamp,
      holdDuration: Number(holdDuration.toFixed(2)),
      interKeyInterval: Number(pending.interKeyInterval.toFixed(2)),
      isCorrection: pending.isCorrection
    };

    this.timingEvents.push(timingRecord);
    this.pendingPresses.delete(pressId);

    return timingRecord;
  }

  /**
   * Finalizes the controlled session.
   * @param {boolean} [completed=true] - Whether target phrase was fully typed
   * @returns {Object} Raw collection summary with pure timing data
   */
  endSession(completed = true) {
    if (!this.isCollecting) {
      throw new Error("Session is not active.");
    }

    this.endTime = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    this.isCollecting = false;

    // Calculate total duration in seconds
    const durationMs = Math.max(0, this.endTime - this.startTime);
    const durationSeconds = Number((durationMs / 1000.0).toFixed(3));

    // Verify privacy safety prior to returning
    this.verifyNoTextStored();

    return {
      sessionId: this.sessionId,
      participantId: this.participantId,
      taskType: "controlled_phrase",
      targetPhraseLength: this.targetPhrase.length,
      sessionDuration: durationSeconds,
      keystrokeCount: this.timingEvents.length,
      timingEvents: [...this.timingEvents],
      completed: Boolean(completed),
      startTime: this.startTime,
      endTime: this.endTime
    };
  }

  /**
   * Privacy verification audit.
   * Confirms that no character text, passwords, or key codes exist in timing records.
   * @returns {boolean} True if privacy compliance verified
   */
  verifyNoTextStored() {
    for (const record of this.timingEvents) {
      if ('key' in record || 'char' in record || 'text' in record || 'value' in record || 'code' in record) {
        throw new Error("PRIVACY VIOLATION: Character or text data detected in timing records!");
      }
    }
    return true;
  }

  /**
   * Fallback UUID generator.
   */
  _generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}
