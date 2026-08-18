import type {Metadata} from 'next';
import {getTranslations, setRequestLocale} from 'next-intl/server';
import type {ReactNode} from 'react';

import {Container} from '@/components/layout';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  CardTitle,
  EmptyState,
  MonogramPlaceholder,
  Pill,
  SkeletonCard,
  Spinner,
  Toast
} from '@/components/ui';
import {defaultLocale, isAppLocale} from '@/i18n/routing';

import {StyleguideDemos} from './StyleguideDemos';

/**
 * Living reference for the "Refined Gold" system: every token and every
 * component on one screen, so the design can be reviewed and screenshotted.
 *
 * This is an internal engineering page, not a customer-facing one. Its labels
 * are token names — `gold-400`, `text-hero` — which are code identifiers and
 * therefore stay in English rather than moving into the message catalog. The
 * demo copy that *does* stand in for real UI is pulled from `common`.
 */

export const metadata: Metadata = {
  title: 'Styleguide',
  // A reference page must never be indexed alongside the menu.
  robots: {index: false, follow: false}
};

const GROUND_SWATCHES = [
  {name: 'ground-base', variable: '--ground-base', hex: '#0E0D0B'},
  {name: 'ground-surface', variable: '--ground-surface', hex: '#17150F'},
  {name: 'ground-elevated', variable: '--ground-elevated', hex: '#211D14'},
  {name: 'ground-border', variable: '--ground-border', hex: '#2E2819'}
] as const;

const GOLD_SWATCHES = [
  {name: '50', variable: '--gold-50', hex: '#FBF6E8'},
  {name: '100', variable: '--gold-100', hex: '#F5EACB'},
  {name: '200', variable: '--gold-200', hex: '#EBD79C'},
  {name: '300', variable: '--gold-300', hex: '#E0C36C'},
  {name: '400', variable: '--gold-400', hex: '#D4AF37'},
  {name: '500', variable: '--gold-500', hex: '#BF9A2A'},
  {name: '600', variable: '--gold-600', hex: '#9A7A1F'},
  {name: '700', variable: '--gold-700', hex: '#6E5716'},
  {name: '800', variable: '--gold-800', hex: '#45360E'},
  {name: '900', variable: '--gold-900', hex: '#241C07'}
] as const;

const OTHER_SWATCHES = [
  {name: 'cream', variable: '--cream', hex: '#F7F3E8'},
  {name: 'ink', variable: '--ink', hex: '#1A1712'},
  {name: 'muted', variable: '--muted', hex: '#8C8574'},
  {name: 'success', variable: '--success', hex: '#3F7D5A'},
  {name: 'danger', variable: '--danger', hex: '#A63D3D'},
  {name: 'warning', variable: '--warning', hex: '#B8862B'}
] as const;

/** Contrast pairs the system guarantees, measured against WCAG 2.1 relative luminance. */
const CONTRAST_PAIRS = [
  {pair: 'cream on ground-base', ratio: '17.52:1', grade: 'AAA'},
  {pair: 'gold-300 on ground-base', ratio: '11.28:1', grade: 'AAA'},
  {pair: 'ink on gold-400', ratio: '8.50:1', grade: 'AAA'},
  {pair: 'gold-200 on ground-surface', ratio: '12.80:1', grade: 'AAA'},
  {pair: 'muted on ground-base', ratio: '5.29:1', grade: 'AA'}
] as const;

const TYPE_SPECIMENS = [
  {token: 'text-hero', className: 'font-display text-hero', spec: 'Playfair 600 · -0.02em'},
  {token: 'text-title', className: 'font-display text-title', spec: 'Playfair 600'},
  {token: 'text-card', className: 'font-display text-card', spec: 'Playfair 600 · 18px'},
  {token: 'text-body', className: 'text-body', spec: 'Inter 400 · 16/1.6'},
  {token: 'text-label', className: 'text-label uppercase', spec: 'Inter 500 · 13px · 0.08em'}
] as const;

const RADII = [
  {token: 'rounded-sm', className: 'rounded-sm', value: '6px'},
  {token: 'rounded-md', className: 'rounded-md', value: '10px'},
  {token: 'rounded-lg', className: 'rounded-lg', value: '16px'},
  {token: 'rounded-pill', className: 'rounded-pill', value: '999px'}
] as const;

const ELEVATIONS = [
  {token: 'shadow-card', className: 'shadow-card'},
  {token: 'shadow-lifted', className: 'shadow-lifted'},
  {token: 'shadow-modal', className: 'shadow-modal'}
] as const;

const DEMO_PRODUCTS = [
  {name: 'Boss salat', category: 'Salads', price: '30 000'},
  {name: 'Tovuq lavash', category: 'Fast food', price: '25 000'},
  {name: 'Choyxona shirinligi', category: 'Desserts', price: '9 500'}
] as const;

