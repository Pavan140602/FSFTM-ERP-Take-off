// OE-DELIVERY: 2026-10-27-receipt-chip (was 2026-10-27-receipt-edit)
/**
 * Post-Award Pipeline panel — shown as a tab on awarded projects.
 *
 * Mirrors the agreed mockups: a stage tracker (work stages with the
 * project's payment schedule woven between them), a stage card with
 * the current stage's action (including its own schedule block), and
 * a right column with the stage summary + activity timeline.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock,
  Eye,
  Factory,
  FileText,
  Mail,
  MessageSquare,
  Paperclip,
  Pencil,
  Plus,
  PencilRuler,
  Send,
  SkipForward,
  Stamp,
  Truck,
  Wallet,
  X,
} from 'lucide-react';
import { apiGet, apiPatch, apiPost } from '@/shared/lib/api';
import { useToastStore } from '@/stores/useToastStore';

interface PipelineStage {
  key: string;
  label: string;
  state: 'done' | 'current' | 'upcoming' | 'skipped';
  completed_at: string | null;
  // Payment stages only (OE-DELIVERY 2026-10-27): the milestone behind
  // this row, so the card can show percent/label and drive the
  // invoice popup + "Mark received" without legacy gate keys.
  milestone_id: string | null;
  percent: number | null;
  milestone_label: string | null;
  amount: number | null;
  email_sent_at: string | null;
  received_at: string | null;
  inv_sent_at: string | null;
  inv_sent_to: string | null;
}

interface PipelineReceipt {
  id: string;
  milestone_id: string;
  percent: number;
  note: string | null;
  is_excess: boolean;
  seq: number;
  created_at: string;
}

interface PipelineMilestone {
  id: string;
  key: string;
  anchor: string;
  anchor_label: string;
  label: string;
  percent: number;
  seq: number;
  amount: number | null;
  email_sent_at: string | null;
  received_at: string | null;
  inv_sent_at: string | null;
  inv_sent_to: string | null;
  is_award: boolean;
  is_sent: boolean;
  // Partial receipts (OE-DELIVERY 2026-10-27): received sums the
  // non-excess receipts, balance is target minus received, excess is
  // the overshoot kept on the final milestone.
  received_percent: number;
  balance_percent: number;
  excess_percent: number;
  receipts: PipelineReceipt[];
}

interface PipelineSend {
  id: string;
  stage: string;
  transmittal_id: string;
  transmittal_number: string | null;
  subject: string | null;
  recipient_email: string | null;
  recipient_name: string | null;
  recipient_role: string | null;
  recipient_count: number;
  file_names: string[];
  sent_at: string | null;
  opened_at: string | null;
  viewed_at: string | null;
  view_count: number;
  acknowledged_at: string | null;
}

interface ProjectFileRow {
  id: string;
  kind: string;
  name: string;
  size_bytes: number | null;
}

interface PipelineActivity {
  id: string;
  text: string;
  actor_name: string | null;
  created_at: string;
}

interface PipelineRevision {
  id: string;
  stage: string;
  round_no: number;
  outcome: string;
  comments: string | null;
  actor_name: string | null;
  created_at: string;
}

interface PipelineView {
  project_id: string;
  project_name: string;
  client_name: string | null;
  contract_value: string | null;
  currency: string;
  gate_amounts: Record<string, number | null>;
  current_stage: string;
  progress_pct: number;
  stages: PipelineStage[];
  pay10_email_sent_at: string | null;
  pay10_received_at: string | null;
  pay10_inv_sent_at: string | null;
  pay10_inv_sent_to: string | null;
  drafting_skipped: boolean;
  drafting_completed_at: string | null;
  shop_title: string | null;
  shop_file_name: string | null;
  shop_sent_at: string | null;
  client_approved_at: string | null;
  pay60_email_sent_at: string | null;
  pay60_received_at: string | null;
  pay60_inv_sent_at: string | null;
  pay60_inv_sent_to: string | null;
  seal_completed_at: string | null;
  fab_vendor: string | null;
  fab_start_date: string | null;
  fab_expected_date: string | null;
  fab_progress: number;
  fab_status: string | null;
  fab_completed_at: string | null;
  pay30_email_sent_at: string | null;
  pay30_received_at: string | null;
  pay30_inv_sent_at: string | null;
  pay30_inv_sent_to: string | null;
  del_shipment_ref: string | null;
  del_tracking_number: string | null;
  del_carrier: string | null;
  del_destination: string | null;
  del_eta: string | null;
  del_status: string;
  delivered_at: string | null;
  feedback_sent_at: string | null;
  feedback_email: string | null;
  feedback_unlock_at: string | null;
  feedback_available: boolean;
  sends: PipelineSend[];
  activity: PipelineActivity[];
  revisions: PipelineRevision[];
  current_rounds: Record<string, number>;
  milestones: PipelineMilestone[];
}

// OE-DELIVERY 2026-10-27: payment stages use dynamic keys
// ("payment_m1", ...), so the tracker falls back to the Wallet icon for
// any key starting with "payment_" (see the tracker render below).
const STAGE_ICONS: Record<string, ReactNode> = {
  drafting: <PencilRuler size={18} />,
  shop_drawings: <FileText size={18} />,
  seal_sign: <Stamp size={18} />,
  fabrication: <Factory size={18} />,
  delivery: <Truck size={18} />,
  feedback: <MessageSquare size={18} />,
};

function projectInitials(name: string): string {
  const initials = name
    .split(/[^A-Za-z]+/)
    .filter(Boolean)
    .map((w) => w[0]!.toUpperCase())
    .join('');
  return initials || 'PRJ';
}

function defaultShipmentRef(projectName: string): string {
  return `FS-SHP-${new Date().getFullYear()}-${projectInitials(projectName)}-0001`;
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString();
}

function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : `${d.toLocaleDateString()} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function fmtMoney(amount: number | null | undefined, currency: string): string {
  if (amount === null || amount === undefined) return '—';
  return `${currency ? `${currency} ` : ''}${amount.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtBytes(n: number | null | undefined): string {
  if (!n && n !== 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

function TrackingChips({ send }: { send: PipelineSend }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-content-secondary">
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full bg-semantic-success" />
        Sent {fmtDate(send.sent_at)}
      </span>
      {send.acknowledged_at ? (
        <span className="font-medium text-semantic-success">Acknowledged</span>
      ) : send.view_count > 0 ? (
        <span className="flex items-center gap-1">
          <Eye size={12} /> Viewed {send.view_count}× · last {fmtDateTime(send.viewed_at)}
        </span>
      ) : send.opened_at ? (
        <span>Opened · not viewed yet</span>
      ) : (
        <span className="text-content-tertiary">Not opened yet</span>
      )}
    </div>
  );
}

function SendHistoryList({ sends, title }: { sends: PipelineSend[]; title: string }) {
  if (sends.length === 0) return null;
  return (
    <div className="mt-4">
      <div className="mb-2 text-xs font-medium text-content-secondary">{title}</div>
      <div className="space-y-2">
        {[...sends].reverse().map((s) => (
          <div key={s.id} className="rounded-lg border border-border-light px-3 py-2.5">
            <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-content-primary">
              <FileText size={15} className="text-oe-blue" />
              Transmittal {s.transmittal_number ?? ''}
              <span className="font-normal text-content-secondary">
                →{' '}
                {s.recipient_count > 1
                  ? `${s.recipient_count} recipients`
                  : `${s.recipient_name ? `${s.recipient_name} · ` : ''}${s.recipient_email}`}
                {s.recipient_role ? ` (${s.recipient_role})` : ''}
              </span>
            </div>
            {s.file_names.length > 0 && (
              <div className="mt-1 text-xs text-oe-blue">{s.file_names.join(', ')}</div>
            )}
            <div className="mt-1.5">
              <TrackingChips send={s} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const REVISION_OUTCOME_LABEL: Record<string, string> = {
  revision_requested: 'Revision requested',
  approved: 'Approved',
  eor_rejected: 'EOR rejected',
  eor_returned: 'Returned from EOR',
};

/**
 * Review-round history for one stage (OE-DELIVERY 2026-10-26).
 * Rows are chronological; the current round is 1 + the count of
 * round-opening outcomes, computed server-side into current_rounds.
 */
