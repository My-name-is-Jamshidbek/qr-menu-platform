# Message catalog

One directory per locale, one JSON file per namespace:

```
messages/
  uz/common.json   -> namespace "common"
  ru/common.json
  en/common.json
```

`uz` is the default locale and the fallback: any key missing from `ru` or `en`
is deep-merged in from `uz` at request time, so a partially translated namespace
never renders a raw key.

## Adding a namespace

Drop `messages/<locale>/<namespace>.json` into every locale directory and run:

```bash
npm run gen:messages
```

That regenerates `src/i18n/catalog.generated.ts`, a **static** import map (no
filesystem access, so it works in the edge runtime). `gen:messages` also runs
automatically before `npm run dev` and `npm run build`.

The file name becomes the top-level namespace, so parallel work on
`menu.json`, `admin.json` and `tables.json` cannot collide. Use it like:

```tsx
const t = useTranslations('common.nav');
t('menu');
```

## Rules

- Keys are English, values are user-facing translations. Never hardcode a
  user-facing string in a component.
- `uz` must contain every key. `ru` and `en` may lag behind.
- Keep the key structure identical across locales; the generated
  `AppConfig["Messages"]` type is derived from the `uz` catalog.
