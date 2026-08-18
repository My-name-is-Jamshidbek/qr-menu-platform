import type {components} from '@/types/api';

/**
 * Shapes of the `tables` slice of the API.
 *
 * Everything the server sends is taken from the generated OpenAPI types rather
 * than restated here; only the shapes this feature invents — the form's input
 * and the result envelope its server actions resolve to — are declared locally.
 */

/** DRF's pagination envelope around the admin table list. */
export type TablePage = components['schemas']['PaginatedAdminTableList'];

/** Aggregate counters from `GET /admin/stats/`; only the scan figure is used here. */
export type AdminStats = components['schemas']['Stats'];

/** Response of `POST /tables/{token}/scan/`. */
export type TableScanResult = components['schemas']['TableScanResponse'];

/**
 * One table as the administrator edits it.
 *
 * `scan_count` is an addition to the generated schema, not part of it: the
 * admin list is meant to show how busy each table is, but `AdminTableSerializer`
 * does not annotate the count yet. Typing it as optional means the column
 * lights up the moment the API starts sending it, and says "not available"
 * until then rather than rendering a zero that would read as "never used".
 */
export type AdminTable = components['schemas']['AdminTable'] & {
  scan_count?: number | null;
};

/** The writable half of a table — everything the create/edit form owns. */
export type TableInput = Required<components['schemas']['AdminTableRequest']>;

/** Per-field validation messages keyed by `TableInput` field name. */
export type TableFieldErrors = Partial<Record<keyof TableInput, string>>;

/**
 * What every table server action resolves to.
 *
 * A rejected promise would surface as an unhandled error boundary in the admin
 * UI; a discriminated result lets the form show the API's own field messages
 * next to the offending input instead.
 */
export type ActionResult<TData = undefined> =
  | {ok: true; data: TData}
  | {ok: false; message: string; fieldErrors: TableFieldErrors};
