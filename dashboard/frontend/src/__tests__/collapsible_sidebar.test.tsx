import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import React from 'react';
import { Sidebar } from '../components/Sidebar';
import { App } from '../App';

describe('Collapsible Left Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders sidebar open with ~280px width class and allows toggling to collapsed (0px width class)', () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <Sidebar
        currentScreen="overview"
        onNavigate={vi.fn()}
        isOpen={true}
        onToggle={onToggle}
      />
    );

    const desktopAside = screen.getByTestId('desktop-sidebar');
    expect(desktopAside).toHaveClass('w-[280px]');

    // Chevron icon rotation when open
    const chevronIcon = screen.getByTestId('sidebar-chevron-icon');
    expect(chevronIcon).toHaveClass('rotate-0');

    // Click toggle button
    const toggleBtn = screen.getByTestId('sidebar-toggle-btn');
    act(() => {
      fireEvent.click(toggleBtn);
    });
    expect(onToggle).toHaveBeenCalledTimes(1);

    // Rerender as collapsed
    rerender(
      <Sidebar
        currentScreen="overview"
        onNavigate={vi.fn()}
        isOpen={false}
        onToggle={onToggle}
      />
    );

    expect(desktopAside).toHaveClass('w-0');
    expect(desktopAside).toHaveClass('opacity-0');
    expect(desktopAside).toHaveClass('border-r-0');
  });

  it('persists sidebar state in localStorage across interactions in App', async () => {
    window.innerWidth = 1024;
    await act(async () => {
      render(<App />);
    });

    // Initially open on desktop
    const desktopAside = screen.getByTestId('desktop-sidebar');
    expect(desktopAside).toHaveClass('w-[280px]');

    // Click toggle button inside sidebar header to collapse
    const sidebarToggle = screen.getByTestId('sidebar-toggle-btn');
    act(() => {
      fireEvent.click(sidebarToggle);
    });

    // Should now be closed
    expect(desktopAside).toHaveClass('w-0');
    expect(localStorage.getItem('sidebar_state')).toBe('closed');

    // Floating toggle button appears on left edge when collapsed
    const collapsedToggleBtn = screen.getByTestId('sidebar-collapsed-toggle-btn');
    expect(collapsedToggleBtn).toBeInTheDocument();

    // Rotated chevron in collapsed indicator
    const floatingChevron = screen.getByTestId('sidebar-collapsed-chevron-icon');
    expect(floatingChevron).toHaveClass('rotate-180');

    // Re-open via collapsed floating button
    act(() => {
      fireEvent.click(collapsedToggleBtn);
    });
    expect(desktopAside).toHaveClass('w-[280px]');
    expect(localStorage.getItem('sidebar_state')).toBe('open');
  });

  it('initializes from existing localStorage state', async () => {
    window.innerWidth = 1024;
    localStorage.setItem('sidebar_state', 'closed');

    await act(async () => {
      render(<App />);
    });

    const desktopAside = screen.getByTestId('desktop-sidebar');
    expect(desktopAside).toHaveClass('w-0');
    expect(screen.getByTestId('sidebar-collapsed-toggle-btn')).toBeInTheDocument();
  });

  it('supports toggling from top Header hamburger button', async () => {
    window.innerWidth = 1024;
    await act(async () => {
      render(<App />);
    });

    const desktopAside = screen.getByTestId('desktop-sidebar');
    expect(desktopAside).toHaveClass('w-[280px]');

    const headerToggle = screen.getByTestId('header-sidebar-toggle');
    act(() => {
      fireEvent.click(headerToggle);
    });

    expect(desktopAside).toHaveClass('w-0');
    expect(localStorage.getItem('sidebar_state')).toBe('closed');

    // Toggle back open from header
    act(() => {
      fireEvent.click(headerToggle);
    });
    expect(desktopAside).toHaveClass('w-[280px]');
    expect(localStorage.getItem('sidebar_state')).toBe('open');
  });

  it('renders mobile drawer and backdrop, closing on backdrop click or navigation', () => {
    const onNavigate = vi.fn();
    const onClose = vi.fn();

    render(
      <Sidebar
        currentScreen="overview"
        onNavigate={onNavigate}
        isOpen={true}
        onClose={onClose}
      />
    );

    // Mobile drawer is rendered
    const mobileDrawer = screen.getByTestId('mobile-sidebar-drawer');
    expect(mobileDrawer).toHaveClass('translate-x-0');

    // Backdrop is present
    const backdrop = screen.getByTestId('mobile-drawer-backdrop');
    expect(backdrop).toBeInTheDocument();

    // Clicking backdrop calls onClose
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();

    // Clicking a nav module calls onNavigate and onClose on mobile
    const assessmentBtn = screen.getAllByRole('button', { name: /New Assessment/i })[0];
    fireEvent.click(assessmentBtn);
    expect(onNavigate).toHaveBeenCalledWith('new-assessment');
  });
});