function RoundHistory({ revisions, stage }: { revisions: PipelineRevision[]; stage: string }) {
  const rows = revisions.filter((r) => r.stage === stage);
  if (rows.length === 0) return null;
  return (
    <div className="mt-4">
      <div className="mb-2 text-xs font-medium text-content-secondary">Review Rounds</div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.id} className="rounded-lg border border-border-light px-3 py-2.5">
            <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-content-primary">
              Round R{r.round_no}
              <span className="font-normal text-content-secondary">
                · {REVISION_OUTCOME_LABEL[r.outcome] ?? r.outcome}
                {r.actor_name ? ` · ${r.actor_name}` : ''}
                {` · ${fmtDateTime(r.created_at)}`}
              </span>
            </div>
            {r.comments ? (
              <div className="mt-1 text-sm text-content-secondary">{r.comments}</div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function groupLabel(r: string): string {
  return r === 'Internal' ? 'Internal' : `${r}s`;
}

interface MultiRecipientGroupProps {
  projectId: string;
  sendStage: StageSendPanelProps['sendStage'];
  groupRole: string;
  roleOptions: string[];
  defaultSubject: string;
  disabled?: boolean;
  selectedFiles: Array<{ file_id: string; file_kind: string; name: string }>;
  onSent: (view: PipelineView) => void;
}

/**
 * One role group's own send block (multi-recipient mode): its own
 * recipient rows (role picklist defaults to the group's role), its own
 * Subject + Message, and its own Send button — one transmittal for the
 * group, everyone in it on the same mail.
 */
function MultiRecipientGroup({
  projectId,
  sendStage,
  groupRole,
  roleOptions,
  defaultSubject,
  disabled,
  selectedFiles,
  onSent,
}: MultiRecipientGroupProps) {
  const addToast = useToastStore((s) => s.addToast);
  const emptyRow = () => ({ name: '', email: '', role: groupRole });
  const [rows, setRows] = useState<Array<{ name: string; email: string; role: string }>>([
    emptyRow(),
  ]);
  const [subject, setSubject] = useState(defaultSubject);
  const [message, setMessage] = useState('');

  const send = useMutation({
    mutationFn: () =>
      apiPost<PipelineView>(`/v1/projects/${projectId}/pipeline/send/`, {
        stage: sendStage,
        subject: subject.trim() || null,
        message: message.trim() || null,
        recipients: rows.map((r) => ({
          email: r.email.trim(),
          name: r.name.trim() || null,
          role: r.role,
        })),
        files: selectedFiles,
      }),
    onSuccess: (data) => {
      onSent(data);
      setRows([emptyRow()]);
      setMessage('');
      addToast({
        type: 'success',
        title: 'Files sent',
        message: `Transmittal emailed to the ${groupLabel(groupRole)} group.`,
      });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Send failed', message: error.message });
    },
  });

  const canSend =
    !disabled &&
    !send.isPending &&
    selectedFiles.length > 0 &&
    rows.length > 0 &&
    rows.every((r) => r.email.trim().includes('@'));

  return (
    <div className="mt-3 rounded-lg border border-border-light bg-surface-secondary/40 p-3">
      <div className="text-sm font-semibold text-content-primary">
        Send to {groupLabel(groupRole)}
      </div>
      <div className="mt-2">
        <label className={labelCls}>Recipients</label>
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} className="flex gap-2">
              <input
                className={inputCls}
                style={{ flex: '0 0 130px' }}
                value={r.name}
                placeholder="Name"
                disabled={disabled}
                onChange={(e) =>
                  setRows((prev) =>
                    prev.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)),
                  )
                }
              />
              <input
                className={inputCls}
                style={{ flex: 1, minWidth: 0 }}
                value={r.email}
                placeholder="name@company.com"
                disabled={disabled}
                onChange={(e) =>
                  setRows((prev) =>
                    prev.map((x, j) => (j === i ? { ...x, email: e.target.value } : x)),
                  )
                }
              />
              <select
                className={inputCls}
                style={{ flex: '0 0 112px' }}
                value={r.role}
                disabled={disabled}
                onChange={(e) =>
                  setRows((prev) =>
                    prev.map((x, j) => (j === i ? { ...x, role: e.target.value } : x)),
                  )
                }
              >
                {roleOptions.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
              <button
                type="button"
                title="Remove recipient"
                disabled={disabled || rows.length <= 1}
                onClick={() => setRows((prev) => prev.filter((_, j) => j !== i))}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border text-content-secondary disabled:opacity-40"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setRows((prev) => [...prev, emptyRow()])}
          className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-oe-blue/60 px-4 py-2 text-sm font-medium text-oe-blue transition-colors hover:bg-oe-blue/5 disabled:opacity-50"
        >
          <Plus size={15} /> Add Recipient
        </button>
      </div>
      <div className="mt-3">
        <label className={labelCls}>Subject</label>
        <input
          className={inputCls}
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          disabled={disabled}
        />
      </div>
      <div className="mt-3">
        <label className={labelCls}>Message (goes in the email)</label>
        <textarea
          className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={`Message for the ${groupLabel(groupRole)} group…`}
          disabled={disabled}
        />
      </div>
      <button
        type="button"
        disabled={!canSend}
        onClick={() => send.mutate()}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-oe-blue px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        <Send size={15} /> {send.isPending ? 'Sending…' : `Send to ${groupLabel(groupRole)}`}
      </button>
    </div>
  );
}

interface StageSendPanelProps {
  projectId: string;
  sendStage: 'drafting' | 'shop_prep' | 'shop_client' | 'fabrication' | 'seal_sign';
  heading?: string;
  buttonLabel: string;
  roleOptions?: string[];
  fixedRole?: string;
  defaultRole?: string;
  defaultSubject: string;
  /** Multi-recipient mode: recipient rows with per-row roles, one
   *  Subject/Message block per role, one transmittal per role group. */
  multiRecipient?: boolean;
  defaultSubjectForRole?: (role: string) => string;
  disabled?: boolean;
  disabledHint?: string;
  onSent: (view: PipelineView) => void;
}

function StageSendPanel({
  projectId,
  sendStage,
  heading,
  buttonLabel,
  roleOptions,
  fixedRole,
  defaultRole,
  defaultSubject,
  multiRecipient,
  defaultSubjectForRole,
  disabled,
  disabledHint,
  onSent,
}: StageSendPanelProps) {
  const addToast = useToastStore((s) => s.addToast);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState(defaultRole ?? roleOptions?.[0] ?? '');
  const [subject, setSubject] = useState(defaultSubject);
  const [message, setMessage] = useState('');

  const filesQuery = useQuery({
    queryKey: ['project', projectId, 'pipeline-files'],
    queryFn: () =>
      apiGet<{ items: ProjectFileRow[] }>(`/v1/projects/${projectId}/files/?limit=200`),
    enabled: !!projectId,
  });
  const files = filesQuery.data?.items ?? [];

  const send = useMutation({
    mutationFn: () =>
      apiPost<PipelineView>(`/v1/projects/${projectId}/pipeline/send/`, {
        stage: sendStage,
        recipient_email: email.trim(),
        recipient_name: name.trim() || null,
        recipient_role: fixedRole ?? (role || null),
        subject: subject.trim() || null,
        message: message.trim() || null,
        files: files
          .filter((f) => selectedIds.includes(f.id))
          .map((f) => ({ file_id: f.id, file_kind: f.kind, name: f.name })),
      }),
    onSuccess: (data) => {
      onSent(data);
      setSelectedIds([]);
      addToast({
        type: 'success',
        title: 'Files sent',
        message: `Transmittal emailed to ${email.trim()}.`,
      });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Send failed', message: error.message });
    },
  });

  const toggleFile = (id: string) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const canSend =
    !disabled && !send.isPending && selectedIds.length > 0 && email.trim().includes('@');

  return (
    <div className="rounded-lg border border-border-light p-3">
      {heading && (
        <div className="mb-2 text-sm font-semibold text-content-primary">{heading}</div>
      )}
      {disabled && disabledHint && (
        <p className="mb-2 text-xs text-semantic-warning">{disabledHint}</p>
      )}
      <div className="max-h-44 space-y-1 overflow-y-auto rounded-md border border-border-light bg-surface-secondary/40 p-2">
        {filesQuery.isLoading ? (
          <div className="px-2 py-3 text-xs text-content-tertiary">Loading project files…</div>
        ) : files.length === 0 ? (
          <div className="px-2 py-3 text-xs text-content-tertiary">
            No files in this project's documents yet — upload them from the Documents / Files tab
            first, then send from here.
          </div>
        ) : (
          files.map((f) => (
            <label
              key={f.id}
              className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-content-primary hover:bg-surface-tertiary/60"
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(f.id)}
                onChange={() => toggleFile(f.id)}
                disabled={disabled}
              />
              <Paperclip size={13} className="shrink-0 text-content-tertiary" />
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-xs text-content-tertiary">{fmtBytes(f.size_bytes)}</span>
            </label>
          ))
        )}
      </div>
      {multiRecipient ? (
        <>
          {(roleOptions ?? ['Internal']).slice(0, 2).map((gRole) => (
            <MultiRecipientGroup
              key={gRole}
              projectId={projectId}
              sendStage={sendStage}
              groupRole={gRole}
              roleOptions={roleOptions ?? ['Internal']}
              defaultSubject={
                defaultSubjectForRole ? defaultSubjectForRole(gRole) : defaultSubject
              }
              disabled={disabled}
              selectedFiles={files
                .filter((f) => selectedIds.includes(f.id))
                .map((f) => ({ file_id: f.id, file_kind: f.kind, name: f.name }))}
              onSent={onSent}
            />
          ))}
          <p className="mt-1.5 text-xs text-content-tertiary">
            Each group sends its own File Transmittal with the files selected above.
          </p>
        </>
      ) : (
        <>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Recipient name</label>
          <input
            className={inputCls}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. ABC Detailing"
            disabled={disabled}
          />
        </div>
        <div>
          <label className={labelCls}>Recipient email</label>
          <input
            className={inputCls}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@company.com"
            disabled={disabled}
          />
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Recipient role</label>
          {fixedRole ? (
            <div className="flex h-9 items-center rounded-md border border-border bg-surface-secondary px-3 text-sm text-content-secondary">
              {fixedRole} (fixed)
            </div>
          ) : (
            <select
              className={inputCls}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              disabled={disabled}
            >
              {(roleOptions ?? ['Internal']).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          )}
        </div>
        <div>
          <label className={labelCls}>Subject</label>
          <input
            className={inputCls}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={disabled}
          />
        </div>
      </div>
      <div className="mt-3">
        <label className={labelCls}>Message (goes in the email)</label>
        <textarea
          className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Write the context for this email — it is included with the files."
          disabled={disabled}
        />
      </div>
      <button
        type="button"
        disabled={!canSend}
        onClick={() => send.mutate()}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-oe-blue px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        <Send size={15} /> {send.isPending ? 'Sending…' : buttonLabel}
      </button>
      <p className="mt-1.5 text-xs text-content-tertiary">
        Creates and emails a real File Transmittal with the selected files.
      </p>
        </>
      )}
    </div>
  );
}

const inputCls =
  'h-9 w-full rounded-md border border-border bg-surface-primary px-3 text-sm text-content-primary';
const labelCls = 'text-xs text-content-secondary mb-1 block';


interface AccountsUser {
  id: string;
  name: string;
  email: string;
  role: string;
}

/**
 * "Send {pct}% Invoice to Accountant" popup: pick an Accounts user
 * (their role fills in automatically), write a message, and the ERP
 * emails that user the milestone details so Accounts can invoice the
 * client externally. The milestone's percent and label drive the
 * title, the message and the email subject.
 */
function InvoiceEmailModal({
  projectId,
  milestone,
  projectName,
  amountText,
  onClose,
  onSent,
}: {
  projectId: string;
  milestone: { id: string; percent: number; label: string };
  projectName: string;
  amountText: string;
  onClose: () => void;
  onSent: (view: PipelineView) => void;
}) {
  const addToast = useToastStore((s) => s.addToast);
  const usersQuery = useQuery({
    queryKey: ['project', projectId, 'pipeline-accounts-users'],
    queryFn: () =>
      apiGet<AccountsUser[]>(`/v1/projects/${projectId}/pipeline/accounts-users/`),
  });
  const users = usersQuery.data ?? [];
  const [userId, setUserId] = useState('');
  const [message, setMessage] = useState(
    `Please raise the ${milestone.percent}% ${milestone.label} invoice for ${projectName} (amount ${amountText}) and send it to the client.`,
  );
  useEffect(() => {
    const first = users[0];
    if (!userId && first) setUserId(first.id);
  }, [users, userId]);
  const selected = users.find((u) => u.id === userId) ?? null;

  const send = useMutation({
    mutationFn: () =>
      apiPost<PipelineView>(`/v1/projects/${projectId}/pipeline/invoice-email/`, {
        milestone_id: milestone.id,
        user_id: userId,
        message: message.trim() || null,
      }),
    onSuccess: (data) => {
      onSent(data);
      addToast({
        type: 'success',
        title: 'Email sent to Accounts team with project details',
        message: `Sent to ${selected?.name ?? ''} (Accounts) for the ${milestone.percent}% invoice.`,
      });
      onClose();
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Send failed', message: error.message });
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-surface-primary p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-content-primary">
            Send {milestone.percent}% Invoice to Accountant
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-content-tertiary hover:bg-surface-secondary"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div>
          <label className={labelCls}>User (Accounts team)</label>
          {usersQuery.isLoading ? (
            <div className="text-sm text-content-tertiary">Loading users…</div>
          ) : users.length === 0 ? (
            <div className="rounded-lg bg-semantic-warning/10 px-3 py-2 text-sm text-semantic-warning">
              No Accounts user found. Add a user whose role mentions "account" in
              Settings → Users first.
            </div>
          ) : (
            <select
              className={inputCls}
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} — {u.email}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="mt-3">
          <label className={labelCls}>Role</label>
          <div className="flex h-9 items-center rounded-md border border-border bg-surface-secondary px-3 text-sm text-content-secondary">
            {selected ? selected.role : '—'}
          </div>
        </div>
        <div className="mt-3">
          <label className={labelCls}>Message</label>
          <textarea
            className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>
        <button
          type="button"
          disabled={!selected || send.isPending}
          onClick={() => send.mutate()}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-oe-blue px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <Send size={15} /> {send.isPending ? 'Sending…' : 'Send'}
        </button>
        <p className="mt-2 text-center text-xs text-content-tertiary">
          This emails the selected Accounts user — they invoice the client externally.
        </p>
      </div>
    </div>
  );
}


// OE-DELIVERY 2026-10-27: round receipt percents to 2 decimals for
// display so float sums never render as 29.999999.
function fmtPct(value: number): string {
  return String(Math.round(value * 100) / 100);
}

/**
 * Schedule block for one non-award milestone (OE-DELIVERY 2026-10-27):
 * the receipts list plus an inline Record receipt form, rendered
 * inside the milestone's own payment stage card. The form posts
 * independently, and the view refreshes through onSaved. With readOnly, only the list and
 * balance render (browsed stages). Receipt edit (OE-DELIVERY
 * 2026-10-27): each direct receipt row on the current stage's
 * incomplete milestone gets an Edit button that turns the row into
 * an inline percent + note editor; carried-forward and excess rows
 * are derived, so they never offer Edit. The received-proportion
 * bar under the header shares the indicator's state colour: amber
 * while partial, green once fully received.
 */
function MilestoneReceipts({
  projectId,
  milestone,
  onSaved,
  readOnly = false,
}: {
  projectId: string;
  milestone: PipelineMilestone;
  onSaved: (view: PipelineView) => void;
  readOnly?: boolean;
}) {
  const addToast = useToastStore((s) => s.addToast);
  const [pct, setPct] = useState('');
  const [note, setNote] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPct, setEditPct] = useState('');
  const [editNote, setEditNote] = useState('');

  // Carried-forward rows are derived from an earlier milestone's
  // overpayment (note convention from the record path) - they are
  // never edited directly, only the original entry can change.
  const isCarried = (r: PipelineReceipt) =>
    (r.note ?? '').startsWith('Carried forward from ');

  const updateReceipt = useMutation({
    mutationFn: (args: { id: string; percent: number; note: string | null }) =>
      apiPatch<PipelineView>(
        `/v1/projects/${projectId}/pipeline/milestones/${milestone.id}/receipts/${args.id}/`,
        { percent: args.percent, note: args.note },
      ),
    onSuccess: (data) => {
      onSaved(data);
      setEditingId(null);
      addToast({ type: 'success', title: 'Saved', message: 'Receipt updated.' });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Receipt update failed', message: error.message });
    },
  });

  const saveReceipt = useMutation({
    mutationFn: () =>
      apiPost<PipelineView>(
        `/v1/projects/${projectId}/pipeline/milestones/${milestone.id}/receipts/`,
        { percent: parseFloat(pct), note: note.trim() || null },
      ),
    onSuccess: (data) => {
      onSaved(data);
      setPct('');
      setNote('');
      addToast({ type: 'success', title: 'Saved', message: 'Receipt recorded.' });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Receipt save failed', message: error.message });
    },
  });

  return (
    <div className="mt-3 rounded-lg border border-border p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-content-secondary">
          {milestone.anchor_label} · Target {milestone.percent}%
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
            milestone.received_percent >= milestone.percent
              ? 'bg-semantic-success/10 text-semantic-success'
              : 'bg-semantic-warning/10 text-semantic-warning'
          }`}
        >
          Received {fmtPct(milestone.received_percent)}% · Balance {fmtPct(milestone.balance_percent)}%
          {milestone.excess_percent > 0
            ? ` · Excess ${fmtPct(milestone.excess_percent)}%`
            : ''}
        </span>
      </div>
      <div className="mb-2 h-2 overflow-hidden rounded-full bg-surface-tertiary">
        <div
          className={`h-full rounded-full transition-all ${
            milestone.received_percent >= milestone.percent
              ? 'bg-semantic-success'
              : 'bg-semantic-warning'
          }`}
          style={{
            width: `${
              milestone.percent > 0
                ? Math.min(100, (milestone.received_percent / milestone.percent) * 100)
                : 0
            }%`,
          }}
        />
      </div>
      {milestone.receipts.length > 0 && (
        <div className="mb-2 space-y-1.5">
          {milestone.receipts.map((r) => {
            const canEdit =
              !readOnly && !milestone.received_at && !r.is_excess && !isCarried(r);
            if (editingId === r.id) {
              return (
                <div key={r.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <input
                    className="h-9 w-24 rounded-md border border-border bg-surface-primary px-2.5 text-sm text-content-primary"
                    type="number"
                    min={0.01}
                    step="any"
                    placeholder="Receipt %"
                    value={editPct}
                    onChange={(e) => setEditPct(e.target.value)}
                  />
                  <input
                    className="h-9 flex-1 rounded-md border border-border bg-surface-primary px-2.5 text-sm text-content-primary"
                    placeholder="Reference or note (optional)"
                    value={editNote}
                    onChange={(e) => setEditNote(e.target.value)}
                  />
                  <button
                    type="button"
                    disabled={updateReceipt.isPending || !(parseFloat(editPct) > 0)}
                    onClick={() =>
                      updateReceipt.mutate({
                        id: r.id,
                        percent: parseFloat(editPct),
                        note: editNote.trim() || null,
                      })
                    }
                    className="rounded-lg bg-oe-blue px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-content-primary transition-colors hover:bg-surface-secondary"
                  >
                    Cancel
                  </button>
                </div>
              );
            }
            return (
              <div key={r.id} className="flex items-center justify-between gap-2 text-sm">
                <span className="font-medium text-content-primary">
                  {fmtPct(r.percent)}%
                  {r.is_excess ? (
                    <span className="ml-2 rounded-full bg-semantic-warning/10 px-2 py-0.5 text-xs font-medium text-semantic-warning">
                      Excess
                    </span>
                  ) : null}
                </span>
                <span className="flex-1 truncate text-xs text-content-secondary">
                  {r.note ?? ''}
                </span>
                <span className="text-xs text-content-tertiary">
                  {fmtDateTime(r.created_at)}
                </span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(r.id);
                      setEditPct(String(r.percent));
                      setEditNote(r.note ?? '');
                    }}
                    className="flex shrink-0 items-center gap-1 rounded-md border border-oe-blue/60 px-2.5 py-1 text-xs font-medium text-oe-blue transition-colors hover:bg-oe-blue/5"
                  >
                    <Pencil size={12} /> Edit
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
      {!readOnly && !milestone.received_at && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="h-9 w-24 rounded-md border border-border bg-surface-primary px-2.5 text-sm text-content-primary"
            type="number"
            min={0.01}
            step="any"
            placeholder="Receipt %"
            value={pct}
            onChange={(e) => setPct(e.target.value)}
          />
          <input
            className="h-9 flex-1 rounded-md border border-border bg-surface-primary px-2.5 text-sm text-content-primary"
            placeholder="Reference or note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            type="button"
            disabled={saveReceipt.isPending || !(parseFloat(pct) > 0)}
            onClick={() => saveReceipt.mutate()}
            className="rounded-lg bg-oe-blue px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Save receipt
          </button>
        </div>
      )}
    </div>
  );
}

export function AwardPipelinePanel({ projectId }: { projectId: string | null }) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const queryKey = ['project', projectId, 'pipeline'];

  const {
    data: view,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: () => apiGet<PipelineView>(`/v1/projects/${projectId}/pipeline/`),
    enabled: !!projectId,
    retry: 1,
  });

  // Stage browsing (tracker arrows): null = follow the current stage.
  const [browseKey, setBrowseKey] = useState<string | null>(null);
  useEffect(() => {
    setBrowseKey(null);
  }, [view?.current_stage]);

  // Local form state for the record stages.
  const [fabVendor, setFabVendor] = useState('');
  const [fabStart, setFabStart] = useState('');
  const [fabExpected, setFabExpected] = useState('');
  const [fabStatus, setFabStatus] = useState('started');
  const [delRef, setDelRef] = useState('');
  const [delTracking, setDelTracking] = useState('');
  const [delCarrier, setDelCarrier] = useState('');
  const [delDest, setDelDest] = useState('');
  const [delEta, setDelEta] = useState('');
  // OE-DELIVERY 2026-10-26: revision / EOR-reject comment boxes.
  const [draftRevComment, setDraftRevComment] = useState('');
  const [shopRevComment, setShopRevComment] = useState('');
  const [sealRejectComment, setSealRejectComment] = useState('');
  const [invoiceGate, setInvoiceGate] = useState<{ id: string; percent: number; label: string } | null>(null);
  const [fbEmail, setFbEmail] = useState('');
  const [fbSubject, setFbSubject] = useState('');
  const [fbMessage, setFbMessage] = useState('');

  // Sync the record-stage forms from the server view — but ONLY fields
  // the user has not edited since the last sync. The view object changes
  // on every refetch (e.g. when a recipient opens a transmittal and the
  // tracking counts move), and a naive sync wiped typed-but-unsaved
  // values, which is why "Save Delivery Details" appeared not to work.
  const formSyncRef = useRef<{ pid: string; values: Record<string, string> } | null>(null);
  useEffect(() => {
    if (!view) return;
    const server: Record<string, string> = {
      fabVendor: view.fab_vendor ?? '',
      fabStart: view.fab_start_date ?? '',
      fabExpected: view.fab_expected_date ?? '',
      fabStatus: view.fab_status ?? 'started',
      delRef: view.del_shipment_ref ?? defaultShipmentRef(view.project_name),
      delTracking: view.del_tracking_number ?? '',
      delCarrier: view.del_carrier ?? '',
      delDest: view.del_destination ?? '',
      delEta: view.del_eta ?? '',
    };
    const setters: Record<string, (v: string) => void> = {
      fabVendor: setFabVendor,
      fabStart: setFabStart,
      fabExpected: setFabExpected,
      fabStatus: setFabStatus,
      delRef: setDelRef,
      delTracking: setDelTracking,
      delCarrier: setDelCarrier,
      delDest: setDelDest,
      delEta: setDelEta,
    };
    const current: Record<string, string> = {
      fabVendor,
      fabStart,
      fabExpected,
      fabStatus,
      delRef,
      delTracking,
      delCarrier,
      delDest,
      delEta,
    };
    const last = formSyncRef.current;
    for (const key of Object.keys(server)) {
      // Adopt the server value on first sync / project switch, or when
      // the field still holds exactly what the last sync put there
      // (untouched by the user). Edited fields are left alone.
      const setter = setters[key];
      const value = server[key];
      if (
        setter &&
        value !== undefined &&
        (!last || last.pid !== view.project_id || current[key] === last.values[key])
      ) {
        setter(value);
      }
    }
    formSyncRef.current = { pid: view.project_id, values: server };
  }, [view]);

  // Prefill the feedback form once the stage unlocks (30 days after delivery).
  useEffect(() => {
    if (view?.feedback_available) {
      setFbSubject((prev) => prev || `We value your feedback — ${view.project_name}`);
      setFbMessage(
        (prev) =>
          prev ||
          `Dear ${view.client_name ?? 'Client'},\n\nThank you for your business. The project ${view.project_name} was delivered recently, and we would love to hear your feedback about our work. A short reply to this email is all it takes.\n\nThank you!`,
      );
    }
  }, [view?.feedback_available, view?.project_name, view?.client_name]);

  const action = useMutation({
    mutationFn: (args: { path: string; body?: unknown }) =>
      apiPost<PipelineView>(`/v1/projects/${projectId}/pipeline/${args.path}`, args.body ?? {}),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKey, data);
      if (variables.path.includes('/receipts/')) {
        addToast({ type: 'success', title: 'Saved', message: 'Receipt recorded.' });
      } else if (variables.path === 'delivery/' || variables.path === 'fabrication/') {
        addToast({ type: 'success', title: 'Saved', message: 'Details saved.' });
      } else if (variables.path.endsWith('revision/')) {
        addToast({ type: 'success', title: 'Saved', message: 'Revision requested.' });
      } else if (variables.path === 'seal-sign/reject/') {
        addToast({ type: 'success', title: 'Saved', message: 'Returned to Engineering.' });
      }
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Pipeline action failed', message: error.message });
    },
  });

  if (!projectId) return null;
  if (isLoading) {
    return <div className="py-10 text-center text-sm text-content-tertiary">Loading pipeline…</div>;
  }
  if (!view) {
    // A failed load must never masquerade as endless loading.
    return (
      <div className="py-10 text-center">
        <p className="text-sm font-semibold text-semantic-danger">Could not load the pipeline.</p>
        <p className="mx-auto mt-1 max-w-md text-xs text-content-tertiary">
          {queryError instanceof Error ? queryError.message : 'Unknown error — try again.'}
        </p>
        <button
          type="button"
          onClick={() => void refetch()}
          className="mt-3 rounded-lg border border-border px-4 py-2 text-sm font-medium text-content-primary transition-colors hover:bg-surface-secondary"
        >
          Retry
        </button>
      </div>
    );
  }

  const stage = view.current_stage;
  const draftingSends = view.sends.filter((s) => s.stage === 'drafting');
  // OE-DELIVERY 2026-10-26: tolerate a pre-update backend view (no rounds yet).
  const viewRevisions = view.revisions ?? [];
  const viewRounds = view.current_rounds ?? {};
  // Latest EOR return, for the rework banner.
  const draftingEorReturn = [...viewRevisions]
    .reverse()
    .find((r) => r.stage === 'drafting' && r.outcome === 'eor_returned');

  // OE-DELIVERY 2026-10-26 (round-grouped activity): split the Stage
  // Activity timeline into segments at each review outcome, so every
  // round's activities sit under their own small heading (Round R2,
  // Round R3, ...). Revisions sort after activities at equal timestamps,
  // so the log that pairs with a revision stays in the round it closes.
  const activityGroups: { heading: string; items: PipelineActivity[] }[] = (() => {
    const stageLabel = new Map(view.stages.map((s) => [s.key, s.label]));
    const reviewStages = new Set(['drafting', 'shop_drawings', 'seal_sign']);
    // Next stage in the dynamic order - the stage after seal_sign
    // is whatever payment milestone follows it on this schedule.
    const nextKeyAfter = (stage: string): string | undefined => {
      const i = view.stages.findIndex((s) => s.key === stage);
      return i >= 0 ? view.stages[i + 1]?.key : undefined;
    };
    const labelFor = (stage: string, round: number | null) =>
      round !== null && reviewStages.has(stage)
        ? `Round R${round} — ${stageLabel.get(stage) ?? stage}`
        : (stageLabel.get(stage) ?? stage);
    type Ev =
      | { t: string; kind: 0; a: PipelineActivity }
      | { t: string; kind: 1; r: PipelineRevision };
    const events: Ev[] = [
      ...view.activity.map((a) => ({ t: a.created_at, kind: 0 as const, a })),
      ...viewRevisions.map((r) => ({ t: r.created_at, kind: 1 as const, r })),
    ];
    events.sort((x, y) => (x.t < y.t ? -1 : x.t > y.t ? 1 : x.kind - y.kind));
    const groups: { heading: string; items: PipelineActivity[] }[] = [
      {
        heading: labelFor(view.drafting_skipped ? 'shop_drawings' : 'drafting', 1),
        items: [],
      },
    ];
    for (const ev of events) {
      if (ev.kind === 1) {
        const r = ev.r;
        if (r.outcome === 'revision_requested' || r.outcome === 'eor_returned') {
          groups.push({ heading: labelFor(r.stage, r.round_no + 1), items: [] });
        } else if (r.outcome === 'approved') {
          const next = nextKeyAfter(r.stage);
          if (next) groups.push({ heading: labelFor(next, 1), items: [] });
        }
        // eor_rejected opens no segment — its paired eor_returned does.
      } else {
        const current = groups[groups.length - 1];
        if (current) current.items.push(ev.a);
      }
    }
    // Newest segment first, newest activity first inside each segment;
    // drop segments with no logged activity yet.
    return groups
      .map((g) => ({ ...g, items: [...g.items].reverse() }))
      .reverse()
      .filter((g) => g.items.length > 0);
  })();
  const clientSends = view.sends.filter((s) => s.stage === 'shop_client');
  const fabSends = view.sends.filter((s) => s.stage === 'fabrication');
  const sealSends = view.sends.filter((s) => s.stage === 'seal_sign');
  // Stage browsing: the arrows / step clicks view another stage's card
  // (read-only) without leaving the current stage's live card.
  const stageKeys = view.stages.map((s) => s.key);
  const viewedKey =
    browseKey && stageKeys.includes(browseKey) ? browseKey : view.current_stage;
  const viewedIdx = Math.max(0, stageKeys.indexOf(viewedKey));
  const isBrowsing = viewedKey !== view.current_stage;
  const goBrowse = (idx: number) => {
    const clamped = Math.max(0, Math.min(stageKeys.length - 1, idx));
    const key = stageKeys[clamped];
    if (!key) return;
    setBrowseKey(key === view.current_stage ? null : key);
  };
  const busy = action.isPending;
  // Display derivations: the stage card renders the VIEWED stage (the
  // current one, or the browsed one in read-only form).
  const displayStage = viewedKey;
  const viewedState = view.stages[viewedIdx]?.state ?? 'upcoming';
  const showLocked = isBrowsing && viewedState === 'upcoming';
  // OE-DELIVERY 2026-10-27: payment stages carry their milestone on
  // the stage row itself - no more legacy payment_10/60/30 keys.
  const viewedStageRow = view.stages[viewedIdx] ?? null;
  const dispMilestone = viewedStageRow?.milestone_id ? viewedStageRow : null;
  const dispGatePct = dispMilestone?.percent ?? null;
  const dispGateLabel = dispMilestone?.milestone_label ?? null;
  const dispGateAmount = dispMilestone?.amount ?? null;
  const dispGateEmailSent = dispMilestone?.email_sent_at ?? null;
  const dispInvSentAt = dispMilestone?.inv_sent_at ?? null;
  const dispGateReceivedAt = dispMilestone?.received_at ?? null;
  // OE-DELIVERY 2026-10-27: the viewed payment milestone's receipt
  // rows. The receipts section renders only on non-award milestones;
  // the award milestone keeps its single-step invoice + received flow.
  const dispMilestoneRow =
    view.milestones.find((m) => m.id === dispMilestone?.milestone_id) ?? null;
  const dispIsAward = dispMilestoneRow?.is_award ?? false;
  const dispBalance = dispMilestoneRow?.balance_percent ?? 0;
  const currentStageRow = view.stages.find((s) => s.key === stage) ?? null;
  const gatePct = currentStageRow?.percent ?? null;
  const gateAmount = currentStageRow?.amount ?? null;
  // OE-DELIVERY 2026-10-27: the current payment milestone's receipts,
  // for the partial-payment Next Action and gate line. The award
  // milestone never carries receipts in the panel, so it keeps the
  // single-step wording.
  const currentMilestoneRow =
    view.milestones.find((m) => m.id === currentStageRow?.milestone_id) ?? null;
  const currentMilestoneIsPayment =
    currentMilestoneRow !== null && !currentMilestoneRow.is_award;
  const currentMilestonePartial =
    currentMilestoneIsPayment &&
    currentMilestoneRow?.received_at === null &&
    (currentMilestoneRow?.received_percent ?? 0) > 0;
  // Label of the stage after the current one, for "advance to ..." text.
  const currentStageIdx = stageKeys.indexOf(stage);
  const nextStageLabel =
    currentStageIdx >= 0 ? (view.stages[currentStageIdx + 1]?.label ?? 'Complete') : 'Complete';
  // Label of the stage after seal_sign, for the seal card helper text.
  const sealStageIdx = stageKeys.indexOf('seal_sign');
  const sealNextLabel =
    sealStageIdx >= 0
      ? (view.stages[sealStageIdx + 1]?.label ?? 'the next stage')
      : 'the next stage';

  const nextAction =
    currentMilestonePartial
      ? `Partial payment received — ${fmtPct(currentMilestoneRow?.balance_percent ?? 0)}% balance remaining`
      : gatePct !== null
        ? 'Awaiting payment confirmation from Accounts'
        : stage === 'drafting'
        ? 'Engineering / drafting in progress — complete it or skip to shop drawings'
        : stage === 'shop_drawings'
          ? clientSends.length > 0
            ? 'Awaiting client approval of the shop drawings'
            : 'Send the shop drawings to the client for approval'
          : stage === 'seal_sign'
            ? 'Awaiting seal & sign by EOR'
            : stage === 'fabrication'
              ? 'Fabrication in progress'
              : stage === 'delivery'
                ? 'Delivery in progress'
                : stage === 'feedback'
                  ? view.feedback_available
                    ? 'Send the feedback request to the client'
                    : 'Feedback opens 30 days after delivery'
                  : 'Pipeline completed';

  const deliverySteps = [
    { key: 'dispatched', label: 'Dispatched' },
    { key: 'in_transit', label: 'In Transit' },
    { key: 'arrived', label: 'Arrived' },
  ];
  const deliveryIdx = ['pending', 'dispatched', 'in_transit', 'arrived'].indexOf(view.del_status);

  return (
    <div className="space-y-4 py-4">
      {/* ── Tracker ─────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-surface-primary p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-wide text-content-primary">
            POST-AWARD PIPELINE
          </h3>
          <div className="flex items-center gap-3">
            <div className="h-2 w-40 overflow-hidden rounded-full bg-surface-tertiary">
              <div
                className="h-full rounded-full bg-oe-blue transition-all"
                style={{ width: `${view.progress_pct}%` }}
              />
            </div>
            <span className="text-xs font-medium text-content-secondary">
              {view.progress_pct}% complete
            </span>
          </div>
        </div>
        <div className="flex items-start">
          {view.stages.map((s, i) => (
            <div
              key={s.key}
              className="relative flex flex-1 cursor-pointer flex-col items-center"
              title={`View ${s.label}`}
              onClick={() => goBrowse(i)}
            >
              {i > 0 && (
                <div
                  className={`absolute left-[-50%] top-5 h-0.5 w-full ${
                    s.state === 'done' || s.state === 'skipped' || s.state === 'current'
                      ? 'bg-semantic-success'
                      : 'bg-border'
                  }`}
                  style={{ zIndex: 0 }}
                />
              )}
              <div
                className={`relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                  isBrowsing && s.key === viewedKey
                    ? 'shadow-[0_0_0_4px] shadow-oe-blue/50 '
                    : ''
                }${
                  s.state === 'done'
                    ? 'border-semantic-success bg-semantic-success text-white'
                    : s.state === 'skipped'
                      ? 'border-semantic-warning bg-semantic-warning text-white'
                      : s.state === 'current'
                        ? 'border-oe-blue bg-oe-blue text-white shadow-[0_0_0_4px] shadow-oe-blue/20'
                        : 'border-border bg-surface-secondary text-content-tertiary'
                }`}
              >
                {s.state === 'done' ? (
                  <Check size={18} />
                ) : s.state === 'skipped' ? (
                  <SkipForward size={16} />
                ) : (
                  STAGE_ICONS[s.key] ??
                  (s.key.startsWith('payment_') ? <Wallet size={18} /> : <Circle size={14} />)
                )}
              </div>
              <div
                className={`mt-2 text-center text-xs font-medium ${
                  s.state === 'current'
                    ? 'text-oe-blue'
                    : s.state === 'done'
                      ? 'text-semantic-success'
                      : 'text-content-secondary'
                }`}
              >
                {s.label}
              </div>
              <div className="text-center text-[11px] text-content-tertiary">
                {s.state === 'done'
                  ? `Completed${s.completed_at ? ` · ${fmtDate(s.completed_at)}` : ''}`
                  : s.state === 'skipped'
                    ? 'Skipped'
                    : s.state === 'current'
                      ? 'Current'
                      : 'Upcoming'}
              </div>
            </div>
          ))}
        </div>
        {/* Stage browsing arrows — step through stages (10% Payment …
            Delivery, and any future stage) without leaving this tab. */}
        <div className="mt-4 flex items-center justify-end gap-2">
          <span className="mr-1 text-xs text-content-tertiary">
            {isBrowsing
              ? `Viewing ${view.stages[viewedIdx]?.label ?? viewedKey} (${viewedIdx + 1} of ${stageKeys.length})`
              : `Stage ${viewedIdx + 1} of ${stageKeys.length}`}
          </span>
          <button
            type="button"
            disabled={viewedIdx <= 0}
            onClick={() => goBrowse(viewedIdx - 1)}
            title="Previous stage"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border text-content-primary transition-colors hover:bg-surface-secondary disabled:opacity-40"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            disabled={viewedIdx >= stageKeys.length - 1}
            onClick={() => goBrowse(viewedIdx + 1)}
            title="Next stage"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border text-content-primary transition-colors hover:bg-surface-secondary disabled:opacity-40"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* ── Current stage card ─────────────────────────────────────── */}
        <div className="rounded-xl border border-border bg-surface-primary p-5 lg:col-span-2">
          {showLocked ? (
            <div className="py-6 text-center">
              <Clock size={36} className="mx-auto text-content-tertiary" />
              <h3 className="mt-3 text-base font-semibold text-content-primary">
                Stage: {view.stages[viewedIdx]?.label ?? viewedKey}
              </h3>
              <p className="mt-1 text-sm text-content-secondary">
                This stage has not started yet
                {viewedIdx > 0
                  ? ` — it unlocks after ${view.stages[viewedIdx - 1]?.label ?? 'the previous stage'} completes.`
                  : '.'}
              </p>
              <button
                type="button"
                onClick={() => setBrowseKey(null)}
                className="mt-3 text-sm font-medium text-oe-blue hover:underline"
              >
                ← Back to current stage
              </button>
            </div>
          ) : (
            <>
          {dispGatePct !== null && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">
                  Stage: {viewedStageRow?.label ?? 'Payment'}
                </h3>
                {isBrowsing ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    In Progress
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-xs text-content-secondary">Project Name</div>
                  <div className="font-medium text-content-primary">{view.project_name}</div>
                </div>
                <div>
                  <div className="text-xs text-content-secondary">Client</div>
                  <div className="font-medium text-content-primary">{view.client_name ?? '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-content-secondary">Contract Value</div>
                  <div className="font-medium text-content-primary">
                    {view.contract_value
                      ? `${view.currency ? `${view.currency} ` : ''}${view.contract_value}`
                      : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-content-secondary">Gate Amount</div>
                  <div className="font-medium text-content-primary">
                    {dispGatePct}% = {fmtMoney(dispGateAmount ?? view.gate_amounts[String(dispGatePct)], view.currency)}
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm">
                {dispGateEmailSent ? (
                  <>
                    <CheckCircle2 size={16} className="text-semantic-success" />
                    <span className="text-semantic-success">
                      Email sent to Accounts team with project details
                    </span>
                  </>
                ) : (
                  <>
                    <Mail size={16} className="text-content-tertiary" />
                    <span className="text-content-secondary">
                      Accounts email not recorded yet — it is sent when this gate opens
                    </span>
                  </>
                )}
              </div>
              {dispMilestoneRow && !dispIsAward && (
                <div className="mt-4">
                  <div className="mb-1 text-xs font-semibold text-content-primary">
                    Payment Schedule — {dispMilestoneRow.label}
                  </div>
                  <div className="mb-2 text-xs text-content-secondary">
                    {dispMilestoneRow.anchor_label} · Target {dispMilestoneRow.percent}%
                  </div>
                  <MilestoneReceipts
                    projectId={projectId}
                    milestone={dispMilestoneRow}
                    onSaved={(data) => queryClient.setQueryData(queryKey, data)}
                    readOnly={isBrowsing}
                  />
                </div>
              )}
              {isBrowsing ? (
                <div className="mt-4 flex items-center gap-2 rounded-lg bg-semantic-success/10 px-3 py-2.5 text-sm font-medium text-semantic-success">
                  <CheckCircle2 size={16} />
                  Payment received
                  {dispGateReceivedAt ? ` · ${fmtDateTime(dispGateReceivedAt)}` : ''}
                </div>
              ) : (
                <>
                  <div className="mt-4 flex gap-3">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        dispMilestone?.milestone_id &&
                        setInvoiceGate({
                          id: dispMilestone.milestone_id,
                          percent: dispGatePct ?? 0,
                          label: dispGateLabel ?? '',
                        })
                      }
                      className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-oe-blue px-4 py-3 text-sm font-semibold text-oe-blue transition-colors hover:bg-oe-blue/5 disabled:opacity-50"
                    >
                      <Mail size={16} /> Send {dispGatePct}% Invoice to Accountant
                    </button>
                    {dispIsAward ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          action.mutate({
                            path: 'payment-received/',
                            body: { milestone_id: dispMilestone?.milestone_id },
                          })
                        }
                        className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                      >
                        <Check size={18} /> Mark Payment Received
                      </button>
                    ) : dispBalance > 0 ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          dispMilestone?.milestone_id &&
                          action.mutate({
                            path: `milestones/${dispMilestone.milestone_id}/receipts/`,
                            body: { percent: dispBalance },
                          })
                        }
                        className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                      >
                        <Check size={18} /> Mark balance received ({fmtPct(dispBalance)}%)
                      </button>
                    ) : null}
                  </div>
                  <p className="mt-2 text-center text-xs text-content-tertiary">
                    Once marked, this will advance the project to {nextStageLabel}.
                  </p>
                </>
              )}
              {dispInvSentAt && (
                <p className="mt-2 flex items-center gap-1.5 text-xs text-content-secondary">
                  <Mail size={13} className="text-semantic-success" />
                  Invoice email sent to Accounting team ·{' '}
                  {fmtDateTime(dispInvSentAt)}
                </p>
              )}
            </>
          )}

          {displayStage === 'drafting' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">Stage: Engineering / Drafting</h3>
                {isBrowsing ? (
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      view.drafting_skipped
                        ? 'bg-semantic-warning/10 text-semantic-warning'
                        : 'bg-semantic-success/10 text-semantic-success'
                    }`}
                  >
                    {view.drafting_skipped ? 'Skipped' : 'Completed'}
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    In Progress
                  </span>
                )}
                {(viewRounds['drafting'] ?? 1) > 1 && (
                  <span className="rounded-full bg-semantic-warning/10 px-2.5 py-0.5 text-xs font-medium text-semantic-warning">
                    Round R{viewRounds['drafting']}
                  </span>
                )}
              </div>
              {view.pay10_received_at && (
                <div className="mb-4 rounded-lg bg-oe-blue/5 px-3 py-2 text-sm text-content-primary">
                  10% payment received on {fmtDate(view.pay10_received_at)}. Proceed to
                  engineering / drafting for shop drawings preparation.
                </div>
              )}
              {draftingEorReturn && !isBrowsing && (
                <div className="mb-4 rounded-lg bg-semantic-error/10 px-3 py-2.5 text-sm text-content-primary">
                  <span className="font-semibold">
                    Returned from EOR — rework round R{viewRounds['drafting'] ?? 1}.
                  </span>
                  {draftingEorReturn.comments ? (
                    <span className="mt-1 block text-content-secondary">
                      EOR: {draftingEorReturn.comments}
                    </span>
                  ) : null}
                </div>
              )}
              <div className="mb-4">
                <StageSendPanel
                  projectId={projectId}
                  sendStage="drafting"
                  heading="Send Drafting Files"
                  buttonLabel="Send Files"
                  roleOptions={['Engineer', 'Drafter', 'Consultant', 'Internal']}
                  defaultRole="Engineer"
                  multiRecipient
                  defaultSubject={`Engineering / Drafting files — ${view.project_name}`}
                  defaultSubjectForRole={(r) =>
                    r === 'Engineer'
                      ? `For engineering — ${view.project_name}`
                      : r === 'Drafter'
                        ? `For drafting — ${view.project_name}`
                        : `Engineering / Drafting files — ${view.project_name}`
                  }
                  disabled={isBrowsing}
                  disabledHint="This stage is complete — you are viewing its history."
                  onSent={(data) => queryClient.setQueryData(queryKey, data)}
                />
                <SendHistoryList sends={draftingSends} title="Sent History" />
                <RoundHistory revisions={viewRevisions} stage="drafting" />
              </div>
              {!isBrowsing && (
                <>
              <div className="mt-4">
                <label className={labelCls}>Request revision — what needs to change?</label>
                <textarea
                  className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
                  rows={2}
                  value={draftRevComment}
                  onChange={(e) => setDraftRevComment(e.target.value)}
                  placeholder="e.g. Re-check member sizes, connection details missing"
                />
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (!draftRevComment.trim()) {
                      addToast({
                        type: 'error',
                        title: 'Comment required',
                        message: 'Please write what needs to change.',
                      });
                      return;
                    }
                    action.mutate({
                      path: 'drafting/revision/',
                      body: { comments: draftRevComment.trim() },
                    });
                    setDraftRevComment('');
                  }}
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-semantic-warning px-4 py-2.5 text-sm font-semibold text-semantic-warning transition-colors hover:bg-semantic-warning/10 disabled:opacity-50"
                >
                  Request Revision — Round R{(viewRounds['drafting'] ?? 1) + 1}
                </button>
                <p className="mt-2 text-xs text-content-tertiary">
                  The stage stays open — revised files go out as new transmittals until the
                  review passes.
                </p>
              </div>
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => action.mutate({ path: 'drafting/skip/' })}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-semantic-warning px-4 py-3 text-sm font-semibold text-semantic-warning transition-colors hover:bg-semantic-warning/10 disabled:opacity-50"
                >
                  <SkipForward size={16} /> Skip drafting
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => action.mutate({ path: 'drafting/complete/' })}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-oe-blue px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  <Check size={16} /> Mark Engineering / Drafting Complete
                </button>
              </div>
              <p className="mt-2 text-xs text-content-tertiary">
                Not every project needs drafting — skip to go straight to shop drawings.
              </p>
                </>
              )}
            </>
          )}

          {displayStage === 'shop_drawings' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">Stage: Shop Drawings</h3>
                {isBrowsing ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    {clientSends.length > 0 ? 'In Review · Current' : 'Current'}
                  </span>
                )}
                {(viewRounds['shop_drawings'] ?? 1) > 1 && (
                  <span className="rounded-full bg-semantic-warning/10 px-2.5 py-0.5 text-xs font-medium text-semantic-warning">
                    Round R{viewRounds['shop_drawings']}
                  </span>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-sm font-semibold text-content-primary">
                      Send to Client for Approval
                    </span>
                    {clientSends.length > 0 ? (
                      <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                        Awaiting Client
                      </span>
                    ) : null}
                  </div>
                  <StageSendPanel
                    projectId={projectId}
                    sendStage="shop_client"
                    buttonLabel="Send to Client"
                    fixedRole="Client"
                    defaultSubject={`Shop drawings for approval — ${view.project_name}`}
                    disabled={isBrowsing}
                    disabledHint="This stage is complete — you are viewing its history."
                    onSent={(data) => queryClient.setQueryData(queryKey, data)}
                  />
                  <SendHistoryList sends={clientSends} title="Sent History" />
                  <RoundHistory revisions={viewRevisions} stage="shop_drawings" />
                </div>
                {isBrowsing ? (
                  view.client_approved_at ? (
                    <div className="flex items-center gap-2 rounded-lg bg-semantic-success/10 px-3 py-2.5 text-sm font-medium text-semantic-success">
                      <CheckCircle2 size={16} />
                      Client approved · {fmtDateTime(view.client_approved_at)}
                    </div>
                  ) : null
                ) : (
                  <>
                    <button
                      type="button"
                      disabled={busy || clientSends.length === 0}
                      onClick={() => action.mutate({ path: 'shop-drawings/client-approved/' })}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                    >
                      <Check size={18} /> Client Approved
                    </button>
                    <p className="text-center text-xs text-content-tertiary">
                      Click when the client confirms the shop drawings are approved. This unlocks
                      the Seal & Sign by EOR stage.
                    </p>
                    <div className="mt-4">
                      <label className={labelCls}>Request revision — what needs to change?</label>
                      <textarea
                        className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
                        rows={2}
                        value={shopRevComment}
                        onChange={(e) => setShopRevComment(e.target.value)}
                        placeholder="e.g. Increase connection plate thickness to 10mm"
                      />
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          if (!shopRevComment.trim()) {
                            addToast({
                              type: 'error',
                              title: 'Comment required',
                              message: 'Please write what needs to change.',
                            });
                            return;
                          }
                          action.mutate({
                            path: 'shop-drawings/revision/',
                            body: { comments: shopRevComment.trim() },
                          });
                          setShopRevComment('');
                        }}
                        className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-semantic-warning px-4 py-2.5 text-sm font-semibold text-semantic-warning transition-colors hover:bg-semantic-warning/10 disabled:opacity-50"
                      >
                        Request Revision — Round R{(viewRounds['shop_drawings'] ?? 1) + 1}
                      </button>
                      <p className="mt-2 text-xs text-content-tertiary">
                        The stage stays open — revised shop drawings go out as a new transmittal
                        until the client approves.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </>
          )}

          {displayStage === 'seal_sign' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">
                  Stage: Seal & Sign by EOR
                </h3>
                {isBrowsing ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    Current
                  </span>
                )}
              </div>
              {view.client_approved_at && (
                <div className="mb-4 rounded-lg bg-oe-blue/5 px-3 py-2 text-sm text-content-primary">
                  Client approved the shop drawings on {fmtDate(view.client_approved_at)}. Send
                  them to the EOR for seal &amp; sign.
                </div>
              )}
              <div className="space-y-4">
                <StageSendPanel
                  projectId={projectId}
                  sendStage="seal_sign"
                  heading="Send Drawings for Seal & Sign"
                  buttonLabel="Send for Seal & Sign"
                  fixedRole="EOR"
                  defaultSubject={`For seal & sign — ${view.project_name}`}
                  disabled={isBrowsing}
                  disabledHint="This stage is complete — you are viewing its history."
                  onSent={(data) => queryClient.setQueryData(queryKey, data)}
                />
                <SendHistoryList sends={sealSends} title="Sent History" />
                {isBrowsing ? (
                  view.seal_completed_at ? (
                    <div className="flex items-center gap-2 rounded-lg bg-semantic-success/10 px-3 py-2.5 text-sm font-medium text-semantic-success">
                      <CheckCircle2 size={16} />
                      Seal &amp; sign completed · {fmtDateTime(view.seal_completed_at)}
                    </div>
                  ) : null
                ) : (
                  <>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => action.mutate({ path: 'seal-sign/complete/' })}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                    >
                      <Stamp size={18} /> Mark Seal &amp; Sign Complete
                    </button>
                    <p className="text-center text-xs text-content-tertiary">
                      Click when the sealed &amp; signed drawings are received back from the
                      EOR. This unlocks the {sealNextLabel} stage.
                    </p>
                    <div className="mt-4 rounded-lg border border-semantic-error/30 px-3 py-3">
                      <label className={labelCls}>
                        EOR rejected — why? (returns to Engineering)
                      </label>
                      <textarea
                        className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
                        rows={2}
                        value={sealRejectComment}
                        onChange={(e) => setSealRejectComment(e.target.value)}
                        placeholder="e.g. Weld symbol missing on sheet S-03, load calculations re-check"
                      />
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          if (!sealRejectComment.trim()) {
                            addToast({
                              type: 'error',
                              title: 'Comment required',
                              message:
                                'Please write why the EOR rejected — it goes to Engineering as the rework brief.',
                            });
                            return;
                          }
                          action.mutate({
                            path: 'seal-sign/reject/',
                            body: { comments: sealRejectComment.trim() },
                          });
                          setSealRejectComment('');
                        }}
                        className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-semantic-error px-4 py-2.5 text-sm font-semibold text-semantic-error transition-colors hover:bg-semantic-error/10 disabled:opacity-50"
                      >
                        EOR Rejected → Back to Engineering
                      </button>
                      <p className="mt-2 text-xs text-content-tertiary">
                        The pipeline returns to Engineering / Drafting as a rework round with
                        this comment; shop client approval must come again before re-seal.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </>
          )}

          {displayStage === 'fabrication' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">Stage: Fabrication</h3>
                {isBrowsing ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    In Fabrication
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Vendor</label>
                  <input
                    className={inputCls}
                    value={fabVendor}
                    onChange={(e) => setFabVendor(e.target.value)}
                    disabled={isBrowsing}
                    placeholder="e.g. USFF Steel Works"
                  />
                </div>
                <div>
                  <label className={labelCls}>Fabrication Status</label>
                  <select
                    className={inputCls}
                    value={fabStatus}
                    onChange={(e) => setFabStatus(e.target.value)}
                    disabled={isBrowsing}
                  >
                    <option value="started">Started</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Start Date</label>
                  <input
                    className={inputCls}
                    type="date"
                    value={fabStart}
                    onChange={(e) => setFabStart(e.target.value)}
                    disabled={isBrowsing}
                  />
                </div>
                <div>
                  <label className={labelCls}>Expected Completion</label>
                  <input
                    className={inputCls}
                    type="date"
                    value={fabExpected}
                    onChange={(e) => setFabExpected(e.target.value)}
                    disabled={isBrowsing}
                  />
                </div>
              </div>
              <div className="mt-4">
                <StageSendPanel
                  projectId={projectId}
                  sendStage="fabrication"
                  heading="Send Fabrication Files"
                  buttonLabel="Send Files"
                  roleOptions={['Vendor', 'Partner']}
                  defaultRole="Vendor"
                  defaultSubject={`Fabrication files — ${view.project_name}`}
                  disabled={isBrowsing}
                  disabledHint="This stage is complete — you are viewing its history."
                  onSent={(data) => queryClient.setQueryData(queryKey, data)}
                />
                <SendHistoryList sends={fabSends} title="Sent History" />
              </div>
              {!isBrowsing && (
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    action.mutate({
                      path: 'fabrication/',
                      body: {
                        vendor: fabVendor || null,
                        start_date: fabStart || null,
                        expected_date: fabExpected || null,
                        status: fabStatus,
                      },
                    })
                  }
                  className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-content-primary transition-colors hover:bg-surface-secondary disabled:opacity-50"
                >
                  Save Details
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => action.mutate({ path: 'fabrication/complete/' })}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  <Check size={16} /> Mark Fabrication Complete
                </button>
              </div>
              )}
            </>
          )}

          {displayStage === 'delivery' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">Stage: Delivery</h3>
                {isBrowsing ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    Current
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Shipment Ref</label>
                  <input
                    className={inputCls}
                    value={delRef}
                    onChange={(e) => setDelRef(e.target.value)}
                    disabled={isBrowsing}
                    placeholder="e.g. SHP-2026-041"
                  />
                </div>
                <div>
                  <label className={labelCls}>Tracking Number</label>
                  <input
                    className={inputCls}
                    value={delTracking}
                    onChange={(e) => setDelTracking(e.target.value)}
                    disabled={isBrowsing}
                    placeholder="e.g. 1Z8845W90312345678"
                  />
                </div>
                <div>
                  <label className={labelCls}>Carrier</label>
                  <input
                    className={inputCls}
                    value={delCarrier}
                    onChange={(e) => setDelCarrier(e.target.value)}
                    disabled={isBrowsing}
                    placeholder="e.g. ABC Logistics"
                  />
                </div>
                <div>
                  <label className={labelCls}>Destination</label>
                  <input
                    className={inputCls}
                    value={delDest}
                    onChange={(e) => setDelDest(e.target.value)}
                    disabled={isBrowsing}
                    placeholder="e.g. Site — Palm Beach"
                  />
                </div>
                <div>
                  <label className={labelCls}>ETA</label>
                  <input
                    className={inputCls}
                    type="date"
                    value={delEta}
                    onChange={(e) => setDelEta(e.target.value)}
                    disabled={isBrowsing}
                  />
                </div>
              </div>
              {!isBrowsing && (
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  action.mutate({
                    path: 'delivery/',
                    body: {
                      shipment_ref: delRef || null,
                      tracking_number: delTracking || null,
                      carrier: delCarrier || null,
                      destination: delDest || null,
                      eta: delEta || null,
                    },
                  })
                }
                className="mt-3 w-full rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-content-primary transition-colors hover:bg-surface-secondary disabled:opacity-50"
              >
                Save Delivery Details
              </button>
              )}

              <div className="mt-5 space-y-0">
                {deliverySteps.map((step, i) => {
                  const reached = deliveryIdx > i;
                  const isCurrent = deliveryIdx === i + 1;
                  return (
                    <div key={step.key} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div
                          className={`flex h-6 w-6 items-center justify-center rounded-full ${
                            reached
                              ? 'bg-semantic-success text-white'
                              : 'border border-border bg-surface-secondary text-content-tertiary'
                          }`}
                        >
                          {reached ? <Check size={13} /> : <Circle size={10} />}
                        </div>
                        {i < deliverySteps.length - 1 && (
                          <div className={`h-6 w-0.5 ${deliveryIdx > i + 1 ? 'bg-semantic-success' : 'bg-border'}`} />
                        )}
                      </div>
                      <div className="pb-4">
                        <div
                          className={`text-sm font-medium ${
                            reached || isCurrent ? 'text-content-primary' : 'text-content-tertiary'
                          }`}
                        >
                          {step.label}
                        </div>
                        {!reached && !isBrowsing && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              action.mutate({ path: 'delivery/', body: { status: step.key } })
                            }
                            className="mt-0.5 text-xs font-medium text-oe-blue hover:underline disabled:opacity-50"
                          >
                            Mark {step.label.toLowerCase()}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {isBrowsing ? (
                view.delivered_at ? (
                  <div className="mt-2 flex items-center gap-2 rounded-lg bg-semantic-success/10 px-3 py-2.5 text-sm font-medium text-semantic-success">
                    <CheckCircle2 size={16} />
                    Delivered &amp; accepted · {fmtDateTime(view.delivered_at)}
                  </div>
                ) : null
              ) : (
                <>
                  <button
                    type="button"
                    disabled={busy || view.del_status !== 'arrived'}
                    onClick={() => action.mutate({ path: 'delivery/delivered/' })}
                    className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    <Check size={18} /> Delivered &amp; Accepted
                  </button>
                  {view.del_status !== 'arrived' && (
                    <p className="mt-2 text-center text-xs text-content-tertiary">
                      Available once the delivery has arrived at site.
                    </p>
                  )}
                </>
              )}
            </>
          )}

          {displayStage === 'feedback' && (
            <>
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-base font-semibold text-content-primary">Stage: Feedback</h3>
                {view.feedback_sent_at ? (
                  <span className="rounded-full bg-semantic-success/10 px-2.5 py-0.5 text-xs font-medium text-semantic-success">
                    Completed
                  </span>
                ) : view.feedback_available ? (
                  <span className="rounded-full bg-oe-blue/10 px-2.5 py-0.5 text-xs font-medium text-oe-blue">
                    Current
                  </span>
                ) : (
                  <span className="rounded-full bg-semantic-warning/10 px-2.5 py-0.5 text-xs font-medium text-semantic-warning">
                    Locked
                  </span>
                )}
              </div>
              {view.feedback_sent_at ? (
                <div className="flex items-center gap-2 rounded-lg bg-semantic-success/10 px-3 py-2.5 text-sm font-medium text-semantic-success">
                  <CheckCircle2 size={16} />
                  Feedback request sent to {view.feedback_email} ·{' '}
                  {fmtDateTime(view.feedback_sent_at)}
                </div>
              ) : (
                <div className="relative">
                  <div className="space-y-3">
                    <div>
                      <label className={labelCls}>Client email</label>
                      <input
                        className={inputCls}
                        value={fbEmail}
                        onChange={(e) => setFbEmail(e.target.value)}
                        placeholder="client@company.com"
                        disabled={!view.feedback_available}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>Subject</label>
                      <input
                        className={inputCls}
                        value={
                          view.feedback_available
                            ? fbSubject
                            : `We value your feedback — ${view.project_name}`
                        }
                        onChange={(e) => setFbSubject(e.target.value)}
                        disabled={!view.feedback_available}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>Message</label>
                      <textarea
                        className="w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary"
                        rows={6}
                        value={
                          view.feedback_available
                            ? fbMessage
                            : `Dear ${view.client_name ?? 'Client'},\n\nThank you for your business. The project ${view.project_name} was delivered recently, and we would love to hear your feedback about our work. A short reply to this email is all it takes.\n\nThank you!`
                        }
                        onChange={(e) => setFbMessage(e.target.value)}
                        disabled={!view.feedback_available}
                      />
                    </div>
                    <button
                      type="button"
                      disabled={busy || !view.feedback_available || !fbEmail.trim().includes('@')}
                      onClick={() =>
                        action.mutate({
                          path: 'feedback/send/',
                          body: {
                            email: fbEmail.trim(),
                            subject: fbSubject.trim() || null,
                            message: fbMessage.trim() || null,
                          },
                        })
                      }
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-semantic-success px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                    >
                      <Send size={16} /> Send Feedback Request
                    </button>
                    <p className="text-center text-xs text-content-tertiary">
                      Emails the client asking for their feedback. This completes the pipeline.
                    </p>
                  </div>
                  {!view.feedback_available && (
                    <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/80 p-4">
                      <div className="text-center">
                        <Clock size={30} className="mx-auto text-white/80" />
                        <p className="mt-2 text-sm font-semibold text-white">
                          Feedback stage is locked
                        </p>
                        <p className="mt-1 text-sm text-white/85">
                          Delivered on {fmtDate(view.delivered_at)}. It opens on{' '}
                          <b>{fmtDate(view.feedback_unlock_at)}</b> — 30 days after delivery.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {displayStage === 'completed' && (
            <div className="py-6 text-center">
              <CheckCircle2 size={40} className="mx-auto text-semantic-success" />
              <h3 className="mt-3 text-base font-semibold text-content-primary">
                Pipeline Completed
              </h3>
              <p className="mt-1 text-sm text-content-secondary">
                Delivered &amp; accepted on {fmtDate(view.delivered_at)}. All stages are complete.
              </p>
            </div>
          )}
            </>
          )}
        </div>

      {invoiceGate !== null && (
        <InvoiceEmailModal
          projectId={projectId}
          milestone={invoiceGate}
          projectName={view.project_name}
          amountText={fmtMoney(
            view.milestones?.find((m) => m.id === invoiceGate.id)?.amount ??
              view.gate_amounts[String(invoiceGate.percent)],
            view.currency,
          )}
          onClose={() => setInvoiceGate(null)}
          onSent={(data) => queryClient.setQueryData(queryKey, data)}
        />
      )}

        {/* ── Right column: summary + activity ─────────────────────────── */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface-primary p-5">
            <h3 className="mb-3 text-sm font-semibold text-content-primary">Stage Summary</h3>
            <div className="flex items-center justify-between text-sm">
              <span className="text-content-secondary">Completion</span>
              <span className="font-medium text-content-primary">{view.progress_pct}%</span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-tertiary">
              <div
                className="h-full rounded-full bg-oe-blue transition-all"
                style={{ width: `${view.progress_pct}%` }}
              />
            </div>
            <div className="mt-4 text-sm">
              <div className="text-xs text-content-secondary">Next Action</div>
              <div className="font-medium text-content-primary">{nextAction}</div>
            </div>
            {gatePct !== null && (
              <div className="mt-3 rounded-lg bg-oe-blue/5 px-3 py-2 text-xs text-content-secondary">
                Gate amount: {gatePct}% = {fmtMoney(gateAmount ?? view.gate_amounts[String(gatePct)], view.currency)}
                {currentMilestoneIsPayment
                  ? ` · Received: ${fmtPct(currentMilestoneRow?.received_percent ?? 0)}%`
                  : ''}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-border bg-surface-primary p-5">
            <h3 className="mb-3 text-sm font-semibold text-content-primary">Stage Activity</h3>
            {activityGroups.length === 0 ? (
              <p className="flex items-center gap-2 text-sm text-content-tertiary">
                <Clock size={14} /> No activity yet
              </p>
            ) : (
              <div className="space-y-4">
                {activityGroups.map((g, gi) => (
                  <div key={`${g.heading}-${gi}`}>
                    <div
                      className={`mb-2 text-xs font-semibold ${
                        g.heading.startsWith('Round')
                          ? 'text-semantic-warning'
                          : 'text-content-secondary'
                      }`}
                    >
                      {g.heading}
                    </div>
                    <div className="space-y-3">
                      {g.items.map((a) => (
                        <div key={a.id} className="flex gap-2.5">
                          <span className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full bg-oe-blue" />
                          <div>
                            <div className="text-sm text-content-primary">{a.text}</div>
                            <div className="text-xs text-content-tertiary">
                              {fmtDateTime(a.created_at)}
                              {a.actor_name ? ` · ${a.actor_name}` : ''}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
