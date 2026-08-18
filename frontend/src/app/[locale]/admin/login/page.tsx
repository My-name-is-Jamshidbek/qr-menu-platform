import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {Container} from '@/components/layout';
import {Card, CardBody, CardHeader, CardTitle} from '@/components/ui';
import {LoginForm, loginErrorKeyFromParam} from '@/features/admin';
import {isAppLocale} from '@/i18n/routing';
import {RETURN_TO_PARAM, adminHome, sanitiseReturnTo} from '@/middleware-auth';

/**
 * The sign-in screen.
 *
 * It sits outside the `(dashboard)` route group, and therefore outside the
 * layout that requires a session — otherwise the guard would redirect the
 * login page to itself.
 */

export async function generateMetadata({
  params
}: PageProps<'/[locale]/admin/login'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'admin.login'});

  return {title: t('title'), robots: {index: false, follow: false}};
}

export default async function AdminLoginPage({
  params,
  searchParams
}: PageProps<'/[locale]/admin/login'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'admin.login'});
  const resolved = await searchParams;
  const requested = resolved[RETURN_TO_PARAM];
  const returnTo =
    sanitiseReturnTo(typeof requested === 'string' ? requested : null) ?? adminHome(locale);
  const reportedError = resolved.error;

  return (
    <Container className="flex flex-1 items-center justify-center py-16">
      <Card className="w-full max-w-md">
        <CardHeader className="flex-col items-start gap-1">
          <CardTitle>{t('title')}</CardTitle>
          <p className="text-body text-muted">{t('subtitle')}</p>
        </CardHeader>
        <CardBody>
          <LoginForm
            returnTo={returnTo}
            initialError={loginErrorKeyFromParam(
              typeof reportedError === 'string' ? reportedError : undefined
            )}
          />
        </CardBody>
      </Card>
    </Container>
  );
}
