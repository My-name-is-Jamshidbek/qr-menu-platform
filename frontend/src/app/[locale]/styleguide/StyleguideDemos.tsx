'use client';

import {useState} from 'react';
import {useTranslations} from 'next-intl';

import {Button, Dialog, Input, Select, Textarea, ToastProvider, useToast} from '@/components/ui';

/** Buttons that raise each toast tone, so the live region can be reviewed for real. */
function ToastTriggers() {
  const t = useTranslations('common');
  const {show} = useToast();

  return (
    <div className="flex flex-wrap gap-3">
      <Button size="sm" onClick={() => show({message: t('state.saved'), tone: 'success'})}>
        {t('state.saved')}
      </Button>
      <Button size="sm" onClick={() => show({message: t('state.saving'), tone: 'info'})}>
        {t('state.saving')}
      </Button>
      <Button
        size="sm"
        variant="danger"
        onClick={() => show({message: t('errors.saveFailed'), tone: 'danger'})}
      >
        {t('errors.saveFailed')}
      </Button>
    </div>
  );
}

/** Modal trigger plus the dialog itself. */
function DialogDemo() {
  const t = useTranslations('common');
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        {t('actions.delete')}
      </Button>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title={t('actions.delete')}
        description={t('errors.generic')}
        closeLabel={t('actions.close')}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              {t('actions.cancel')}
            </Button>
            <Button variant="danger" onClick={() => setOpen(false)}>
              {t('actions.delete')}
            </Button>
          </>
        }
      >
        <p>{t('state.empty')}</p>
      </Dialog>
    </>
  );
}

/** The three text-entry controls, including the invalid state. */
function FormDemo() {
  const t = useTranslations('common');

  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <Input label="Name (uz)" placeholder="Boss salat" defaultValue="Boss salat" />
      <Input
        label="Price"
        numeric
        inputMode="numeric"
        defaultValue="30000"
        hint="tabular-nums, right aligned"
      />
      <Select label="Category" defaultValue="salads">
        <option value="salads">Salads</option>
        <option value="hot">Hot dishes</option>
        <option value="desserts">Desserts</option>
      </Select>
      <Input
        label="Slug"
        defaultValue="boss salat"
        error={t('errors.generic')}
        labelSuffix={t('form.required')}
      />
      <Textarea
        label="Description (ru)"
        className="sm:col-span-2"
        labelSuffix={t('form.optional')}
        placeholder="—"
        rows={3}
      />
    </div>
  );
}

/**
 * Every interactive piece of the system on one client island, so the styleguide
 * page itself can stay a server component.
 */
export function StyleguideDemos() {
  const t = useTranslations('common');

  return (
    <ToastProvider closeLabel={t('actions.close')}>
      <div className="flex flex-col gap-8">
        <FormDemo />
        <div className="flex flex-wrap items-center gap-3">
          <DialogDemo />
          <ToastTriggers />
        </div>
      </div>
    </ToastProvider>
  );
}
