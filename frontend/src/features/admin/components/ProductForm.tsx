'use client';

import {useTranslations} from 'next-intl';
import {useActionState, useState} from 'react';

import {Card, CardBody, CardHeader, CardTitle, Input, Select, Toast} from '@/components/ui';
import {Link} from '@/i18n/navigation';
import type {AppLocale} from '@/i18n/routing';

import {saveProductAction} from '../actions';
import {CONTENT_LANGUAGES, MIN_PRICE_UZS, type ContentLanguage} from '../constants';
import {IDLE_ACTION_STATE, type AdminProduct, type CategoryOption, type TranslationDraft} from '../types';

import {SubmitButton} from './SubmitButton';
import {TranslationEditor} from './TranslationEditor';

/**
 * Create and edit, in one component.
 *
 * The two screens differ only by whether a product id is posted, and the API
 * writes the product and its translations in a single transaction — so this is
 * a single form with a single save, not a wizard.
 */
export interface ProductFormProps {
  locale: AppLocale;
  categories: readonly CategoryOption[];
  /** Omitted when creating. */
  product?: AdminProduct;
}

function initialDrafts(product: AdminProduct | undefined): TranslationDraft[] {
  return CONTENT_LANGUAGES.map((language) => {
    const existing = product?.translations.find((row) => row.language === language);
    return {
      language,
      name: existing?.name ?? '',
      description: existing?.description ?? ''
    };
  });
}

export function ProductForm({locale, categories, product}: ProductFormProps) {
  const t = useTranslations('admin.form');
  const tCommon = useTranslations('common');

  const [state, formAction] = useActionState(saveProductAction, IDLE_ACTION_STATE);
  const [drafts, setDrafts] = useState<TranslationDraft[]>(() => initialDrafts(product));

  function updateDraft(language: ContentLanguage, field: 'name' | 'description', value: string) {
    setDrafts((current) =>
      current.map((draft) => (draft.language === language ? {...draft, [field]: value} : draft))
    );
  }

  return (
    <form
      action={formAction}
      data-testid="admin-product-form"
      className="flex flex-col gap-6"
    >
      <input type="hidden" name="locale" value={locale} />
      {product ? <input type="hidden" name="id" value={product.id} /> : null}

      <Card>
        <CardHeader>
          <CardTitle>{t('details')}</CardTitle>
        </CardHeader>
        <CardBody className="grid gap-5 sm:grid-cols-2">
          <Select
            label={t('category')}
            name="category"
            defaultValue={product ? String(product.category) : ''}
            error={state.fieldErrors?.category?.[0]}
            required
          >
            <option value="" disabled>
              {t('category')}
            </option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.isChild ? `— ${category.label}` : category.label}
              </option>
            ))}
          </Select>

          <Input
            label={t('price')}
            name="price"
            type="number"
            inputMode="numeric"
            min={MIN_PRICE_UZS}
            step={100}
            numeric
            defaultValue={product ? String(product.price) : ''}
            hint={t('priceHint', {min: MIN_PRICE_UZS})}
            error={state.fieldErrors?.price?.[0]}
            required
          />

          <Input
            label={t('order')}
            name="order"
            type="number"
            inputMode="numeric"
            min={0}
            numeric
            defaultValue={String(product?.order ?? 0)}
            hint={t('orderHint')}
            error={state.fieldErrors?.order?.[0]}
          />

          <label className="flex min-h-11 items-center gap-3 self-end text-body text-cream">
            <input
              type="checkbox"
              name="is_available"
              defaultChecked={product?.is_available ?? true}
              className="size-5 accent-gold-400"
            />
            <span>
              {t('available')}
              <span className="block text-label text-muted normal-case tracking-normal">
                {t('availableHint')}
              </span>
            </span>
          </label>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('translations')}</CardTitle>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <p className="text-label text-muted normal-case tracking-normal">
            {t('translationsHint')}
          </p>
          <TranslationEditor
            drafts={drafts}
            onChange={updateDraft}
            fieldErrors={state.fieldErrors}
          />
        </CardBody>
      </Card>

      {/* Announced rather than merely repainted, for both outcomes. */}
      <div role="status" aria-live="polite">
        {state.status !== 'idle' ? (
          <Toast
            message={state.message ?? (state.status === 'success' ? t('saved') : t('errors.saveFailed'))}
            tone={state.status === 'success' ? 'success' : 'danger'}
            closeLabel={tCommon('actions.close')}
            className="w-full"
          />
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SubmitButton
          variant="primary"
          size="lg"
          data-testid="admin-save-product"
          label={t('save')}
          pendingLabel={t('saving')}
        />
        <Link
          href="/admin/products"
          className="inline-flex min-h-11 items-center rounded-md px-4 text-label text-cream/70 uppercase hover:text-gold-200"
        >
          {t('cancel')}
        </Link>
      </div>
    </form>
  );
}
