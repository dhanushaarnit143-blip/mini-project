import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ModalityInputs } from '../components/forms/ModalityInputs';
import { usePipelineStore } from '../store/usePipelineStore';

describe('Missing Modality Toggles', () => {
  it('toggles modality between included and missing, updating disabled input state', () => {
    render(<ModalityInputs />);

    const olfCard = screen.getByTestId('modality-card-olfactory');
    expect(olfCard).toBeInTheDocument();

    const toggleBtn = olfCard.querySelector('button')!;
    expect(toggleBtn.textContent).toContain('Included');

    // Toggle to missing
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain('Marked Missing');
    expect(usePipelineStore.getState().olfactoryEnabled).toBe(false);

    // Toggle back to included
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain('Included');
    expect(usePipelineStore.getState().olfactoryEnabled).toBe(true);
  });
});
