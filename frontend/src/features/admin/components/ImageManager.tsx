'use client';

import Image from 'next/image';
import {useRouter} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {useRef, useState, type ChangeEvent} from 'react';

import {Badge, Button, Dialog, Input, Toast} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

import {deleteProductImageAction} from '../actions';
import {ACCEPTED_IMAGE_TYPES, MAX_IMAGE_BYTES} from '../constants';
import type {AdminProductImage} from '../types';

import {SubmitButton} from './SubmitButton';

/**
 * Photo library for one product: upload with a local preview and a real
 * progress bar, and removal behind a confirmation.
 *
 * The upload is an `XMLHttpRequest` rather than `fetch` for one reason: it is
 * the only browser API that reports how many bytes have actually gone out.
 * Kitchen photos are several megabytes over a phone connection, and a
 * spinner that cannot say "62%" is indistinguishable from a frozen page. The
 * request goes to a Route Handler on this origin, which attaches the bearer
 * token server-side — the browser still never holds one.
 */
export interface ImageManagerProps {
  locale: AppLocale;
  productId: number;
  images: readonly AdminProductImage[];
}

type UploadState =
  | {phase: 'idle'}
  | {phase: 'uploading'; percent: number}
  | {phase: 'error'; messageKey: 'tooLarge' | 'wrongType' | 'failed'}
  | {phase: 'done'};

/** Thumbnail width; the API always renders a 400px WebP derivative. */
const THUMBNAIL_WIDTH = 400;

/** The narrowest derivative, falling back to any width the API did return. */
function thumbnailFor(image: AdminProductImage): string {
  return image.srcset[String(THUMBNAIL_WIDTH)] ?? Object.values(image.srcset)[0] ?? '';
}

