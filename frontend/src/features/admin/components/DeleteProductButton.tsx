'use client';

import {useTranslations} from 'next-intl';
import {useState} from 'react';

import {Button, Dialog} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {deleteProductAction} from '../actions';

import {SubmitButton} from './SubmitButton';

/**
 * Deletion behind a confirmation.
 *
 * Products are hard-deleted and their stored images go with them, so the
 * destructive step is never one click away, and the dialog names the product
 * rather than asking "are you sure?" about nothing in particular.
 */
export interface DeleteProductButtonProps {
  locale: AppLocale;
  productId: number;
  productName: string;
  /** `sm` in a table row, `md` on the edit screen. */
  size?: 'sm' | 'md';
}

export function DeleteProductButton({
  locale,
  productId,
  productName,
  size = 'sm'
}: DeleteProductButtonProps) {
  const t = useTranslations('admin.delete');
  const tCommon = useTranslations('common');
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size={size}
        onClick={() => setOpen(true)}
        data-testid="admin-delete-product"
        aria-label={t('actionNamed', {name: productName})}
        className="text-danger-text hover:bg-danger/15"
      >
        {t('action')}
      </Button>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title={t('title')}
        description={t('description', {name: productName})}
        closeLabel={tCommon('actions.close')}
        footer={
          <form action={deleteProductAction} className="flex flex-wrap justify-end gap-3">
            <input type="hidden" name="locale" value={locale} />
            <input type="hidden" name="id" value={productId} />

            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              {t('cancel')}
            </Button>
            <SubmitButton
              variant="danger"
              data-testid="admin-confirm-delete"
              label={t('confirm')}
            />
          </form>
        }
      />
    </>
  );
}
