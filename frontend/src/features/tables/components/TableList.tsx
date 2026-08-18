'use client';

import {useTranslations} from 'next-intl';

import {Badge, Button} from '@/components/ui';

import type {AdminTable} from '../types';

export interface TableListProps {
  tables: readonly AdminTable[];
  onShowQr: (table: AdminTable) => void;
  onEdit: (table: AdminTable) => void;
  onDelete: (table: AdminTable) => void;
}

/**
 * Lifetime scans of one table. An absent figure is stated as such: rendering a
 * zero would claim the table has never been used, which is a different fact.
 */
function ScanCount({value}: {value: number | null | undefined}) {
  const t = useTranslations('tables.admin');

  return value === null || value === undefined ? (
    <span className="text-body text-muted">{t('scansUnknown')}</span>
  ) : (
    <span className="tabular font-display text-price text-cream">{value}</span>
  );
}

/**
 * The room, as a data grid.
 *
 * A real `<table>` rather than a grid of cards: these are homogeneous records
 * an administrator scans down a column, and the semantics give a screen reader
 * the row/column context for free. It scrolls inside its own container so a
 * narrow phone never scrolls the whole page sideways.
 */
export function TableList({tables, onShowQr, onEdit, onDelete}: TableListProps) {
  const t = useTranslations('tables.admin');

  return (
    <div className="overflow-x-auto rounded-lg border border-ground-border bg-ground-surface">
      <table className="w-full min-w-[44rem] border-collapse text-left">
        <caption className="sr-only">{t('description')}</caption>
        <thead>
          <tr className="border-b border-ground-border">
            <th scope="col" className="px-5 py-3 text-label text-gold-200 uppercase">
              {t('columns.number')}
            </th>
            <th scope="col" className="px-5 py-3 text-label text-gold-200 uppercase">
              {t('columns.label')}
            </th>
            <th scope="col" className="px-5 py-3 text-label text-gold-200 uppercase">
              {t('columns.status')}
            </th>
            <th scope="col" className="px-5 py-3 text-right text-label text-gold-200 uppercase">
              {t('columns.scans')}
            </th>
            <th scope="col" className="px-5 py-3 text-right text-label text-gold-200 uppercase">
              {t('columns.actions')}
            </th>
          </tr>
        </thead>

        <tbody>
          {tables.map((table) => (
            <tr
              key={table.id}
              className="border-b border-ground-border/70 transition-colors duration-[var(--motion-fast)] last:border-b-0 hover:bg-ground-elevated"
            >
              <th scope="row" className="px-5 py-4 font-display text-card tabular text-cream">
                {table.number}
              </th>
              <td className="px-5 py-4 text-body text-cream/80">{table.label}</td>
              <td className="px-5 py-4">
                <Badge tone={table.is_active ? 'success' : 'neutral'}>
                  {t(table.is_active ? 'status.active' : 'status.inactive')}
                </Badge>
              </td>
              <td className="px-5 py-4 text-right">
                <ScanCount value={table.scan_count} />
              </td>
              <td className="px-5 py-4">
                <div className="flex flex-wrap justify-end gap-2">
                  <Button size="sm" variant="secondary" onClick={() => onShowQr(table)}>
                    {t('actions.showQr')}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onEdit(table)}>
                    {t('actions.edit')}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onDelete(table)}>
                    {t('actions.delete')}
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
