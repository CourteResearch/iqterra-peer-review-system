/**
 * Allocation table component
 */

import { Button } from '../common';
import type { AllocationRow } from '../../types';

interface AllocationTableProps {
  rows: AllocationRow[];
  onReallocate: (student: string) => void;
}

export function AllocationTable({ rows, onReallocate }: AllocationTableProps) {
  return (
    <div className="allocation-table" role="table" aria-label="Reviewer allocations">
      <div className="table-head" role="row">
        <span role="columnheader">Student</span>
        <span role="columnheader">Assigned reviewers</span>
        <span role="columnheader">Assigned</span>
        <span role="columnheader">Completed</span>
        <span role="columnheader">Action</span>
      </div>
      {rows.map((row, index) => (
        <div key={index} className="table-row" role="row">
          <span role="cell">{row[0]}</span>
          <span role="cell">{row[1]}</span>
          <span role="cell">{row[2]}</span>
          <span role="cell">{row[3]}</span>
          <span role="cell">
            <Button variant="ghost" size="sm" onClick={() => onReallocate(row[0])}>
              {row[4]}
            </Button>
          </span>
        </div>
      ))}
    </div>
  );
}