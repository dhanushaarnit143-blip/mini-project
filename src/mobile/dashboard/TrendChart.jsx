import React, { useState } from 'react';
import { TrendingUp, Info, Calendar, ShieldCheck, Activity } from 'lucide-react';

/**
 * TrendChart Component — Section 2: Personal Trends
 * 
 * Displays longitudinal trend charts for digital biomarker modalities:
 * - 14, 30, and 90-day time range filters
 * - Baseline reference band (mean ± 1 std envelope)
 * - Current value callout with distance from baseline
 * - Non-diagnostic research labels:
 *   "Within personal baseline" / "Moderate deviation from baseline"
 * - Uncertainty indicator explaining personal normal envelope
 * 
 * Strict Compliance:
 * - Zero diagnostic claims
 * - Non-alarming amber/orange for deviations; calm emerald for baseline
 * - Responsive SVG line rendering with point hover/tap details
 */

export function TrendChart({
  data = [],
  metricName = 'Voice Jitter (%)',
  modality = 'voice',
  timeRange = '30d',
  onTimeRangeChange,
  baselineMean = 1.42,
  baselineStd = 0.28,
  currentValue = 1.55,
  unit = '%',
  description = 'Acoustic pitch perturbation over sustained phonation'
}) {
  const [selectedRange, setSelectedRange] = useState(timeRange);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const handleRangeChange = (range) => {
    setSelectedRange(range);
    if (onTimeRangeChange) {
      onTimeRangeChange(range);
    }
  };

  // Determine deviation magnitude
  const delta = currentValue - baselineMean;
  const zScore = baselineStd > 0 ? delta / baselineStd : 0;
  const absZ = Math.abs(zScore);

  let statusLabel = 'Within personal baseline';
  let statusColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  let badgeDot = 'bg-emerald-400';

  if (absZ >= 2.0 && absZ < 3.0) {
    statusLabel = 'Moderate deviation from baseline';
    statusColor = 'text-amber-300 bg-amber-500/10 border-amber-500/30';
    badgeDot = 'bg-amber-400';
  } else if (absZ >= 3.0) {
    statusLabel = 'Significant deviation from baseline';
    statusColor = 'text-amber-400 bg-amber-600/15 border-amber-600/40';
    badgeDot = 'bg-amber-500';
  } else if (absZ >= 1.5) {
    statusLabel = 'Mild deviation from baseline';
    statusColor = 'text-amber-200/90 bg-amber-500/10 border-amber-500/25';
    badgeDot = 'bg-amber-300';
  }

  // Fallback synthetic data generator for demo/standalone view if data empty
  const points = data.length > 0 ? data : generateDefaultTrendData(selectedRange, baselineMean, baselineStd, currentValue);

  // SVG dimensions
  const svgWidth = 340;
  const svgHeight = 160;
  const padding = { top: 20, right: 16, bottom: 26, left: 38 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;

  // Min and max bounds for y-axis
  const allValues = points.filter(p => !p.isMissing && p.value != null).map(p => p.value);
  const bandMin = baselineMean - (baselineStd * 1.8);
  const bandMax = baselineMean + (baselineStd * 1.8);
  const minY = Math.min(...allValues, bandMin, currentValue) * 0.92;
  const maxY = Math.max(...allValues, bandMax, currentValue) * 1.08;
  const ySpan = maxY - minY || 1;

  const getX = (idx, total) => padding.left + (idx / Math.max(total - 1, 1)) * chartWidth;
  const getY = (val) => padding.top + chartHeight - ((val - minY) / ySpan) * chartHeight;

  // Baseline envelope coordinates
  const upperY = getY(baselineMean + baselineStd);
  const lowerY = getY(baselineMean - baselineStd);
  const meanY = getY(baselineMean);

  // Build path for valid points
  const validPoints = points.map((p, idx) => ({
    ...p,
    x: getX(idx, points.length),
    y: p.isMissing || p.value == null ? null : getY(p.value),
    index: idx
  }));

  const lineSegments = [];
  let currentSegment = [];

  validPoints.forEach(pt => {
    if (pt.y !== null) {
      currentSegment.push(`${pt.x.toFixed(1)},${pt.y.toFixed(1)}`);
    } else if (currentSegment.length > 0) {
      lineSegments.push(currentSegment.join(' '));
      currentSegment = [];
    }
  });
  if (currentSegment.length > 0) {
    lineSegments.push(currentSegment.join(' '));
  }

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-lg space-y-4">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider font-semibold text-indigo-400">
              {modality} Modality
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-xs text-slate-400">{description}</span>
          </div>
          <h3 className="text-base font-bold text-white mt-0.5">{metricName}</h3>
        </div>

        {/* Range Selector */}
        <div className="inline-flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs font-medium self-start sm:self-auto">
          {['14d', '30d', '90d'].map((range) => (
            <button
              key={range}
              onClick={() => handleRangeChange(range)}
              className={`px-3 py-1 rounded-lg transition-all ${
                selectedRange === range
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Current Value & Baseline Status Callout */}
      <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
        <div>
          <div className="text-xs text-slate-400">Latest Observation</div>
          <div className="text-2xl font-extrabold text-white mt-0.5">
            {currentValue.toFixed(2)} <span className="text-xs font-normal text-slate-400">{unit}</span>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs text-slate-400">Personal Reference</div>
          <div className="text-xs font-mono text-slate-300 mt-0.5">
            μ = {baselineMean.toFixed(2)} ± {baselineStd.toFixed(2)} {unit}
          </div>
        </div>
      </div>

      {/* Status Badge */}
      <div className="flex items-center justify-between">
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${statusColor}`}>
          <span className={`w-2 h-2 rounded-full ${badgeDot}`} />
          <span>{statusLabel}</span>
        </div>

        <div className="text-[11px] text-slate-400">
          Z-Score: <span className="font-mono text-slate-200">{zScore >= 0 ? `+${zScore.toFixed(2)}` : zScore.toFixed(2)}σ</span>
        </div>
      </div>

      {/* SVG Chart Canvas */}
      <div className="relative w-full overflow-hidden pt-1">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto overflow-visible select-none"
          role="img"
          aria-label={`${metricName} personal trend line chart over ${selectedRange}`}
        >
          {/* Shaded Baseline Band (mean ± 1 std) */}
          <rect
            x={padding.left}
            y={upperY}
            width={chartWidth}
            height={Math.max(lowerY - upperY, 2)}
            fill="rgba(16, 185, 129, 0.12)"
            rx="4"
          />

          {/* Baseline Band Mean Line */}
          <line
            x1={padding.left}
            y1={meanY}
            x2={padding.left + chartWidth}
            y2={meanY}
            stroke="#10b981"
            strokeWidth="1"
            strokeDasharray="4 4"
            opacity="0.75"
          />

          {/* Y Axis Guide Lines */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left + chartWidth}
            y2={padding.top}
            stroke="#334155"
            strokeWidth="0.5"
            strokeDasharray="2 2"
          />
          <line
            x1={padding.left}
            y1={padding.top + chartHeight}
            x2={padding.left + chartWidth}
            y2={padding.top + chartHeight}
            stroke="#334155"
            strokeWidth="0.5"
          />

          {/* Y Axis Labels */}
          <text
            x={padding.left - 6}
            y={upperY + 3}
            fill="#94a3b8"
            fontSize="9"
            textAnchor="end"
            fontFamily="monospace"
          >
            +1σ
          </text>
          <text
            x={padding.left - 6}
            y={meanY + 3}
            fill="#10b981"
            fontSize="9"
            fontWeight="bold"
            textAnchor="end"
            fontFamily="monospace"
          >
            mean
          </text>
          <text
            x={padding.left - 6}
            y={lowerY + 3}
            fill="#94a3b8"
            fontSize="9"
            textAnchor="end"
            fontFamily="monospace"
          >
            -1σ
          </text>

          {/* Trend Line Segments */}
          {lineSegments.map((d, i) => (
            <polyline
              key={i}
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={d}
            />
          ))}

          {/* Data Points */}
          {validPoints.map((pt, i) => {
            const isLast = i === validPoints.length - 1;
            if (pt.isMissing || pt.y === null) {
              return (
                <circle
                  key={i}
                  cx={pt.x}
                  cy={meanY}
                  r="2.5"
                  fill="none"
                  stroke="#64748b"
                  strokeWidth="1.2"
                  strokeDasharray="1.5 1.5"
                />
              );
            }

            const ptZ = baselineStd > 0 ? Math.abs((pt.value - baselineMean) / baselineStd) : 0;
            const isDeviated = ptZ >= 1.5;
            const ptColor = isDeviated ? '#f59e0b' : '#10b981';

            return (
              <g key={i}>
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isLast ? '4.5' : '3'}
                  fill={ptColor}
                  stroke="#0f172a"
                  strokeWidth={isLast ? '2' : '1.5'}
                  className="cursor-pointer transition-transform hover:scale-125"
                  onMouseEnter={() => setHoveredPoint(pt)}
                  onMouseLeave={() => setHoveredPoint(null)}
                />
                {isLast && (
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r="8"
                    fill="none"
                    stroke={ptColor}
                    strokeWidth="1.2"
                    opacity="0.6"
                    className="animate-pulse"
                  />
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip */}
        {hoveredPoint && (
          <div
            className="absolute z-10 px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-[11px] text-white shadow-xl pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2"
            style={{
              left: `${(hoveredPoint.x / svgWidth) * 100}%`,
              top: `${(hoveredPoint.y / svgHeight) * 100}%`
            }}
          >
            <div className="font-semibold text-slate-300">{hoveredPoint.date || 'Observation'}</div>
            <div className="text-white font-mono">
              {hoveredPoint.value?.toFixed(2)} {unit}
            </div>
          </div>
        )}
      </div>

      {/* Uncertainty & Baseline Band Legend */}
      <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm bg-emerald-500/25 border border-emerald-500/40 inline-block" />
            <span>Personal Baseline Band (mean ± 1 std)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-slate-500 inline-block" />
            <span>Missing day</span>
          </div>
        </div>

        <div className="text-slate-400 italic">
          Uncertainty envelope derived from 14-day calibration profile
        </div>
      </div>
    </div>
  );
}

/**
 * Generates synthetic trend points for testing or initial view [SYNTHETIC].
 */
function generateDefaultTrendData(range, mean, std, current) {
  const count = range === '14d' ? 14 : range === '90d' ? 90 : 30;
  const result = [];
  const now = new Date();

  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];

    if (i === 0) {
      result.push({ date: dateStr, value: current, isMissing: false });
    } else if (i % 7 === 3) {
      // simulate occasional missing day
      result.push({ date: dateStr, value: null, isMissing: true });
    } else {
      // Natural fluctuation around personal mean
      const noise = (Math.sin(i * 0.7) * std * 0.8) + ((Math.random() - 0.5) * std * 0.4);
      result.push({
        date: dateStr,
        value: parseFloat((mean + noise).toFixed(3)),
        isMissing: false
      });
    }
  }
  return result;
}

export default TrendChart;