export function ImageManager({locale, productId, images}: ImageManagerProps) {
  const t = useTranslations('admin.images');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadState>({phase: 'idle'});
  const [pendingDeletion, setPendingDeletion] = useState<AdminProductImage | null>(null);

  function resetSelection() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    resetSelection();
    if (!selected) return;

    if (!ACCEPTED_IMAGE_TYPES.includes(selected.type)) {
      setUpload({phase: 'error', messageKey: 'wrongType'});
      return;
    }
    if (selected.size > MAX_IMAGE_BYTES) {
      setUpload({phase: 'error', messageKey: 'tooLarge'});
      return;
    }

    setUpload({phase: 'idle'});
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  }

  function startUpload(form: HTMLFormElement) {
    if (!file) return;

    const payload = new FormData(form);
    payload.set('image', file);

    const request = new XMLHttpRequest();
    request.open('POST', `/${locale}/admin/products/${productId}/images`);

    request.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return;
      setUpload({phase: 'uploading', percent: Math.round((event.loaded / event.total) * 100)});
    });

    request.addEventListener('load', () => {
      if (request.status >= 200 && request.status < 300) {
        setUpload({phase: 'done'});
        resetSelection();
        // The list of photos is rendered on the server, so re-render it there.
        router.refresh();
      } else {
        setUpload({phase: 'error', messageKey: 'failed'});
      }
    });

    request.addEventListener('error', () => setUpload({phase: 'error', messageKey: 'failed'}));

    setUpload({phase: 'uploading', percent: 0});
    request.send(payload);
  }

  return (
    <div className="flex flex-col gap-5">
      {images.length === 0 ? (
        <p className="text-body text-muted">{t('empty')}</p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {images.map((image) => (
            <li
              key={image.id}
              className="flex flex-col gap-2 rounded-md border border-ground-border bg-ground-base/40 p-2"
            >
              {/*
                `unoptimized`: the API already stored this exact file as WebP at
                400px. Sending it through the image optimizer would re-encode a
                thumbnail that is already the right format at the right size.
              */}
              <Image
                src={thumbnailFor(image)}
                alt={image.alt ?? ''}
                width={THUMBNAIL_WIDTH}
                height={Math.round((THUMBNAIL_WIDTH * image.height) / Math.max(1, image.width))}
                unoptimized
                className="h-auto w-full rounded-sm border border-gold-800 object-cover"
                sizes="(max-width: 640px) 45vw, 200px"
              />

              <div className="flex items-center justify-between gap-2">
                {image.is_primary ? <Badge tone="gold">{t('primary')}</Badge> : <span />}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-danger-text hover:bg-danger/15"
                  onClick={() => setPendingDeletion(image)}
                >
                  {t('remove')}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        data-testid="admin-image-form"
        className="flex flex-col gap-4 rounded-md border border-ground-border bg-ground-base/40 p-4"
        onSubmit={(event) => {
          event.preventDefault();
          startUpload(event.currentTarget);
        }}
      >
        <div className="flex flex-col gap-1.5">
          <label htmlFor="product-image-file" className="text-label text-gold-200 uppercase">
            {t('choose')}
          </label>
          <input
            id="product-image-file"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_IMAGE_TYPES.join(',')}
            onChange={handleFileChange}
            className="min-h-11 w-full cursor-pointer rounded-md border border-ground-border bg-ground-base px-3 py-2.5 text-body text-cream file:mr-3 file:cursor-pointer file:rounded-sm file:border-0 file:bg-gold-gradient file:px-3 file:py-2 file:text-label file:text-ink"
          />
          <p className="text-label text-muted normal-case tracking-normal">{t('hint')}</p>
        </div>

        {previewUrl && file ? (
          <div className="flex items-start gap-4">
            {/* Local object URL — `next/image` cannot optimise a blob, and there
                is nothing to optimise: the file has not left the device yet. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt={t('preview')}
              className="size-24 rounded-sm border border-gold-800 object-cover"
            />
            <p className="text-label text-muted normal-case tracking-normal">
              {t('selected', {name: file.name})}
            </p>
          </div>
        ) : null}

        <Input label={t('alt')} name="alt" hint={t('altHint')} maxLength={200} />

        <label className="flex min-h-11 items-center gap-3 text-body text-cream">
          <input type="checkbox" name="is_primary" className="size-5 accent-gold-400" />
          {t('makePrimary')}
        </label>

        {upload.phase === 'uploading' ? (
          <div className="flex items-center gap-3">
            <progress
              value={upload.percent}
              max={100}
              className="h-2 flex-1 overflow-hidden rounded-pill"
            />
            <span className="tabular text-label text-gold-200">
              {t('uploading', {percent: upload.percent})}
            </span>
          </div>
        ) : null}

        <div role="status" aria-live="polite">
          {upload.phase === 'error' ? (
            <Toast
              message={t(`errors.${upload.messageKey}`)}
              tone="danger"
              closeLabel={tCommon('actions.close')}
              className="w-full"
            />
          ) : null}
          {upload.phase === 'done' ? (
            <Toast
              message={t('uploaded')}
              tone="success"
              closeLabel={tCommon('actions.close')}
              className="w-full"
            />
          ) : null}
        </div>

        <div className="flex flex-wrap gap-3">
          <Button
            type="submit"
            variant="primary"
            data-testid="admin-upload-image"
            disabled={!file || upload.phase === 'uploading'}
          >
            {t('upload')}
          </Button>
          {file ? (
            <Button type="button" variant="ghost" onClick={resetSelection}>
              {t('cancel')}
            </Button>
          ) : null}
        </div>
      </form>

      <Dialog
        open={pendingDeletion !== null}
        onClose={() => setPendingDeletion(null)}
        title={t('removeTitle')}
        description={t('removeDescription')}
        closeLabel={tCommon('actions.close')}
        footer={
          <form
            action={deleteProductImageAction}
            onSubmit={() => setPendingDeletion(null)}
            className="flex flex-wrap justify-end gap-3"
          >
            <input type="hidden" name="locale" value={locale} />
            <input type="hidden" name="productId" value={productId} />
            <input type="hidden" name="imageId" value={pendingDeletion?.id ?? ''} />

            <Button type="button" variant="ghost" onClick={() => setPendingDeletion(null)}>
              {tCommon('actions.cancel')}
            </Button>
            <SubmitButton
              variant="danger"
              data-testid="admin-confirm-remove-image"
              label={t('remove')}
            />
          </form>
        }
      />
    </div>
  );
}
