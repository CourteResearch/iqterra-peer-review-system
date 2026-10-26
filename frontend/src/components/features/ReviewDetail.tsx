/**
 * Review detail component for conducting a review
 */

import { useState, useMemo } from 'react';
import { Button, Panel, Input } from '../common';
import { RUBRIC } from '../../constants';
import type { Review, RubricItem } from '../../types';

interface ReviewDetailProps {
  review: Review | null;
  onSubmit: () => void;
  onClose: () => void;
  onScoreChange: (index: number, value: number) => void;
  onCommentChange: (value: string) => void;
  scores: number[];
  comment: string;
}

export function ReviewDetail({
  review,
  onSubmit,
  onClose,
  onScoreChange,
  onCommentChange,
  scores,
  comment,
}: ReviewDetailProps) {
  const [hoveredScore, setHoveredScore] = useState<number | null>(null);
  const words = useMemo(() => comment.trim() ? comment.trim().split(/\s+/).length : 0, [comment]);
  const canSubmit = scores.every(s => s > 0) && words >= 60;

  if (!review) return null;

  const handleScoreClick = (criterionIndex: number, score: number) => {
    onScoreChange(criterionIndex, score);
  };

  const handleKeyDown = (e: React.KeyboardEvent, criterionIndex: number, score: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleScoreClick(criterionIndex, score);
    }
  };

  return (
    <div className="review-detail" role="region" aria-labelledby="review-detail-title">
      <Panel
        title={review.title}
        subtitle={`${review.course} · ${review.due}`}
        headingAction={
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        }
      >
        <div className="review-submission">
          <div className="submission-header">
            <div className="submission-author">
              <span className="author-avatar" style={{ backgroundColor: `var(--${review.tint})` }}>
                {review.initials}
              </span>
              <div>
                <b>{review.author}</b>
                <small>{review.course}</small>
              </div>
            </div>
            <span className={`submission-status status-${review.status.toLowerCase().replace(' ', '-')}`}>
              {review.status}
            </span>
          </div>

          <div className="submission-content">
            <p className="submission-text">
              This is the student's submission content. In a real application, this would display
              the actual submitted work (document, code, design, etc.) for review.
            </p>
          </div>

          <div className="rubric-section">
            <h3>Review rubric</h3>
            <p className="rubric-note">Score each criterion from 1 (needs improvement) to 3 (excellent)</p>
            <div className="rubric-grid" role="radiogroup" aria-label="Rubric scoring">
              {RUBRIC.map((criterion: RubricItem, index: number) => (
                <div key={index} className="rubric-item">
                  <div className="rubric-criterion">
                    <h4>{criterion.title}</h4>
                    <p>{criterion.note}</p>
                  </div>
                  <div className="rubric-scores" role="group" aria-label={`${criterion.title} score`}>
                    {[1, 2, 3].map((score) => (
                      <button
                        key={score}
                        className={`rubric-score ${scores[index] === score ? 'selected' : ''} ${hoveredScore === score && scores[index] !== score ? 'hovered' : ''}`}
                        onClick={() => handleScoreClick(index, score)}
                        onMouseEnter={() => setHoveredScore(score)}
                        onMouseLeave={() => setHoveredScore(null)}
                        onKeyDown={(e) => handleKeyDown(e, index, score)}
                        role="radio"
                        aria-checked={scores[index] === score}
                        aria-label={`${score} out of 3`}
                        tabIndex={0}
                      >
                        {score}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="comment-section">
            <label className="comment-label">
              <span>Written feedback <small>(minimum 60 words)</small></span>
              <span className="word-count">{words}/60 words</span>
            </label>
            <Input
              type="textarea"
              value={comment}
              onChange={onCommentChange}
              placeholder="Provide constructive feedback... Minimum 60 words required."
              className="comment-textarea"
            />
            {words < 60 && comment && (
              <p className="word-count-warning">{60 - words} more words needed</p>
            )}
          </div>

          <div className="review-actions">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={onSubmit}
              disabled={!canSubmit}
            >
              Submit review
            </Button>
          </div>
        </div>
      </Panel>
    </div>
  );
}