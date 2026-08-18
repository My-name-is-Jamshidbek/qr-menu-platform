import type {Metadata} from 'next';
import {notFound, redirect} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {EmptyState} from '@/components/ui';
import {AdminShell} from '@/features/admin';
import {fetchAdminStats, listTables} from '@/features/tables/api';
import {TablesManager} from '@/features/tables';
import type {AdminTable} from '@/features/tables';
import {isAppLocale} from '@/i18n/routing';
import {ApiError} from '@/lib/api';
import {fetchCurrentUser, readAccessToken} from '@/lib/auth';
import {adminLoginPath} from '@/middleware-auth';

/**
 * Table administration: CRUD, per-table QR artwork and scan figures.
 *
 * The panel's other screens sit in the `(dashboard)` route group and inherit
 * their session gate and chrome from its layout. This route serves the same
 * `/admin/tables` URL from outside that group, so it repeats both explicitly —
 * folding it into the group later means deleting the two lines below, not
 * rewriting the screen.
 */

export async function generateMetadata({
  params
}: PageProps<'/[locale]/admin/tables'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'tables.admin'});

  // The room layout is not public information, and an admin screen has no
  // business in a search index.
  return {title: t('title'), robots: {index: false, follow: false}};
}

export default async function AdminTablesPage({params}: PageProps<'/[locale]/admin/tables'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const accessToken = await readAccessToken();
  if (!accessToken) redirect(adminLoginPath(locale, null));

  const user = await fetchCurrentUser(accessToken);
  if (!user) redirect(adminLoginPath(locale, null));

  const t = await getTranslations({locale, namespace: 'tables.admin'});
  const tCommon = await getTranslations({locale, namespace: 'common.errors'});

  let tables: AdminTable[];
  let scansLast7Days: number;

  try {
    // One round trip each, in parallel: the counters are a different resource
    // from the list and neither depends on the other.
    const [page, stats] = await Promise.all([
      listTables(accessToken),
      fetchAdminStats(accessToken)
    ]);
    tables = page.results;
    scansLast7Days = stats.scans_last_7_days;
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;

    // The session survived `getSessionUser` but the API refused this read —
    // a STAFF account, or an API that went away between the two calls.
    return (
      <AdminShell locale={locale} user={user}>
        <EmptyState
          title={tCommon(error.status === 403 ? 'unauthorized' : 'generic')}
          description={t('loadFailed')}
        />
      </AdminShell>
    );
  }

  return (
    <AdminShell locale={locale} user={user}>
      <TablesManager tables={tables} scansLast7Days={scansLast7Days} locale={locale} />
    </AdminShell>
  );
}
