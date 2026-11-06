# OE-DELIVERY 2026-11-03-admin-create-user (frontend): "Create account" on the Users page.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:120])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('api.ts', [(
    """export async function sendInviteLink(data: InviteLinkPayload): Promise<InviteLinkResult> {""",
    """/** Admin creates a ready-to-use account (OE-DELIVERY 2026-11-03-admin-create-user). */
export async function createUserAccount(data: { email: string; full_name: string; password: string; role: string }): Promise<{ id: string; email: string }> {
  return apiPost<{ id: string; email: string }>('/v1/users/create/', data);
}

export async function sendInviteLink(data: InviteLinkPayload): Promise<InviteLinkResult> {""",
)])

MODAL = r'''/* ── Create Account Modal (OE-DELIVERY 2026-11-03-admin-create-user) ──
 * The admin sets name, email, a first password and the role; the account is
 * active at once (no email needed). The user can change the password later. */
function CreateAccountModal({
  onClose,
  onSubmit,
  isPending,
}: {
  onClose: () => void;
  onSubmit: (data: { email: string; full_name: string; password: string; role: string }) => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'editor' });
  const [show, setShow] = useState(false);
  const pwOk = form.password.length >= 8 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password);
  const canSubmit = !isPending && !!form.full_name.trim() && /.+@.+\..+/.test(form.email) && pwOk;
  return (
    <WideModal
      open
      onClose={onClose}
      title={t('users.create_account', { defaultValue: 'Create account' })}
      size="sm"
      busy={isPending}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </Button>
          <Button variant="primary" icon={<UserPlus size={14} />} disabled={!canSubmit} loading={isPending} onClick={() => onSubmit({ ...form, full_name: form.full_name.trim(), email: form.email.trim() })}>
            {t('users.create_account', { defaultValue: 'Create account' })}
          </Button>
        </>
      }
    >
      <div className="space-y-4" data-testid="create-account-form">
        <p className="text-sm text-content-secondary">
          {t('users.create_account_hint', { defaultValue: 'The account works straight away - no email or approval needed. Give the person their email and this first password; they can change it under their profile.' })}
        </p>
        <div>
          <label htmlFor="ca_name" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.full_name', { defaultValue: 'Full Name' })}</label>
          <input id="ca_name" className={inputCls} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoFocus data-testid="ca-name" />
        </div>
        <div>
          <label htmlFor="ca_email" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.email', { defaultValue: 'Email' })}</label>
          <input id="ca_email" type="email" className={inputCls} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@company.com" data-testid="ca-email" />
        </div>
        <div>
          <label htmlFor="ca_pw" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.first_password', { defaultValue: 'First password' })}</label>
          <div className="flex gap-2">
            <input id="ca_pw" type={show ? 'text' : 'password'} className={inputCls} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" data-testid="ca-password" />
            <Button variant="ghost" size="sm" onClick={() => setShow((v) => !v)}>{show ? t('common.hide', { defaultValue: 'Hide' }) : t('common.show', { defaultValue: 'Show' })}</Button>
          </div>
          <p className={clsx('mt-1 text-[11px]', form.password && !pwOk ? 'text-semantic-error' : 'text-content-tertiary')}>
            {t('users.password_rule', { defaultValue: 'At least 8 characters, with a letter and a digit.' })}
          </p>
        </div>
        <div>
          <label htmlFor="ca_role" className="mb-1 block text-xs font-medium text-content-secondary">{t('users.role', { defaultValue: 'Role' })}</label>
          <select id="ca_role" className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} data-testid="ca-role">
            <option value="admin">{t('users.role_admin', { defaultValue: 'Admin - full access, manages users' })}</option>
            <option value="manager">{t('users.role_manager', { defaultValue: 'Manager' })}</option>
            <option value="editor">{t('users.role_editor', { defaultValue: 'Editor - can take off and edit' })}</option>
            <option value="viewer">{t('users.role_viewer', { defaultValue: 'Viewer - read only' })}</option>
          </select>
        </div>
      </div>
    </WideModal>
  );
}

/* ── Create Custom Role Modal ──────────────────────────────────────────'''

patch('UserManagementPage.tsx', [
    ("""/* ── Create Custom Role Modal ──────────────────────────────────────────""", MODAL),
    ("""            {isAdmin && (
              <Button
                variant="primary"
                size="sm"
                icon={<UserPlus size={14} />}
                onClick={() => setShowInvite(true)}
              >""", """            {isAdmin && (
              <Button
                variant="primary"
                size="sm"
                icon={<UserPlus size={14} />}
                onClick={() => setShowCreateAccount(true)}
                data-testid="users-create-account"
              >
                {t('users.create_account', { defaultValue: 'Create account' })}
              </Button>
            )}
            {isAdmin && (
              <Button
                variant="ghost"
                size="sm"
                icon={<UserPlus size={14} />}
                onClick={() => setShowInvite(true)}
              >"""),
    ("""  const inviteMut = useMutation({""", """  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const createAccountMut = useMutation({
    mutationFn: createUserAccount,
    onSuccess: (u) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowCreateAccount(false);
      addToast({ type: 'success', title: t('users.account_created', { defaultValue: 'Account created' }), message: u.email });
    },
    onError: (e: Error) => {
      addToast({ type: 'error', title: t('common.error', { defaultValue: 'Error' }), message: e.message });
    },
  });

  const inviteMut = useMutation({"""),
    ("""      {/* Invite Modal */}
      {showInvite && (""", """      {showCreateAccount && (
        <CreateAccountModal
          onClose={() => setShowCreateAccount(false)}
          onSubmit={(data) => createAccountMut.mutate(data)}
          isPending={createAccountMut.isPending}
        />
      )}

      {/* Invite Modal */}
      {showInvite && ("""),
])
p = ROOT / 'UserManagementPage.tsx'
s = p.read_text(encoding='utf-8')
a = s.index("import {\n", s.index("import { apiGet } from '@/shared/lib/api';"))
s = s[:a] + "import {\n  createUserAccount,\n" + s[a + len("import {\n"):]
p.write_text(s, encoding='utf-8')
print('ok')
