'use client';

import {useTransition} from 'react';
import {useTranslations} from 'next-intl';

import {Button, Dialog} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {deleteTableAction} from '../actions';
import type {AdminTable} from '../types';

export interface DeleteTableDialogProps {
  table: AdminTable;
  locale: AppLocale;
  onClose: () => void;
  /** Called with an already-translated toast message once the row is gone. */
  onDeleted: (message: string) => void;
  /** Called with the translated failure message when the API refuses. */
  onFailed: (message: string) => void;
}

/**
 * Confirmation for a destructive, irreversible action: deleting a table takes
 * its scan history with it, so the guest-facing consequence is spelled out
 * rather than reduced to "Are you sure?".
 */
export function DeleteTableDialog({
  table,
  locale,
  onClose,
  onDeleted,
  onFailed
}: DeleteTableDialogProps) {
  const t = useTranslations('tables.admin');
  const tCommon = useTranslations('common');
  const [isPending, startTransition] = useTransition();

  function confirm() {
    startTransition(async () => {
      const result = await deleteTableAction(locale, table.id);
      if (result.ok) {
        onDeleted(t('toast.deleted'));
      } else {
        onFailed(result.message || t('toast.failed'));
      }
    });
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title={t('delete.title')}
      closeLabel={tCommon('actions.close')}
      description={t('delete.description', {name: table.label || `#${table.number}`})}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            {tCommon('actions.cancel')}
          </Button>
          <Button variant="danger" onClick={confirm} disabled={isPending}>
            {tCommon('actions.delete')}
          </Button>
        </>
      }
    />
  );
}
