import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { AnalysisButton } from '../components/forms/AnalysisButton';
import { usePipelineStore } from '../store/usePipelineStore';

describe('Error Handling and UI Resilience', () => {
  it('renders an error toast gracefully without crashing when an error is set in store', () => {
    usePipelineStore.setState({
      errorMessage: 'Audio file failed quality check. Please try another recording or mark as missing.',
    });

    render(<AnalysisButton />);
    const errorToast = screen.getByTestId('error-toast');
    expect(errorToast).toBeInTheDocument();
    expect(errorToast.textContent).toContain('Audio file failed quality check');
  });
});
