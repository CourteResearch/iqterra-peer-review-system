/**
 * Progress chart component (simple bar chart using CSS)
 */

import type { ChartData } from '../../types';

interface ProgressChartProps {
  data: ChartData;
}

export function ProgressChart({ data }: ProgressChartProps) {
  const { labels, datasets } = data;
  const maxValue = Math.max(...datasets.flatMap(d => d.data));

  return (
    <div className="chart" role="img" aria-label="Weekly review activity chart">
      <div className="chart-bars">
        {labels.map((label, i) => (
          <div key={label} className="chart-bar-group">
            <div className="chart-bars-wrapper">
              {datasets.map((dataset, dIndex) => (
                <div
                  key={dIndex}
                  className="chart-bar"
                  style={{
                    height: `${(dataset.data[i] / maxValue) * 100}%`,
                    backgroundColor: dataset.color,
                  }}
                  title={`${dataset.label}: ${dataset.data[i]}`}
                />
              ))}
            </div>
            <span className="chart-day">{label}</span>
          </div>
        ))}
      </div>
      <div className="chart-legend">
        {datasets.map((dataset, i) => (
          <span key={i} className="chart-legend-item">
            <span className="chart-legend-color" style={{ backgroundColor: dataset.color }} />
            {dataset.label}
          </span>
        ))}
      </div>
    </div>
  );
}