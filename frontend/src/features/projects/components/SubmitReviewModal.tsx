// OE-DELIVERY: 2026-10-15-estimation-review-v1
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP

/**
 * Modal for submitting a project's estimation for internal review.
 * Pick three reviewers — Lead Estimator, Coordinator, Manager —
 * then Submit. Notifications go to each reviewer. Only the Manager's
 * approval moves the project to Estimation Submitted.
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/shared/lib/api';

interface User {
  id: string;
  full_name?: string;
  email: string;
}

interface SubmitReviewModalProps {
  projectId: string;
  projectName: string;
  onClose: () => void;
  onSubmit: (data: {
    lead_estimator_id?: string;
    coordinator_id?: string;
    manager_id?: string;
    note?: string;
  }) => void;
  isSubmitting: boolean;
  errorMessage?: string;
}

function UserSelect({
  label,
  value,
  onChange,
  users,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  users: User[];
  placeholder: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-content-secondary mb-1.5">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full rounded-lg border border-border bg-surface-primary px-3 text-sm focus:outline-none focus:ring-2 focus:ring-oe-blue/30 focus:border-oe-blue"
      >
        <option value="">{placeholder}</option>
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.full_name || u.email} ({u.email})
          </option>
        ))}
      </select>
    </div>
  );
}

export function SubmitReviewModal({
  projectId,
  projectName,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
}: SubmitReviewModalProps) {
  const { t } = useTranslation();
  const [leadEstimatorId, setLeadEstimatorId] = useState('');
  const [coordinatorId, setCoordinatorId] = useState('');
  const [managerId, setManagerId] = useState('');
  const [note, setNote] = useState('');

  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: () => apiGet<User[]>('/v1/users/'),
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSubmit({
        lead_estimator_id: leadEstimatorId || undefined,
        coordinator_id: coordinatorId || undefined,
        manager_id: managerId || undefined,
        note: note || undefined,
      });
    },
    [leadEstimatorId, coordinatorId, managerId, note, onSubmit],
  );

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('projects.submit_review_title', {
        defaultValue: 'Submit for Internal Review',
      })}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
      data-testid="submit-review-modal"
    >
      <form
        className="bg-surface-primary rounded-xl shadow-xl w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className="flex items-center justify-between border-b border-border-light px-4 py-3">
          <h2 className="text-base font-semibold text-content-primary">
            {t('projects.submit_review_title', {
              defaultValue: 'Submit for Internal Review',
            })}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-content-tertiary hover:text-content-primary"
            aria-label={t('common.close', { defaultValue: 'Close' })}
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-4 py-4 space-y-4">
          <p className="text-sm text-content-secondary">
            {t('projects.submit_review_desc', {
              defaultValue: `Select reviewers for "${projectName}". Notifications will be sent to each. Only the Manager's approval moves the project to Estimation Submitted.`,
              projectName,
            })}
          </p>
          <UserSelect
            label={t('projects.reviewer_lead_estimator', { defaultValue: 'Lead Estimator' })}
            value={leadEstimatorId}
            onChange={setLeadEstimatorId}
            users={users}
            placeholder={t('projects.select_user', { defaultValue: 'Select user...' })}
          />
          <UserSelect
            label={t('projects.reviewer_coordinator', { defaultValue: 'Coordinator' })}
            value={coordinatorId}
            onChange={setCoordinatorId}
            users={users}
            placeholder={t('projects.select_user', { defaultValue: 'Select user...' })}
          />
          <UserSelect
            label={t('projects.reviewer_manager', { defaultValue: 'Manager' })}
            value={managerId}
            onChange={setManagerId}
            users={users}
            placeholder={t('projects.select_user', { defaultValue: 'Select user...' })}
          />
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1.5">
              {t('projects.review_note', { defaultValue: 'Note (optional)' })}
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-oe-blue/30 focus:border-oe-blue"
              placeholder={t('projects.review_note_placeholder', {
                defaultValue: 'Add a note for reviewers...',
              })}
            />
          </div>
          {errorMessage && (
            <p className="text-sm text-red-600">{errorMessage}</p>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-border-light px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-content-secondary hover:bg-surface-secondary"
          >
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-lg bg-oe-blue px-4 py-2 text-sm font-medium text-white hover:bg-oe-blue-dark disabled:opacity-50"
          >
            {isSubmitting
              ? t('common.submitting', { defaultValue: 'Submitting...' })
              : t('common.submit', { defaultValue: 'Submit' })}
          </button>
        </div>
      </form>
    </div>
  );
}
