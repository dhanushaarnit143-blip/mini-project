import React, { useState } from 'react';
import { Camera, Mic, Compass, Keyboard, CheckCircle2, ArrowRight, ArrowLeft, ShieldAlert } from 'lucide-react';

/**
 * Screen 3: Device Sensor Permissions
 * Granular hardware permission granting with plain-language necessity explanations.
 */
export function PermissionsScreen({ onNext, onBack, permissionsState, onUpdatePermissions }) {
  const [permissions, setPermissions] = useState({
    microphone: permissionsState?.microphone ?? true,
    motion: permissionsState?.motion ?? true,
    keyboard: permissionsState?.keyboard ?? true,
    camera: permissionsState?.camera ?? false,
  });

  const togglePermission = (key) => {
    setPermissions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleGrant = () => {
    onUpdatePermissions(permissions);
    onNext();
  };

  const permissionItems = [
    {
      key: 'microphone',
      name: 'Microphone Access',
      icon: Mic,
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      badge: 'Required for Voice',
      badgeColor: 'bg-amber-950/80 text-amber-300 border-amber-800',
      description: 'Used solely during active voice tasks to record brief sustained phonation (e.g., saying "ah" for 5 seconds). No ambient listening.'
    },
    {
      key: 'motion',
      name: 'Motion Sensors (Accelerometer & Gyro)',
      icon: Compass,
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      badge: 'Required for Motor',
      badgeColor: 'bg-emerald-950/80 text-emerald-300 border-emerald-800',
      description: 'Samples high-frequency postural tremor and alternating tap rhythm. Sensor data is processed during explicit 20-second active tests.'
    },
    {
      key: 'keyboard',
      name: 'Keyboard & Touchscreen Timing',
      icon: Keyboard,
      color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
      badge: 'Required for Typing',
      badgeColor: 'bg-sky-950/80 text-sky-300 border-sky-800',
      description: 'Calculates millisecond timing between key presses and touch durations. Typed text, letters, and numbers are NEVER stored or inspected.'
    },
    {
      key: 'camera',
      name: 'Front Camera (Ocular / Visual)',
      icon: Camera,
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
      badge: 'Optional Task',
      badgeColor: 'bg-slate-800 text-slate-300 border-slate-700',
      description: 'Measures fixational stability and saccadic eye movements during dot-following tests. (This is visual behavior tracking, NOT retinal imaging).'
    }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto font-sans">
      <div>
        {/* Navigation Bar */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Step 3: Device Permissions
          </div>
          <div className="w-5" />
        </div>

        <h2 className="text-2xl font-bold tracking-tight text-white">
          Granular Hardware Access
        </h2>
        <p className="mt-2 text-xs text-slate-400 leading-relaxed">
          Select which sensors to authorize for in-app micro-assessments. You can grant or revoke any sensor permission at any time in settings.
        </p>

        {/* Permissions List */}
        <div className="mt-5 space-y-3">
          {permissionItems.map((item) => {
            const Icon = item.icon;
            const isGranted = permissions[item.key];
            return (
              <div
                key={item.key}
                onClick={() => togglePermission(item.key)}
                className={`p-3.5 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                  isGranted
                    ? 'bg-slate-900/90 border-indigo-600/50 shadow-md shadow-indigo-950/20'
                    : 'bg-slate-900/40 border-slate-800/80 opacity-75'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl border ${item.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-slate-100">{item.name}</span>
                        <span className={`px-2 py-0.5 rounded-full border text-[9px] font-semibold ${item.badgeColor}`}>
                          {item.badge}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        {item.description}
                      </div>
                    </div>
                  </div>

                  {/* Toggle Indicator */}
                  <div className={`shrink-0 w-5 h-5 rounded-full border flex items-center justify-center transition mt-0.5 ${
                    isGranted
                      ? 'bg-emerald-500 border-emerald-400 text-slate-950'
                      : 'border-slate-700 bg-slate-800'
                  }`}>
                    {isGranted && <CheckCircle2 className="w-4 h-4 text-white" />}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 text-indigo-400 shrink-0" />
          <span>Sensors are strictly powered down when active tasks are complete.</span>
        </div>
      </div>

      {/* Grant Action */}
      <div className="pt-4 pb-2">
        <button
          onClick={handleGrant}
          className="w-full py-3.5 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <span>Grant Selected Permissions</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default PermissionsScreen;
