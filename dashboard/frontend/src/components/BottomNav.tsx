import React from 'react';
import { ScreenId } from '../types';

interface BottomNavProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
}

interface NavItem {
  id: ScreenId;
  label: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: 'analytics' },
  { id: 'new-assessment', label: 'Assessment', icon: 'assignment_add' },
  { id: 'results-dashboard', label: 'Results', icon: 'monitoring' },
  { id: 'explainability-shap', label: 'Explain', icon: 'psychology' },
];

export const BottomNav: React.FC<BottomNavProps> = ({ currentScreen, onNavigate }) => {
  return (
    <nav className="fixed bottom-0 w-full z-50 pb-safe bg-surface/95 backdrop-blur-xl border-t border-surface-container-high/40 shadow-[0_-2px_12px_rgba(0,0,0,0.04)] lg:hidden">
      <div className="h-16 px-space-sm max-w-4xl mx-auto flex items-center justify-around">
        {NAV_ITEMS.map((item) => {
          const isActive = currentScreen === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              aria-current={isActive ? 'page' : undefined}
              className={`flex flex-col items-center justify-center gap-0.5 min-w-[56px] min-h-[44px] px-2 rounded-lg transition-colors cursor-pointer select-none ${
                isActive
                  ? 'text-primary font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className={`material-symbols-outlined text-[22px] transition-transform ${isActive ? 'scale-110' : ''}`}>
                {item.icon}
              </span>
              <span className="font-label-sm text-[11px] tracking-tight">{item.label}</span>
              {isActive && (
                <span className="w-1.5 h-1.5 rounded-full bg-primary -mt-0.5"></span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
