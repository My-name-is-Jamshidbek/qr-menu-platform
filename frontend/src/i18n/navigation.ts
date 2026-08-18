import {createNavigation} from 'next-intl/navigation';

import {routing} from './routing';

/**
 * Locale-aware replacements for `next/link` and `next/navigation`.
 * Always import navigation helpers from here so links keep their /uz|/ru|/en
 * prefix instead of dropping the visitor back to the default locale.
 */
export const {Link, redirect, usePathname, useRouter, getPathname} = createNavigation(routing);
