/**
 * Review list component
 */

import { Button } from '../common';
import type { Review } from '../../types';

interface ReviewListProps {
  reviews: Review[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onStartReview: (review: Review) => void;
}

export function ReviewList({ reviews, selectedId, onSelect, onStartReview }: ReviewListProps) {
  return (
    <div className="review-list" role="list" aria-label="Review assignments">
      {reviews.map((review) => (
        <div
          key={review.id}
          className={`review-card ${selectedId === review.id ? 'selected' : ''}`}
          role="listitem"
          onClick={() => onSelect(review.id)}
        >
          <div className="review-thumb" style={{ backgroundColor: `var(--${review.tint})` }}>
            <span aria-hidden="true">{review.initials}</span>
          </div>
          <div className="review-info">
            <h3>{review.title}</h3>
            <p className="review-meta">
              <span>{review.author}</span>
              <span>·</span>
              <span>{review.course}</span>
              <span>·</span>
              <span>{review.due}</span>
            </p>
          </div>
          <div className="review-status">
            <span className={`status-pill status-${review.status.toLowerCase().replace(' ', '-')}`}>
              {review.status}
            </span>
            {review.status !== 'Submitted' && (
              <Button variant="primary" size="sm" onClick={(e) => { e.stopPropagation(); onStartReview(review); }}>
                {review.status === 'In progress' ? 'Continue' : 'Start review'}
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}