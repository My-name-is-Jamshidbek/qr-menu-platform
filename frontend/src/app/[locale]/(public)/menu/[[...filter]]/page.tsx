import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {Container} from '@/components/layout';
import {
  CategoryNav,
  getMenu,
  MenuBrowser,
  menuFilterPaths,
  resolveMenuView,
  UnknownMenuFilterError,
  type MenuCategory,
  type MenuView
} from '@/features/menu';
import {defaultLocale, isAppLocale, routing, type AppLocale} from '@/i18n/routing';

type MenuPageProps = PageProps<'/[locale]/menu/[[...filter]]'>;

/**
 * Prerenders every filter of the menu — `/menu`, each section and each
 * subsection — in all three languages. Because the underlying fetch is tagged
 * `menu` and never expires on a timer, those pages are served from the ISR cache
 * until a staff edit posts to `/api/revalidate`.
 */
export async function generateStaticParams({
  params
}: {
  params: {locale: string};
}): Promise<Array<{filter: string[]}>> {
  const locale = isAppLocale(params.locale) ? params.locale : defaultLocale;
  const menu = await getMenu(locale);

  return menuFilterPaths(menu).map((filter) => ({filter}));
}

interface ResolvedMenuPage {
  locale: AppLocale;
  view: MenuView;
  categories: MenuCategory[];
}

/**
 * Resolves the route once. Called by both `generateMetadata` and the page body;
 * the second call is free because the underlying fetch is deduplicated within a
 * render and cached across them.
 */
async function loadPage(
  localeParam: string,
  filter: string[] | undefined
): Promise<ResolvedMenuPage> {
  if (!isAppLocale(localeParam)) notFound();

  const menu = await getMenu(localeParam);

  try {
    return {
      locale: localeParam,
      view: resolveMenuView(menu, filter),
      categories: menu.categories
    };
  } catch (error) {
    // An unknown section in the URL is a 404, not a silent fall back to
    // "everything" — otherwise a typo would serve the wrong page and still
    // hand a crawler a 200.
    if (error instanceof UnknownMenuFilterError) notFound();
    throw error;
  }
}

/** `/uz/menu`, `/uz/menu/salads`, `/uz/menu/national/soups`. */
function menuPath(locale: string, filter: string[] | undefined): string {
  return filter?.length ? `/${locale}/menu/${filter.join('/')}` : `/${locale}/menu`;
}

export async function generateMetadata({params}: MenuPageProps): Promise<Metadata> {
  const {locale: localeParam, filter} = await params;
  const {locale, view} = await loadPage(localeParam, filter);

  const t = await getTranslations({locale, namespace: 'menu.meta'});

  const section = view.subcategory ?? view.category;
  const title = section ? t('titleForCategory', {category: section.name}) : t('title');
  const description = section
    ? t('descriptionForCategory', {category: section.name, count: view.productCount})
    : t('description');

  const canonical = menuPath(locale, filter);

  // The first photo in the view doubles as the share image, so a link to
  // "Desserts" previews a dessert rather than a generic logo.
  const leadImage = view.groups[0]?.products.find((product) => product.image)?.image;

  return {
    title,
    description,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        routing.locales.map((item) => [item, menuPath(item, filter)])
      )
    },
    openGraph: {
      type: 'website',
      title,
      description,
      url: canonical,
      locale,
      alternateLocale: routing.locales.filter((item) => item !== locale),
      images: leadImage
        ? [
            {
              url: leadImage.srcset['1600'] ?? leadImage.src,
              width: leadImage.width,
              height: leadImage.height,
              alt: leadImage.alt
            }
          ]
        : undefined
    }
  };
}

/**
 * The public menu — what a guest sees after scanning the QR code on their table.
 *
 * A Server Component: the menu is fetched and rendered on the server, so the
 * browser gets finished HTML instead of a spinner and a fetch waterfall. The
 * only JavaScript shipped for the page itself is the search box.
 */
export default async function MenuPage({params}: MenuPageProps) {
  const {locale: localeParam, filter} = await params;
  const {locale, view, categories} = await loadPage(localeParam, filter);

  // Required for `next-intl` to render this route statically.
  setRequestLocale(locale);

  const t = await getTranslations('menu.heading');

  const section = view.subcategory ?? view.category;

  return (
    <Container as="main" className="py-10 sm:py-14">
      <header className="flex flex-col gap-3">
        <h1 className="font-display text-hero text-cream">
          {section ? section.name : t('title')}
        </h1>
        <p className="max-w-prose text-body text-muted">{t('subtitle')}</p>
      </header>

      <div className="mt-8">
        <CategoryNav
          activeCategory={view.category}
          activeSubcategory={view.subcategory}
          categories={categories}
        />
      </div>

      <MenuBrowser groups={view.groups} />
    </Container>
  );
}
