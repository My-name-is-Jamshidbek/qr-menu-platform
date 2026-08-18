import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {Card, CardBody, CardHeader, CardTitle, Toast} from '@/components/ui';
import {
  DeleteProductButton,
  ImageManager,
  ProductForm,
  fetchCategories,
  fetchProduct,
  toCategoryOptions,
  translatedName,
  type AdminProduct
} from '@/features/admin';
import {isAppLocale} from '@/i18n/routing';
import {ApiError} from '@/lib/api';

/**
 * Editing a product: the same single-submit form as creation, plus the photo
 * library and the delete action, which live outside the form element so that
 * neither ends up nested inside it.
 */

async function loadProduct(id: string): Promise<AdminProduct> {
  const productId = Number.parseInt(id, 10);
  if (!Number.isSafeInteger(productId) || productId <= 0) notFound();

  try {
    return await fetchProduct(productId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({
  params
}: PageProps<'/[locale]/admin/products/[id]'>): Promise<Metadata> {
  const {locale, id} = await params;
  if (!isAppLocale(locale)) notFound();

  const product = await loadProduct(id);
  const t = await getTranslations({locale, namespace: 'admin.form'});

  return {title: translatedName(product.translations, locale) || t('editTitle')};
}

export default async function EditProductPage({
  params,
  searchParams
}: PageProps<'/[locale]/admin/products/[id]'>) {
  const {locale, id} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'admin.form'});
  const tImages = await getTranslations({locale, namespace: 'admin.images'});
  const tCommon = await getTranslations({locale, namespace: 'common'});

  const [product, categories] = await Promise.all([loadProduct(id), fetchCategories()]);
  const justCreated = (await searchParams).created === '1';
  const displayName = translatedName(product.translations, locale) || String(product.id);

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-title text-cream">{displayName}</h1>
          <p className="text-body text-muted">{t('editSubtitle')}</p>
        </div>

        <DeleteProductButton
          locale={locale}
          productId={product.id}
          productName={displayName}
          size="md"
        />
      </div>

      {justCreated ? (
        <Toast
          message={t('created')}
          tone="success"
          closeLabel={tCommon('actions.close')}
          className="w-full"
        />
      ) : null}

      <ProductForm
        locale={locale}
        categories={toCategoryOptions(categories, locale)}
        product={product}
      />

      <Card>
        <CardHeader>
          <CardTitle>{tImages('title')}</CardTitle>
        </CardHeader>
        <CardBody>
          <ImageManager locale={locale} productId={product.id} images={product.images} />
        </CardBody>
      </Card>
    </section>
  );
}
