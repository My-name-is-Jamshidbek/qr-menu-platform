import 'server-only';

import {fetchMenuData} from '@/lib/api';
import type {AppLocale} from '@/i18n/routing';

import type {MenuResponse} from './types';

/**
 * Fetches the whole menu for one language.
 *
 * One request returns every category, subcategory and product (~105 rows), which
 * beats a request per section: the dataset is small, the page is statically
 * generated, and having the full set in memory is what lets search run on the
 * client without touching the network.
 *
 * `fetchMenuData` tags the response with `menu` and caches it until that tag is
 * purged, so the page is rebuilt on a staff edit rather than on a timer — see
 * `src/app/api/revalidate/route.ts`.
 */
export function getMenu(locale: AppLocale): Promise<MenuResponse> {
  return fetchMenuData<MenuResponse>('menu/', {query: {lang: locale}});
}
