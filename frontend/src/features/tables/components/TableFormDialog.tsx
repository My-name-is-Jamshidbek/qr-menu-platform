'use client';

import {useId, useState, useTransition} from 'react';
import {useTranslations} from 'next-intl';

import {Button, Dialog, Input} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {saveTableAction} from '../actions';
import type {AdminTable, TableFieldErrors, TableInput} from '../types';

export interface TableFormDialogProps {
  /** `null` puts the dialog in create mode. */
  table: AdminTable | null;
  locale: AppLocale;
  onClose: () => void;
  /** Called after a successful write, with an already-translated toast message. */
  onSaved: (message: string) => void;
}

interface FormState {
  number: string;
  label: string;
  isActive: boolean;
}

/** A new table is active and unnumbered until told otherwise. */
function initialForm(table: AdminTable | null): FormState {
  // `label` and `is_active` are optional in the schema (the API defaults them),
  // so the form supplies the same defaults rather than binding `undefined` to a
  // controlled input.
  return table
    ? {number: String(table.number), label: table.label ?? '', isActive: table.is_active ?? true}
    : {number: '', label: '', isActive: true};
}

/**
 * Create and edit share one dialog: the fields and their rules are identical.
 *
 * Mounted only while it is open, and keyed by the table being edited, so the
 * initial state below is the seeding logic — no effect has to reset the fields
 * when the administrator moves from one row to the next.
 */
export function TableFormDialog({table, locale, onClose, onSaved}: TableFormDialogProps) {
  const t = useTranslations('tables.admin');
  const tCommon = useTranslations('common');
  const formId = useId();
  const [form, setForm] = useState<FormState>(() => initialForm(table));
  const [fieldErrors, setFieldErrors] = useState<TableFieldErrors>({});
  const [formError, setFormError] = useState('');
  const [isPending, startTransition] = useTransition();

  function submit() {
    const number = Number(form.number);

    // The API enforces this too; checking here keeps a typo from costing a
    // round trip and lets the message be one of ours rather than DRF's.
    if (!Number.isInteger(number) || number < 1) {
      setFieldErrors({number: t('form.numberHint')});
      return;
    }

    const input: TableInput = {number, label: form.label.trim(), is_active: form.isActive};

    startTransition(async () => {
      const result = await saveTableAction(locale, table?.id ?? null, input);

      if (result.ok) {
        onSaved(t(table ? 'toast.updated' : 'toast.created'));
        return;
      }

      setFieldErrors(result.fieldErrors);
      setFormError(result.message);
    });
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={t(table ? 'form.editTitle' : 'form.createTitle')}
      closeLabel={tCommon('actions.close')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            {tCommon('actions.cancel')}
          </Button>
          <Button variant="primary" type="submit" form={formId} disabled={isPending}>
            {isPending ? tCommon('state.saving') : tCommon('actions.save')}
          </Button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="flex flex-col gap-5"
      >
        <Input
          label={t('form.number')}
          hint={t('form.numberHint')}
          error={fieldErrors.number}
          type="number"
          inputMode="numeric"
          min={1}
          numeric
          required
          autoFocus
          value={form.number}
          onChange={(event) => setForm((current) => ({...current, number: event.target.value}))}
        />

        <Input
          label={t('form.label')}
          hint={t('form.labelHint')}
          error={fieldErrors.label}
          labelSuffix={tCommon('form.optional')}
          maxLength={60}
          value={form.label}
          onChange={(event) => setForm((current) => ({...current, label: event.target.value}))}
        />

        <label className="flex items-start gap-3 text-body text-cream">
          <input
            type="checkbox"
            checked={form.isActive}
            onChange={(event) =>
              setForm((current) => ({...current, isActive: event.target.checked}))
            }
            className="mt-1 size-5 shrink-0 accent-[var(--gold-400)]"
          />
          <span className="flex flex-col gap-1">
            <span>{t('form.isActive')}</span>
            <span className="text-label text-muted normal-case tracking-normal">
              {t('form.isActiveHint')}
            </span>
          </span>
        </label>

        {formError ? (
          <p role="alert" className="text-body text-danger-text">
            {formError}
          </p>
        ) : null}
      </form>
    </Dialog>
  );
}
