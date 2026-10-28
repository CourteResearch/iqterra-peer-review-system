/**
 * Progress panel component showing student progress table
 */

import { ProgressChart } from './ProgressChart';
import type { ProgressRow, ChartData } from '../../types';

interface ProgressPanelProps {
  rows: ProgressRow[];
  chartData: ChartData;
}

export function ProgressPanel({ rows, chartData }: ProgressPanelProps) {
  return (
    <section className="progress-panel panel" aria-labelledby="progress-title">
      <div className="panel-heading">
        <div>
          <h2 id="progress-title">Student progress</h2>
          <p>Track individual review completion across the cohort</p>
        </div>
      </div>
      <div className="panel-body">
        <div className="progress-table" role="table">
          <div className="table-head" role="row">
            <span role="columnheader">Student</span>
            <span role="columnheader">Reviews</span>
            <span role="columnheader">Score</span>
            <span role="columnheader">Status</span>
          </div>
          {rows.map((row, index) => (
            <div key={index} className="table-row" role="row">
              <div className="student-cell" role="cell">
                <span className="student-initials" style={{ backgroundColor: `var(--${row[5]})` }}>
                  {row[0]}
                </span>
                <div className="student-info">
                  <b>{row[1]}</b>
                  <small>{row[2]} completed · {row[3]} scored</small>
                </div>
              </div>
              <span role="cell">{row[2]}</span>
              <span role="cell">{row[3]}</span>
              <span role="cell">
                <span className={`status-badge status-${row[4].toLowerCase().replace(' ', '-')}`}>
                  {row[4]}
                </span>
              </span>
            </div>
          ))}
        </div>
        <ProgressChart data={chartData} />
      </div>
    </section>
  );
}