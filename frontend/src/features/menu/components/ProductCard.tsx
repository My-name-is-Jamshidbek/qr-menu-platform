'use client';

import Image from 'next/image';
import {useLocale, useTranslations} from 'next-intl';

import {Badge, Card, MonogramPlaceholder} from '@/components/ui';

import {formatPrice} from '../format';
import {createProductImageLoader, fullSizeUrl, PRODUCT_IMAGE_SIZES} from '../imageLoader';
import type {MenuProduct} from '../types';

export interface ProductCardProps {
  product: MenuProduct;
  /**
   * Loads the photo immediately instead of on approach. Reserved for the handful
   * of cards above the fold — everything further down stays lazy so a phone on a
   * weak connection downloads a screenful, not the whole menu.
   */
  eager?: boolean;
}

/** 4:3 is the ratio the design system crops product photography to. */
const IMAGE_WIDTH = 800;
const IMAGE_HEIGHT = 600;

/**
 * One dish. The card is deliberately not a link: there is no product detail
 * route in the public menu, and a clickable surface that goes nowhere is worse
 * than a static one.
 */
export function ProductCard({product, eager = false}: ProductCardProps) {
  const locale = useLocale();
  const t = useTranslations('menu.product');
  const {image} = product;

  return (
    <Card className="flex h-full flex-col overflow-hidden" tone="surface">
      <div className="relative aspect-[4/3] w-full overflow-hidden border-b border-ground-border bg-ground-elevated">
        {image ? (
          <Image
            alt={image.alt}
            className="size-full object-cover"
            /*
             * The intrinsic ratio, not the rendered size: `width`/`height` are
             * what let the browser reserve the box before the file arrives, so
             * the grid never reflows. The real size comes from the CSS above.
             */
            height={IMAGE_HEIGHT}
            loader={createProductImageLoader(image)}
            loading={eager ? 'eager' : 'lazy'}
            sizes={PRODUCT_IMAGE_SIZES}
            src={fullSizeUrl(image)}
            width={IMAGE_WIDTH}
          />
        ) : (
          <MonogramPlaceholder className="size-full" name={product.name} />
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-display text-card text-cream">{product.name}</h3>

          <Badge className="shrink-0" numeric tone="gold">
            <span className="sr-only">{t('priceLabel')}: </span>
            {formatPrice(product.price, locale, t('currency'))}
          </Badge>
        </div>

        {product.description ? (
          <p className="text-body text-cream/70">{product.description}</p>
        ) : null}

        {product.is_fallback ? (
          /*
           * The API flags a product whose name fell back to Uzbek. Surfacing it
           * is honest to the guest and doubles as the nudge that gets the
           * missing translation filled in.
           */
          <p className="mt-auto pt-1 text-label text-muted normal-case tracking-normal">
            {t('translationPendingHint')}
          </p>
        ) : null}
      </div>
    </Card>
  );
}
