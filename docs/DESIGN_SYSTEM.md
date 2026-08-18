# Design System — "Refined Gold"

The visual identity is gold, as in the original app, but gold is treated as a **precious accent
on a dark, warm ground** — never as a flat page background. The reference feeling is an
embossed menu card in a dimly lit dining room, not a yellow website.

## Why the original failed

| Original | Problem | Fix |
|---|---|---|
| `#D4AF37` as full-page background | Cheap, fatiguing, no hierarchy | Dark warm ground; gold reserved for accents |
| White text on `#D4AF37` | Contrast ≈ 2.0:1 — fails WCAG AA | Ink text on gold (≈ 8:1), gold text on dark (≈ 9:1) |
| Every element gold | Nothing stands out | One gold accent per visual group |
| System font stack | Generic | Serif display + humanist sans |
| Inline `style={{...}}` objects | 60% of each file is CSS | Tailwind tokens |

## Color tokens

Defined as CSS custom properties on `:root`, consumed through Tailwind theme extension.
Never hardcode a hex value in a component.

```
/* Ground — warm near-black, not pure grey */
--ground-base      #0E0D0B
--ground-surface   #17150F
--ground-elevated  #211D14
--ground-border    #2E2819

/* Gold ramp */
--gold-50   #FBF6E8
--gold-100  #F5EACB
--gold-200  #EBD79C
--gold-300  #E0C36C
--gold-400  #D4AF37   /* original brand anchor */
--gold-500  #BF9A2A
--gold-600  #9A7A1F
--gold-700  #6E5716
--gold-800  #45360E
--gold-900  #241C07

/* Neutrals */
--cream     #F7F3E8
--ink       #1A1712
--muted     #8C8574

/* Semantic */
--success   #3F7D5A
--danger    #A63D3D
--warning   #B8862B
```

**Contrast rules (enforced, WCAG AA minimum):**

- Text on `--ground-*` → `--cream` (≈ 15:1) or `--gold-300` (≈ 9:1)
- Text on gold fill → `--ink` only. **Never white on gold.**
- `--muted` is for non-essential text at 14px+ only
- Focus ring: `--gold-300`, 2px, 2px offset — always visible, never `outline: none`

## Gold as material

Flat gold reads as yellow. Gold reads as metal when it has a gradient with a light band:

```css
--gradient-gold: linear-gradient(135deg,
  var(--gold-600) 0%, var(--gold-300) 42%,
  var(--gold-200) 50%, var(--gold-400) 58%, var(--gold-700) 100%);
```

Use on: primary buttons, the logo ring, active category pill, price badges, hairline dividers.
Do **not** use on large areas — it becomes noise above roughly 25% of the viewport.

## Typography

Self-host with `next/font` — no external font requests (CSP-safe, no layout shift).

- **Display** — `Playfair Display` (serif, has Cyrillic). Headings, product names, prices.
- **Body** — `Inter` (has Cyrillic). Everything else.

```
--text-hero    clamp(2.5rem, 6vw, 4.5rem)   Playfair 600, tracking -0.02em
--text-title   clamp(1.5rem, 3vw, 2rem)     Playfair 600
--text-card    1.125rem                     Playfair 600
--text-body    1rem                          Inter 400, line-height 1.6
--text-label   0.8125rem                     Inter 500, tracking 0.08em, uppercase
--text-price   1.125rem                      Playfair 600, tabular-nums
```

`tabular-nums` on every price so digits align down a column.

## Spacing, radius, elevation

4px base scale. Radius: `sm 6px`, `md 10px`, `lg 16px`, `pill 999px`.

Elevation is warm, never neutral grey:
```
--shadow-card  0 1px 2px rgb(14 13 11 / .30), 0 8px 24px -8px rgb(14 13 11 / .45)
--shadow-modal 0 24px 64px -12px rgb(14 13 11 / .65)
```

## Component rules

**Product card** — the primary object; it must look worth eating.
- Image 4:3, `object-fit: cover`, gold hairline border, `lg` radius
- Category label: small pill, `--ground-elevated` at 85% opacity over the image, `--gold-200` text
- Name in Playfair on `--ground-surface`; price right-aligned in a gold-gradient badge with ink text
- Hover/focus: 1.02 scale + shadow lift, 180ms `ease-out`. Skipped under `prefers-reduced-motion`
- No image → a gold monogram placeholder, never a broken `<img>`

**Category filter** — real links (`/uz/menu/desserts`), not `useState`. Active pill uses the gold
gradient with ink text. Horizontally scrollable on mobile with edge fade, keyboard-navigable.

**Buttons** — primary: gold gradient + ink text. Secondary: transparent + gold border + gold text.
Danger: `--danger` fill + cream text. Minimum hit area 44×44px.

**Admin panel** — same tokens, calmer application: mostly `--ground-surface`, gold only on primary
actions and active rows. It is a tool, not a showpiece.

## Layout

Mobile-first — most traffic arrives by scanning a QR code at a table.

- Content max-width `1200px`, gutters `clamp(16px, 4vw, 32px)`
- Menu grid: 1 col < 640px, 2 < 1024px, 3 < 1280px, 4 above
- Sticky header, 64px tall, `backdrop-filter: blur(12px)` over `--ground-base` at 80%

## Non-negotiables

1. No hardcoded hex values in components — tokens only
2. No white text on gold, ever
3. Every interactive element has a visible focus state
4. Every image has meaningful `alt`, driven by the product's translated name
5. All motion respects `prefers-reduced-motion`
6. Lighthouse ≥ 95 on Performance, Accessibility, Best Practices, SEO
7. Public menu page weight < 500 KB on first load (original was ~10 MB)