function Section({
  id,
  title,
  lead,
  children
}: {
  id: string;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 id={`${id}-heading`} className="font-display text-title text-cream">
          {title}
        </h2>
        {lead ? <p className="max-w-2xl text-body text-muted">{lead}</p> : null}
        <hr className="rule-gold mt-2 opacity-70" />
      </div>
      {children}
    </section>
  );
}

function Swatch({name, variable, hex}: {name: string; variable: string; hex: string}) {
  return (
    <figure className="flex flex-col gap-2">
      <div
        className="h-16 rounded-md border border-ground-border"
        style={{backgroundColor: `var(${variable})`}}
      />
      <figcaption className="flex flex-col gap-0.5">
        <span className="text-label text-cream normal-case tracking-normal">{name}</span>
        <span className="tabular text-label text-muted normal-case tracking-normal">{hex}</span>
      </figcaption>
    </figure>
  );
}

export default async function StyleguidePage({params}: PageProps<'/[locale]/styleguide'>) {
  const {locale} = await params;
  const resolvedLocale = isAppLocale(locale) ? locale : defaultLocale;

  setRequestLocale(resolvedLocale);
  const t = await getTranslations('common');

  return (
    <Container as="main" className="flex flex-col gap-16 py-14">
      {/* ------------------------------------------------------------ hero */}
      <header className="flex flex-col gap-5">
        <span className="text-label text-gold-300 uppercase">Design system</span>
        <h1 className="font-display text-hero text-gold-gradient max-w-[14ch]">Refined Gold</h1>
        <p className="max-w-2xl text-body text-cream/75">
          Gold treated as a precious accent on a warm near-black ground — an embossed menu card
          in a dimly lit dining room, never a yellow website. Every value below is a CSS custom
          property; no component in this codebase contains a hex literal.
        </p>
        <dl className="flex flex-wrap gap-2">
          {CONTRAST_PAIRS.map((item) => (
            <div key={item.pair} className="contents">
              <dt className="sr-only">{item.pair}</dt>
              <dd>
                <Badge tone="outline">
                  <span className="normal-case tracking-normal">{item.pair}</span>
                  <span className="tabular text-gold-100">{item.ratio}</span>
                  <span className="text-gold-400">{item.grade}</span>
                </Badge>
              </dd>
            </div>
          ))}
        </dl>
      </header>

      {/* ----------------------------------------------------------- colour */}
      <Section
        id="colour"
        title="Colour"
        lead="Four ground steps carry every surface; the gold ramp is spent sparingly on top of them."
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {GROUND_SWATCHES.map((swatch) => (
            <Swatch key={swatch.name} {...swatch} />
          ))}
        </div>

        <div className="grid grid-cols-5 gap-3 sm:grid-cols-10">
          {GOLD_SWATCHES.map((swatch) => (
            <Swatch key={swatch.name} {...swatch} />
          ))}
        </div>

        <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
          {OTHER_SWATCHES.map((swatch) => (
            <Swatch key={swatch.name} {...swatch} />
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------------ gold material */}
      <Section
        id="material"
        title="Gold as material"
        lead="Flat gold reads as yellow. A 135° gradient with a light band at the midpoint reads as brushed metal. Never above roughly a quarter of the viewport."
      >
        <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
          <div className="flex flex-col gap-4">
            <div className="bg-gold-gradient flex h-24 items-center justify-center rounded-lg shadow-card">
              <span className="font-display text-title text-ink">--gradient-gold</span>
            </div>
            <hr className="rule-gold" />
            <p className="text-body text-muted">
              Used on primary buttons, the logo ring, the active category pill, price badges and
              hairline dividers — nothing larger.
            </p>
          </div>

          <div className="flex items-center justify-center gap-6 rounded-lg border border-ground-border bg-ground-surface p-6">
            <span className="bg-gold-gradient flex size-20 items-center justify-center rounded-pill shadow-card">
              <span className="flex size-16 items-center justify-center rounded-pill bg-ground-base font-display text-title text-gold-300">
                B
              </span>
            </span>
            <Badge tone="gold" numeric>
              30 000
            </Badge>
          </div>
        </div>
      </Section>

      {/* ------------------------------------------------------- typography */}
      <Section
        id="typography"
        title="Typography"
        lead="Playfair Display for anything that names or prices a dish; Inter for everything else. Both self-hosted, both with Cyrillic."
      >
        <div className="flex flex-col divide-y divide-ground-border">
          {TYPE_SPECIMENS.map((specimen) => (
            <div
              key={specimen.token}
              className="flex flex-col gap-2 py-6 md:flex-row md:items-baseline md:gap-8"
            >
              <div className="flex w-56 shrink-0 flex-col gap-1">
                <code className="text-label text-gold-300 normal-case tracking-normal">
                  {specimen.token}
                </code>
                <span className="text-label text-muted normal-case tracking-normal">
                  {specimen.spec}
                </span>
              </div>
              <p className={`${specimen.className} text-cream`}>Choyxona shirinligi</p>
            </div>
          ))}
        </div>

        <Card className="max-w-sm">
          <CardHeader>
            <CardTitle>text-price · tabular-nums</CardTitle>
          </CardHeader>
          <CardBody className="flex flex-col gap-2">
            {['9 500', '30 000', '125 000'].map((price) => (
              <div key={price} className="flex items-baseline justify-between gap-6">
                <span className="text-body text-cream/70">Price row</span>
                <span className="tabular font-display text-price text-gold-200">{price}</span>
              </div>
            ))}
          </CardBody>
        </Card>
      </Section>

      {/* --------------------------------------------- radius and elevation */}
      <Section
        id="surface"
        title="Radius & elevation"
        lead="A 4px base scale, and shadows tinted with the ground so nothing casts a neutral grey halo."
      >
        <div className="grid gap-6 md:grid-cols-2">
          <div className="flex flex-wrap items-end gap-6 rounded-lg border border-ground-border bg-ground-surface p-8">
            {RADII.map((radius) => (
              <figure key={radius.token} className="flex flex-col items-center gap-2">
                <div
                  className={`size-20 border border-gold-600 bg-ground-elevated ${radius.className}`}
                />
                <figcaption className="flex flex-col items-center gap-0.5 text-center">
                  <code className="text-label text-gold-300 normal-case tracking-normal">
                    {radius.token}
                  </code>
                  <span className="tabular text-label text-muted normal-case tracking-normal">
                    {radius.value}
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>

          {/*
            The elevation samples sit on `ground-surface` rather than on the page
            ground: a warm shadow is only legible when it falls on a surface
            lighter than itself.
          */}
          <div className="flex flex-wrap items-end gap-8 rounded-lg border border-ground-border bg-ground-surface p-8">
            {ELEVATIONS.map((elevation) => (
              <figure key={elevation.token} className="flex flex-col items-center gap-3">
                <div
                  className={`size-20 rounded-md border border-ground-border bg-ground-elevated ${elevation.className}`}
                />
                <figcaption className="text-label text-muted normal-case tracking-normal">
                  {elevation.token}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------- buttons */}
      <Section
        id="buttons"
        title="Buttons, pills & badges"
        lead="One gold call to action per view. Every target clears 44×44px, and every one of them has a visible focus ring."
      >
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" size="lg">
            Primary
          </Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
          <Button variant="secondary" size="sm">
            Small
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Pill active>All</Pill>
          <Pill>Salads</Pill>
          <Pill>Hot dishes</Pill>
          <Pill>Desserts</Pill>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="gold" numeric>
            30 000
          </Badge>
          <Badge tone="outline">Featured</Badge>
          <Badge tone="neutral">Draft</Badge>
          <Badge tone="success">Available</Badge>
          <Badge tone="warning">Missing ru</Badge>
          <Badge tone="danger">Hidden</Badge>
        </div>
      </Section>

      {/* ------------------------------------------------------------- cards */}
      <Section
        id="cards"
        title="Product card"
        lead="The primary object of the menu. No image resolves to a gold monogram, never to a broken picture."
      >
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {DEMO_PRODUCTS.map((product) => (
            <Card key={product.name} interactive className="overflow-hidden">
              <div className="relative">
                <MonogramPlaceholder name={product.name} className="aspect-[4/3] w-full" />
                <span className="absolute top-3 left-3">
                  <Badge tone="neutral" className="bg-ground-elevated/85 text-gold-200 backdrop-blur-sm">
                    {product.category}
                  </Badge>
                </span>
              </div>
              <CardHeader>
                <CardTitle>{product.name}</CardTitle>
              </CardHeader>
              <CardFooter>
                <span className="text-label text-muted normal-case tracking-normal">so&apos;m</span>
                <Badge tone="gold" numeric>
                  {product.price}
                </Badge>
              </CardFooter>
            </Card>
          ))}

          <SkeletonCard />
        </div>
      </Section>

      {/* ------------------------------------------------------------- forms */}
      <Section
        id="forms"
        title="Forms, dialog & toasts"
        lead="Labels are always visible, errors are announced through aria-describedby, and the modal is a native <dialog> so the focus trap comes from the platform."
      >
        <StyleguideDemos />
      </Section>

      {/* ------------------------------------------------------------ states */}
      <Section
        id="states"
        title="Loading & empty states"
        lead="A blank region is indistinguishable from a broken one, so every list resolves to something."
      >
        <div className="grid gap-6 md:grid-cols-2">
          <EmptyState
            title={t('state.empty')}
            description={t('errors.notFound')}
            action={<Button variant="secondary">{t('actions.back')}</Button>}
          />

          <Card className="flex flex-col items-center justify-center gap-5 p-10">
            <Spinner size="lg" label={t('state.loading')} />
            <Toast message={t('state.saved')} tone="success" closeLabel={t('actions.close')} />
          </Card>
        </div>
      </Section>
    </Container>
  );
}
