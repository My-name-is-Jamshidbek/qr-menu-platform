'use client';

import {useCallback, useState, useTransition} from 'react';
import {useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

import {Button, EmptyState, ToastProvider, useToast} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {fetchQrSheetAction} from '../actions';
import {base64ToArrayBuffer, downloadBlob} from '../download';
import type {AdminTable} from '../types';

import {DeleteTableDialog} from './DeleteTableDialog';
import {TableFormDialog} from './TableFormDialog';
import {TableList} from './TableList';
import {TableQrDialog} from './TableQrDialog';

export interface TablesManagerProps {
  tables: readonly AdminTable[];
  /** Seven-day scan total from `GET /admin/stats/`. */
  scansLast7Days: number;
  locale: AppLocale;
}

/** One counter in the header strip. */
function Stat({label, value}: {label: string; value: number}) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-ground-border bg-ground-surface px-5 py-4">
      <span className="text-label text-gold-200 uppercase">{label}</span>
      <span className="tabular font-display text-title text-cream">{value}</span>
    </div>
  );
}

/**
 * Every dialog on this screen is driven from here so that only one can be open
 * at a time — a QR preview stacked over a delete confirmation would leave the
 * administrator unsure which table they are about to remove.
 */
type OpenDialog =
  | {kind: 'none'}
  | {kind: 'form'; table: AdminTable | null}
  | {kind: 'qr'; table: AdminTable}
  | {kind: 'delete'; table: AdminTable};

function TablesScreen({tables, scansLast7Days, locale}: TablesManagerProps) {
  const t = useTranslations('tables.admin');
  const router = useRouter();
  const {show} = useToast();
  const [dialog, setDialog] = useState<OpenDialog>({kind: 'none'});
  const [isSheetPending, startSheetTransition] = useTransition();

  const close = useCallback(() => setDialog({kind: 'none'}), []);

  const fail = useCallback(
    (message: string) => show({message, tone: 'danger'}),
    [show]
  );

  /** Closes the dialog, reports the outcome and pulls the fresh server render. */
  const succeed = useCallback(
    (message: string) => {
      close();
      show({message, tone: 'success'});
      router.refresh();
    },
    [close, show, router]
  );

  function printAll() {
    startSheetTransition(async () => {
      const result = await fetchQrSheetAction(locale);

      if (!result.ok) {
        fail(result.message || t('toast.failed'));
        return;
      }

      downloadBlob(base64ToArrayBuffer(result.data), 'table-qr-sheet.pdf', 'application/pdf');
      show({message: t('toast.sheetReady'), tone: 'success'});
    });
  }

  const activeCount = tables.filter((table) => table.is_active).length;

  return (
    <>
      <header className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h1 className="font-display text-title text-cream">{t('title')}</h1>
            <p className="text-body text-muted">{t('description')}</p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              onClick={printAll}
              disabled={isSheetPending || activeCount === 0}
            >
              {t('actions.printAll')}
            </Button>
            <Button variant="primary" onClick={() => setDialog({kind: 'form', table: null})}>
              {t('actions.create')}
            </Button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label={t('stats.tables')} value={tables.length} />
          <Stat label={t('stats.active')} value={activeCount} />
          <Stat label={t('stats.scansLast7Days')} value={scansLast7Days} />
        </div>
      </header>

      {tables.length === 0 ? (
        <EmptyState
          title={t('empty.title')}
          description={t('empty.description')}
          action={
            <Button variant="primary" onClick={() => setDialog({kind: 'form', table: null})}>
              {t('actions.create')}
            </Button>
          }
        />
      ) : (
        <TableList
          tables={tables}
          onShowQr={(table) => setDialog({kind: 'qr', table})}
          onEdit={(table) => setDialog({kind: 'form', table})}
          onDelete={(table) => setDialog({kind: 'delete', table})}
        />
      )}

      {/*
        Each dialog is mounted only while it is the open one. That keeps its
        state seeded from props at mount — no effect has to reset the form or
        clear the previous table's QR preview — and guarantees at most one
        modal exists at a time.
      */}
      {dialog.kind === 'form' ? (
        <TableFormDialog
          key={dialog.table?.id ?? 'new'}
          table={dialog.table}
          locale={locale}
          onClose={close}
          onSaved={succeed}
        />
      ) : null}

      {dialog.kind === 'qr' ? (
        <TableQrDialog table={dialog.table} locale={locale} onClose={close} onFailed={fail} />
      ) : null}

      {dialog.kind === 'delete' ? (
        <DeleteTableDialog
          table={dialog.table}
          locale={locale}
          onClose={close}
          onDeleted={succeed}
          onFailed={fail}
        />
      ) : null}
    </>
  );
}

/**
 * Client shell of the admin tables screen.
 *
 * The list itself is fetched and rendered on the server; this component owns
 * only the interactive layer — dialogs, the QR downloads and the toast region
 * they report into.
 */
export function TablesManager(props: TablesManagerProps) {
  const tCommon = useTranslations('common');

  return (
    <ToastProvider closeLabel={tCommon('actions.close')}>
      <TablesScreen {...props} />
    </ToastProvider>
  );
}
