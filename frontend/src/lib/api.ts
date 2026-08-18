import 'server-only';

/**
 * Server-side client for the Django API.
 *
 * The browser never talks to the API directly: `API_INTERNAL_URL` is a
 * server-only variable (no `NEXT_PUBLIC_` prefix) pointing at an address that
 * may not even be routable from the internet, and JWTs live in httpOnly
 * cookies. The `server-only` import above turns any accidental client import
 * into a build error.
 */

/** Cache tags used with `revalidateTag()` from the API's revalidation webhook. */
export const CACHE_TAGS = {
  /** Anything derived from the menu: categories, products, images. */
  menu: 'menu'
} as const;

export type CacheTag = (typeof CACHE_TAGS)[keyof typeof CACHE_TAGS];

/** Per-field validation messages, as sent by DRF serializers. */
export type FieldErrors = Record<string, string[]>;

/** Error payload shape from the API contract. */
type ErrorPayload = {
  detail?: unknown;
  code?: unknown;
  field_errors?: unknown;
};

/** A non-2xx response, or a transport failure (`status` is then 0). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldErrors;
  readonly path: string;

  constructor(init: {
    message: string;
    status: number;
    code: string;
    fieldErrors?: FieldErrors;
    path: string;
    cause?: unknown;
  }) {
    super(init.message, {cause: init.cause});
    this.name = 'ApiError';
    this.status = init.status;
    this.code = init.code;
    this.fieldErrors = init.fieldErrors ?? {};
    this.path = init.path;
  }

  /** The request never reached the API (DNS, connection refused, timeout). */
  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

export type QueryValue = string | number | boolean | null | undefined;

export type ApiRequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  /** Appended as a query string; `null` and `undefined` entries are dropped. */
  query?: Record<string, QueryValue>;
  /** JSON-encoded, unless it is a `FormData` (image upload → multipart). */
  body?: unknown;
  /** JWT access token for `/admin/*` and `/auth/me/`. Never sent otherwise. */
  accessToken?: string;
  /** Next.js cache tags; pass `CACHE_TAGS.menu` for menu-derived data. */
  tags?: readonly string[];
  /** Seconds until revalidation, or `false` to cache until a tag is purged. */
  revalidate?: number | false;
  /** Escape hatch for requests that must never be cached (auth, mutations). */
  cache?: RequestCache;
  /** Defaults to 10s so a hanging API cannot hold a render open. */
  timeoutMs?: number;
  signal?: AbortSignal;
};

const DEFAULT_TIMEOUT_MS = 10_000;

function getBaseUrl(): string {
  const baseUrl = process.env.API_INTERNAL_URL;

  if (!baseUrl) {
    throw new Error(
      'API_INTERNAL_URL is not set. It must point at the Django API base path, e.g. http://api:8000/api/v1'
    );
  }

  return baseUrl.replace(/\/+$/, '');
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(`${getBaseUrl()}/${path.replace(/^\/+/, '')}`);

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

function asFieldErrors(value: unknown): FieldErrors {
  if (typeof value !== 'object' || value === null) return {};

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([, messages]) => Array.isArray(messages))
      .map(([field, messages]) => [field, (messages as unknown[]).map(String)])
  );
}

async function toApiError(response: Response, path: string): Promise<ApiError> {
  let payload: ErrorPayload = {};

  try {
    payload = (await response.json()) as ErrorPayload;
  } catch {
    // Non-JSON error body (proxy timeout, HTML 502) — the status carries the meaning.
  }

  return new ApiError({
    message: typeof payload.detail === 'string' ? payload.detail : response.statusText || 'API request failed',
    status: response.status,
    code: typeof payload.code === 'string' ? payload.code : `http_${response.status}`,
    fieldErrors: asFieldErrors(payload.field_errors),
    path
  });
}

function buildRequestInit(options: ApiRequestOptions, signal: AbortSignal): RequestInit {
  const {method = 'GET', body, accessToken, tags, revalidate, cache} = options;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  const headers: Record<string, string> = {Accept: 'application/json'};
  if (body !== undefined && !isFormData) {
    // FormData sets its own multipart boundary; overriding it breaks the upload.
    headers['Content-Type'] = 'application/json';
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const init: RequestInit = {
    method,
    headers,
    signal,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body)
  };

  if (cache) {
    init.cache = cache;
  } else if (tags?.length || revalidate !== undefined) {
    init.next = {
      ...(tags?.length ? {tags: [...tags]} : {}),
      ...(revalidate !== undefined ? {revalidate} : {})
    };
  } else if (method !== 'GET') {
    init.cache = 'no-store';
  }

  return init;
}

/**
 * Performs one API call and returns the parsed JSON body.
 *
 * @throws {ApiError} on any non-2xx response or transport failure.
 */
export async function apiFetch<TResponse>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<TResponse> {
  const url = buildUrl(path, options.query);
  const timeout = AbortSignal.timeout(options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;

  let response: Response;
  try {
    response = await fetch(url, buildRequestInit(options, signal));
  } catch (cause) {
    throw new ApiError({
      message: `Could not reach the API at ${path}`,
      status: 0,
      code: cause instanceof Error && cause.name === 'TimeoutError' ? 'timeout' : 'network_error',
      path,
      cause
    });
  }

  if (!response.ok) {
    throw await toApiError(response, path);
  }

  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

/** `apiFetch` for public, menu-derived data: cached until the `menu` tag is purged. */
export function fetchMenuData<TResponse>(
  path: string,
  options: Omit<ApiRequestOptions, 'tags' | 'revalidate' | 'accessToken'> = {}
): Promise<TResponse> {
  return apiFetch<TResponse>(path, {
    ...options,
    tags: [CACHE_TAGS.menu],
    revalidate: false
  });
}
