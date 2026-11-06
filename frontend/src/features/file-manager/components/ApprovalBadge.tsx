// OE-DELIVERY: 2026-10-22-approved-tag-v4-inreview
/**
 * Approval outcome tags for the Documents grid/list.
 *
 * A file carries a pill next to its name from its LATEST approval
 * workflow: amber IN REVIEW while that workflow is still open (from
 * Submit for Internal Review until a decision lands), green APPROVED
 * when the manager approved it, red REJECTED when it was rejected.
 * Withdrawn workflows show no pill. Workflow data comes from the same
 * `useApprovals` query
 * the preview pane uses, so there is no extra fetch — React Query
 * shares the cache, and the tag updates live when a decision is made.
 */
import { useMemo } from 'react';
import { BadgeCheck, Clock, XCircle } from 'lucide-react';
import { useApprovals } from '@/features/file-approvals/hooks';

export type ApprovalOutcome = 'approved' | 'rejected' | 'in_review';

/** Latest decided outcome per file key (`${file_kind}:${file_id}`). */
export function useApprovalStatusByFile(
  projectId: string | null | undefined,
): Map<string, ApprovalOutcome> {
  const { data: workflows = [] } = useApprovals(projectId);
  return useMemo(() => {
    const latest = new Map<string, { status: string; created_at: string }>();
    for (const w of workflows) {
      const key = `${w.file_kind}:${w.file_id}`;
      const prev = latest.get(key);
      if (!prev || w.created_at > prev.created_at) {
        latest.set(key, { status: w.status, created_at: w.created_at });
      }
    }
    const out = new Map<string, ApprovalOutcome>();
    for (const [key, v] of latest) {
      if (
        v.status === 'approved' ||
        v.status === 'rejected' ||
        v.status === 'in_review'
      ) {
        out.set(key, v.status);
      }
    }
    return out;
  }, [workflows]);
}

export function fileApprovalKey(kind: string, id: string): string {
  return `${kind}:${id}`;
}

/** Amber IN REVIEW / green APPROVED / red REJECTED pill. Renders nothing otherwise. */
export function ApprovalPill({
  status,
}: {
  status: ApprovalOutcome | string | undefined;
}) {
  if (status === 'approved') {
    return (
      <span className="inline-flex shrink-0 items-center gap-0.5 rounded-md bg-emerald-600 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-white">
        <BadgeCheck size={10} strokeWidth={2.5} />
        Approved
      </span>
    );
  }
  if (status === 'in_review') {
    return (
      <span className="inline-flex shrink-0 items-center gap-0.5 rounded-md bg-amber-600 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-white">
        <Clock size={10} strokeWidth={2.5} />
        In Review
      </span>
    );
  }
  if (status === 'rejected') {
    return (
      <span className="inline-flex shrink-0 items-center gap-0.5 rounded-md bg-red-600 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-white">
        <XCircle size={10} strokeWidth={2.5} />
        Rejected
      </span>
    );
  }
  return null;
}
