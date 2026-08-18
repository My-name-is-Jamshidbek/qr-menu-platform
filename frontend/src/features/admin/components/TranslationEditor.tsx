'use client';

import {useTranslations} from 'next-intl';

import {Badge, Input, Textarea} from '@/components/ui';
import {cn} from '@/lib/cn';

import {CONTENT_LANGUAGES, REQUIRED_CONTENT_LANGUAGE, type ContentLanguage} from '../constants';
import type {TranslationDraft} from '../types';

/**
 * All three languages in one view.
 *
 * Tabs were rejected on purpose: a missing Russian name is the single most
 * common defect in this dataset — 74 of the imported products had one — and
 * hiding two thirds of the form behind tabs is what let that happen unnoticed.
 * Every language is visible at once, and one carries a "Missing" badge the
 * moment its name field is empty.
 */
export interface TranslationEditorProps {
  drafts: readonly TranslationDraft[];
  onChange: (language: ContentLanguage, field: 'name' | 'description', value: string) => void;
  /** Server-side messages keyed `name_<language>`. */
  fieldErrors?: Record<string, string[]>;
}

export function TranslationEditor({drafts, onChange, fieldErrors}: TranslationEditorProps) {
  const t = useTranslations('admin.form');
  const tLanguage = useTranslations('common.language');

  return (
    <div className="flex flex-col gap-5">
      {CONTENT_LANGUAGES.map((language) => {
        const draft = drafts.find((row) => row.language === language);
        const isRequired = language === REQUIRED_CONTENT_LANGUAGE;
        const isMissing = (draft?.name ?? '').trim() === '';
        const error = fieldErrors?.[`name_${language}`]?.[0];

        return (
          <fieldset
            key={language}
            className={cn(
              'flex flex-col gap-4 rounded-md border p-4',
              isMissing && !isRequired
                ? 'border-warning/40 bg-warning/5'
                : 'border-ground-border bg-ground-base/40'
            )}
          >
            <legend className="flex items-center gap-2 px-2">
              <span className="font-display text-card text-cream">{tLanguage(language)}</span>
              {isMissing ? (
                <Badge tone={isRequired ? 'danger' : 'warning'}>{t('missingBadge')}</Badge>
              ) : (
                <Badge tone="outline">{t('completeBadge')}</Badge>
              )}
            </legend>

            <Input
              label={t('name')}
              name={`name_${language}`}
              value={draft?.name ?? ''}
              onChange={(event) => onChange(language, 'name', event.target.value)}
              error={error}
              labelSuffix={isRequired ? t('requiredBadge') : t('optionalBadge')}
              autoComplete="off"
              maxLength={160}
            />

            <Textarea
              label={t('description')}
              name={`description_${language}`}
              value={draft?.description ?? ''}
              onChange={(event) => onChange(language, 'description', event.target.value)}
              rows={3}
            />
          </fieldset>
        );
      })}
    </div>
  );
}
