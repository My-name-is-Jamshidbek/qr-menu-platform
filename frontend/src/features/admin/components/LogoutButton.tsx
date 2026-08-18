'use client';

import {useRouter} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {useState} from 'react';

import {Button} from '@/components/ui';
import type {AppLocale} from '@/i18n/routing';

/**
 * Signing out is a `POST`, never a link: a `GET` that destroys a session can be
 * triggered by a prefetch or an image tag on any page the staff member visits.
 */
export function LogoutButton({locale}: {locale: AppLocale}) {
  const t = useTranslations('admin.nav');
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function signOut() {
    setPending(true);
    try {
      await fetch('/api/auth/logout', {method: 'POST'});
    } finally {
      router.replace(`/${locale}/admin/login`);
      router.refresh();
    }
  }

  return (
    <Button type="button" variant="ghost" size="sm" onClick={signOut} disabled={pending}>
      {pending ? t('loggingOut') : t('logout')}
    </Button>
  );
}
