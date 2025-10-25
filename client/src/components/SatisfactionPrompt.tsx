import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Sparkles, X } from 'lucide-react';
import { submitSatisfactionFeedback } from '../services/context';

interface SatisfactionPromptProps {
  conversationId: string;
  onClose: () => void;
  onSubmitted: (satisfied: boolean) => void;
}

export function SatisfactionPrompt({
  conversationId,
  onClose,
  onSubmitted,
}: SatisfactionPromptProps) {
  const [selectedSatisfaction, setSelectedSatisfaction] = useState<boolean | null>(null);
  const [userNotes, setUserNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (selectedSatisfaction === null) return;

    setSubmitting(true);
    setError(null);

    try {
      await submitSatisfactionFeedback(
        conversationId,
        selectedSatisfaction,
        userNotes.trim() || undefined
      );

      onSubmitted(selectedSatisfaction);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-accent-purple/10 via-accent-blue/10 to-accent-green/10 border border-dark-border rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-accent-purple" />
          <h3 className="text-lg font-semibold text-text-primary">
            How did this query work for you?
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-dark-hover rounded transition-colors"
          title="Close"
        >
          <X className="w-5 h-5 text-text-tertiary" />
        </button>
      </div>

      <p className="text-sm text-text-secondary mb-4">
        If you're satisfied with the results, I'll analyze this conversation to learn more about
        your database structure and business rules for future queries!
      </p>

      {/* Satisfaction Buttons */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={() => setSelectedSatisfaction(true)}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
            selectedSatisfaction === true
              ? 'bg-accent-green/20 border-accent-green text-accent-green'
              : 'bg-dark-card border-dark-border text-text-secondary hover:border-accent-green/50 hover:text-accent-green/80'
          }`}
        >
          <ThumbsUp className="w-5 h-5" />
          <span className="font-medium">Perfect!</span>
        </button>

        <button
          onClick={() => setSelectedSatisfaction(false)}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
            selectedSatisfaction === false
              ? 'bg-accent-red/20 border-accent-red text-accent-red'
              : 'bg-dark-card border-dark-border text-text-secondary hover:border-accent-red/50 hover:text-accent-red/80'
          }`}
        >
          <ThumbsDown className="w-5 h-5" />
          <span className="font-medium">Needs work</span>
        </button>
      </div>

      {/* Additional notes for satisfied users */}
      {selectedSatisfaction === true && (
        <div className="space-y-3 mb-4 animate-fade-in">
          <label className="block text-sm font-medium text-text-primary">
            Additional context (optional)
          </label>
          <textarea
            value={userNotes}
            onChange={(e) => setUserNotes(e.target.value)}
            placeholder="Any additional business rules or context about this query? For example: 'Active users = logged in within 30 days' or 'Premium tier = tier field equals premium'"
            rows={3}
            className="input resize-none text-sm"
          />
          <p className="text-xs text-text-tertiary">
            This helps me understand your specific business logic and terminology
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-accent-red/10 border border-accent-red/30 rounded text-sm text-accent-red">
          {error}
        </div>
      )}

      {/* Submit Button */}
      {selectedSatisfaction !== null && (
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className={`btn ${selectedSatisfaction ? 'btn-success' : 'btn-primary'}`}
          >
            {submitting ? (
              'Submitting...'
            ) : selectedSatisfaction ? (
              <>
                <Sparkles className="w-4 h-4" />
                Analyze & Learn
              </>
            ) : (
              'Submit Feedback'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
