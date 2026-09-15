import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { DisclaimerBanner } from '../components/layout/DisclaimerBanner';

describe('Disclaimer Banner Compliance', () => {
  it('renders the persistent disclaimer banner with non-diagnostic warnings', () => {
    render(<DisclaimerBanner />);
    const banner = screen.getByTestId('disclaimer-banner');
    expect(banner).toBeInTheDocument();
    expect(banner.textContent?.toLowerCase()).toContain('not for clinical diagnosis');
    expect(banner.textContent?.toLowerCase()).toContain('research prototype');
  });
});
