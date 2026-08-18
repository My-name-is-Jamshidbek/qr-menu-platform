'use client';

import {useEffect, useRef, useState} from 'react';
import {useTranslations} from 'next-intl';

import {Button, Dialog, Spinner} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {fetchTableQrAction} from '../actions';
import {downloadBlob} from '../download';
import type {AdminTable} from '../types';

export interface TableQrDialogProps {
  table: AdminTable;
  locale: AppLocale;
  onClose: () => void;
  /** Called with the translated failure message when the code cannot be fetched. */
  onFailed: (message: string) => void;
}

/**
 * Preview and download of one table's printed code.
 *
 * The markup is rendered by the API (`segno`) rather than by a client-side QR
 * library, so what is previewed here is byte-for-byte what the PDF sheet
 * prints. The code sits on a light panel because a QR reader needs dark modules
 * on a light field — the dark ground of the rest of the admin would make it
 * unscannable.
 *
 * Mounted only while a table is selected, so the fetch below runs exactly once
 * per opening and there is no stale preview to clear on the way out.
 */
export function TableQrDialog({table, locale, onClose, onFailed}: TableQrDialogProps) {
  const t = useTranslations('tables.admin');
  const tCommon = useTranslations('common');
  const [svg, setSvg] = useState<string | null>(null);

  // Held in a ref so the fetch below depends only on *which* code to load. Put
  // in the dependency array, a caller that re-created its handlers on every
  // render would restart the request on every render.
  const handlers = useRef({onFailed, onClose, t});
  useEffect(() => {
    handlers.current = {onFailed, onClose, t};
  });

  const tableId = table.id;
  useEffect(() => {
    let active = true;

    void fetchTableQrAction(locale, tableId).then((result) => {
      // The administrator may already have closed the dialog; a late response
      // must not resurrect it.
      if (!active) return;

      if (result.ok) {
        setSvg(result.data);
        return;
      }

      handlers.current.onFailed(result.message || handlers.current.t('toast.failed'));
      handlers.current.onClose();
    });

    return () => {
      active = false;
    };
  }, [tableId, locale]);

  return (
    <Dialog
      open
      onClose={onClose}
      title={t('qr.title', {number: table.number})}
      description={t('qr.description')}
      closeLabel={tCommon('actions.close')}
      footer={
        <Button
          variant="primary"
          disabled={!svg}
          onClick={() => {
            if (!svg) return;
            downloadBlob(svg, `table-${table.number}-qr.svg`, 'image/svg+xml');
          }}
        >
          {t('actions.download')}
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex aspect-square items-center justify-center rounded-md bg-cream p-5">
          {svg ? (
            // Markup produced by our own API from a UUID; there is no
            // attacker-controlled substring in it.
            <div
              className="size-full [&>svg]:size-full"
              role="img"
              aria-label={t('qr.title', {number: table.number})}
              dangerouslySetInnerHTML={{__html: svg}}
            />
          ) : (
            <Spinner size="lg" label={tCommon('state.loading')} />
          )}
        </div>

        <p className="flex flex-col gap-1">
          <span className="text-label text-gold-200 uppercase">{t('qr.urlLabel')}</span>
          <code className="break-all text-body text-muted">{table.scan_url}</code>
        </p>
      </div>
    </Dialog>
  );
}
