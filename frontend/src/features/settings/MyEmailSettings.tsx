// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
//
// MyEmailSettings — per-user SMTP configuration.
//
// When enabled, task-assignment (and future per-user) emails send through
// THIS user's mail provider with their own From address, instead of the
// system SMTP. The password is encrypted at rest server-side and never
// returned by the API.

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Mail } from 'lucide-react';

import { apiGet, apiPut } from '@/shared/lib/api';
import { Card, CardContent, CardHeader } from '@/shared/ui/Card';
import { Button } from '@/shared/ui/Button';
import { useToastStore } from '@/stores/useToastStore';

interface EmailSettings {
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_from: string | null;
  smtp_tls: boolean;
  smtp_enabled: boolean;
  smtp_use_for_automated: boolean;
  has_password: boolean;
}

const inputCls =
  'w-full rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm text-content-primary placeholder:text-content-tertiary focus:outline-none focus:ring-2 focus:ring-oe-blue/30 focus:border-oe-blue transition-colors';

export function MyEmailSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);

  const { data, isLoading } = useQuery({
    queryKey: ['my-email-settings'],
    queryFn: () => apiGet<EmailSettings>('/v1/users/me/email-settings/'),
    retry: false,
  });

  const [form, setForm] = useState({
    smtp_host: '',
    smtp_port: '587',
    smtp_username: '',
    smtp_password: '',
    smtp_from: '',
    smtp_tls: true,
    smtp_enabled: false,
    smtp_use_for_automated: false,
  });

  useEffect(() => {
    if (data) {
      setForm({
        smtp_host: data.smtp_host ?? '',
        smtp_port: String(data.smtp_port ?? 587),
        smtp_username: data.smtp_username ?? '',
        smtp_password: '',
        smtp_from: data.smtp_from ?? '',
        smtp_tls: data.smtp_tls,
        smtp_enabled: data.smtp_enabled,
        smtp_use_for_automated: data.smtp_use_for_automated ?? false,
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      apiPut<EmailSettings>('/v1/users/me/email-settings/', {
        smtp_host: form.smtp_host.trim() || null,
        smtp_port: parseInt(form.smtp_port, 10) || null,
        smtp_username: form.smtp_username.trim() || null,
        // Only send password when the user typed a new one.
        smtp_password: form.smtp_password || null,
        smtp_from: form.smtp_from.trim() || null,
        smtp_tls: form.smtp_tls,
        smtp_enabled: form.smtp_enabled,
        smtp_use_for_automated: form.smtp_use_for_automated,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-email-settings'] });
      setForm((f) => ({ ...f, smtp_password: '' }));
      addToast({
        type: 'success',
        title: t('settings.email_saved', { defaultValue: 'Email settings saved' }),
      });
    },
    onError: () => {
      addToast({
        type: 'error',
        title: t('settings.email_save_failed', { defaultValue: 'Could not save email settings' }),
      });
    },
  });

  const set = (k: keyof typeof form, v: string | boolean) =>
    setForm((f) => ({ ...f, [k]: v }));

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        title={t('settings.my_email_title', { defaultValue: 'My Email Settings' })}
        subtitle={t('settings.my_email_subtitle', {
          defaultValue:
            'Send task emails from your own address. When enabled, recipients see your email as the sender instead of the company address.',
        })}
      />
      <CardContent>
        {isLoading ? (
          <div className="flex items-center gap-2 text-content-tertiary text-sm">
            <Loader2 size={16} className="animate-spin" />
            {t('common.loading', { defaultValue: 'Loading…' })}
          </div>
        ) : (
          <div className="space-y-4 max-w-md">
            <label className="flex items-center gap-2 text-sm text-content-primary cursor-pointer">
              <input
                type="checkbox"
                checked={form.smtp_enabled}
                onChange={(e) => set('smtp_enabled', e.target.checked)}
                className="rounded border-border"
              />
              {t('settings.email_enable', {
                defaultValue: 'Send emails from my own address',
              })}
            </label>
            <label className="flex items-start gap-2 text-sm text-content-primary cursor-pointer">
              <input
                type="checkbox"
                checked={form.smtp_use_for_automated}
                onChange={(e) => set('smtp_use_for_automated', e.target.checked)}
                className="rounded border-border mt-0.5"
              />
              <span>
                {t('settings.email_use_for_automated', {
                  defaultValue: 'Use my email for automated notifications',
                })}
                <span className="block text-xs text-content-secondary mt-0.5">
                  {t('settings.email_use_for_automated_hint', {
                    defaultValue:
                      'When off, notifications are sent from the system address (your Sent box stays clean). When on, they are sent from your own address.',
                  })}
                </span>
              </span>
            </label>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-content-primary mb-1">
                  {t('settings.email_smtp_host', { defaultValue: 'SMTP Host' })}
                </label>
                <input
                  className={inputCls}
                  placeholder="smtp.zoho.com"
                  value={form.smtp_host}
                  onChange={(e) => set('smtp_host', e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-content-primary mb-1">
                  {t('settings.email_smtp_port', { defaultValue: 'Port' })}
                </label>
                <input
                  className={inputCls}
                  placeholder="587"
                  inputMode="numeric"
                  value={form.smtp_port}
                  onChange={(e) => set('smtp_port', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-content-primary mb-1">
                {t('settings.email_smtp_user', { defaultValue: 'SMTP Username' })}
              </label>
              <input
                className={inputCls}
                placeholder="you@company.com"
                autoComplete="username"
                value={form.smtp_username}
                onChange={(e) => set('smtp_username', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-content-primary mb-1">
                {t('settings.email_smtp_password', { defaultValue: 'SMTP Password' })}
              </label>
              <input
                type="password"
                className={inputCls}
                autoComplete="new-password"
                placeholder={
                  data?.has_password
                    ? t('settings.email_password_set', { defaultValue: '•••••••• (saved — leave blank to keep)' })
                    : t('settings.email_password_hint', { defaultValue: 'App password if 2FA is on' })
                }
                value={form.smtp_password}
                onChange={(e) => set('smtp_password', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-content-primary mb-1">
                {t('settings.email_from', { defaultValue: 'From Address' })}
              </label>
              <input
                className={inputCls}
                placeholder="you@company.com"
                value={form.smtp_from}
                onChange={(e) => set('smtp_from', e.target.value)}
              />
            </div>

            <label className="flex items-center gap-2 text-sm text-content-primary cursor-pointer">
              <input
                type="checkbox"
                checked={form.smtp_tls}
                onChange={(e) => set('smtp_tls', e.target.checked)}
                className="rounded border-border"
              />
              {t('settings.email_tls', {
                defaultValue: 'Use STARTTLS (port 587)',
              })}
            </label>

            <div className="flex items-center gap-2 pt-1">
              <Button
                variant="primary"
                loading={save.isPending}
                onClick={() => save.mutate()}
                icon={<Mail size={14} />}
              >
                {t('common.save', { defaultValue: 'Save' })}
              </Button>
            </div>

            <p className="text-xs text-content-tertiary">
              {t('settings.email_note', {
                defaultValue:
                  'Zoho: smtp.zoho.com:587 (or :465). Gmail: smtp.gmail.com:587 with an App Password. Port 465 uses implicit TLS.',
              })}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
