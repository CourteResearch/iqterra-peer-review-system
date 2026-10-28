/**
 * Reviews page component
 */

import { useState } from 'react';
import { ReviewList, ReviewDetail } from '../components/features';
import { INITIAL_REVIEWS } from '../constants/reviews';
import type { Review, View } from '../types';

interface ReviewsPageProps {
  role: 'Instructor' | 'Student';
}

export function ReviewsPage({ role }: ReviewsPageProps) {
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [scores, setScores] = useState<number[]>([0, 0, 0, 0]);
  const [comment, setComment] = useState('');

  const handleStartReview = (review: Review) => {
    setSelectedReview(review);
    setScores([0, 0, 0, 0]);
    setComment('');
  };

  const handleScoreChange = (index: number, value: number) => {
    setScores(prev => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const handleCommentChange = (value: string) => {
    setComment(value);
  };

  const handleSubmit = () => {
    const words = comment.trim() ? comment.trim().split(/\s+/).length : 0;
    if (scores.some(s => !s)) {
      alert('Choose a score for each rubric criterion.');
      return;
    }
    if (words < 60) {
      alert(`Add ${60 - words} more words to meet the 60-word minimum.`);
      return;
    }
    // In a real app, this would submit to an API
    alert('Review submitted. Thank you for your thoughtful feedback.');
    setSelectedReview(null);
    setScores([0, 0, 0, 0]);
    setComment('');
  };

  const handleClose = () => {
    setSelectedReview(null);
    setScores([0, 0, 0, 0]);
    setComment('');
  };

  return (
    <div className="reviews-page">
      <div className="page-heading">
        <div>
          <h1>Reviews</h1>
          <p>Manage and monitor review rounds for your course</p>
        </div>
        <div className="heading-actions">
          <button className="button button-secondary">Export</button>
          <button className="button button-primary">
            <span>New review round</span>
            <span>→</span>
          </button>
        </div>
      </div>
      <div className="review-grid">
        <ReviewList
          reviews={INITIAL_REVIEWS}
          selectedId={selectedReview?.id || null}
          onSelect={(id) => setSelectedReview(INITIAL_REVIEWS.find(r => r.id === id) || null)}
          onStartReview={handleStartReview}
        />
        <ReviewDetail
          review={selectedReview}
          onSubmit={handleSubmit}
          onClose={handleClose}
          onScoreChange={handleScoreChange}
          onCommentChange={handleCommentChange}
          scores={scores}
          comment={comment}
        />
      </div>
    </div>
  );
}