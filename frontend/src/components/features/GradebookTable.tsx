/**
 * Gradebook table component
 */

import { Button } from '../common';
import { Badge } from '../common';
import type { GradeStudent } from '../../types';

interface GradebookTableProps {
  students: GradeStudent[];
  onView: (student: string) => void;
}

export function GradebookTable({ students, onView }: GradebookTableProps) {
  const statusVariants: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
    Ready: 'success',
    Pending: 'warning',
    'Needs review': 'warning',
    Incomplete: 'error',
  };

  return (
    <div className="gradebook-table" role="table" aria-label="Student grades">
      <div className="table-head" role="row">
        <span role="columnheader">Student</span>
        <span role="columnheader">Reviews completed</span>
        <span role="columnheader">Final score</span>
        <span role="columnheader">Status</span>
        <span role="columnheader">Action</span>
      </div>
      {students.map((student, index) => (
        <div key={index} className="table-row" role="row">
          <span role="cell">{student[0]}</span>
          <span role="cell">{student[1]}</span>
          <span role="cell"><b>{student[2]}</b></span>
          <span role="cell">
            <Badge variant={statusVariants[student[3]] || 'info'}>
              {student[3]}
            </Badge>
          </span>
          <span role="cell">
            <Button variant="ghost" size="sm" onClick={() => onView(student[0])}>
              {student[4]}
            </Button>
          </span>
        </div>
      ))}
    </div>
  );
}