import {cookies} from 'next/headers';
import {NextResponse, type NextRequest} from 'next/server';

import {ApiError} from '@/lib/api';
import {fetchCurrentUser, obtainTokens, writeSessionCookies, type SessionUser} from '@/lib/auth';
import {
  RETURN_TO_PARAM,
  adminHome,
  adminLoginPath,
  localeFromPath,
  sanitiseReturnTo
} from '@/middleware-auth';

/**
 * `POST /api/auth/login` — the credential exchange, server side.
 *
 * The browser posts a username and password here and gets back nothing but the
 * account it just signed in as. The JWT pair is obtained from Django by this
 * handler and stored in httpOnly cookies, so the token never enters the
 * document, `localStorage`, or a JavaScript variable.
 *
 * Two request encodings are accepted for one reason: the login form posts JSON
 * through `fetch` when its script is running, and posts itself as a normal
 * `application/x-www-form-urlencoded` form when it is not. Without the second
 * path a failed script would leave the browser submitting the form with its
 * default method — putting the password in a URL, and in history.
 */

export const runtime = 'nodejs';
/** A login must never be served from a cache, at any layer. */
export const dynamic = 'force-dynamic';

/** Reasons the client can distinguish. The copy itself lives in the messages. */
export type LoginErrorCode = 'invalid_request' | 'invalid_credentials' | 'unavailable';

type LoginSuccess = {user: SessionUser};
type LoginFailure = {error: LoginErrorCode};

export type LoginResponseBody = LoginSuccess | LoginFailure;

type Credentials = {username: string; password: string; returnTo: string | null};

function readCredentials(source: {
  username: unknown;
  password: unknown;
  next: unknown;
}): Credentials | null {
  const {username, password, next} = source;
  if (typeof username !== 'string' || typeof password !== 'string') return null;
  if (username.trim() === '' || password === '') return null;

  return {
    username: username.trim(),
    password,
    returnTo: sanitiseReturnTo(typeof next === 'string' ? next : null)
  };
}

async function parseRequest(request: NextRequest): Promise<Credentials | null> {
  const contentType = request.headers.get('content-type') ?? '';

  if (contentType.includes('application/json')) {
    try {
      const payload = (await request.json()) as Record<string, unknown>;
      return readCredentials({
        username: payload.username,
        password: payload.password,
        next: payload.next
      });
    } catch {
      return null;
    }
  }

  const form = await request.formData();
  return readCredentials({
    username: form.get('username'),
    password: form.get('password'),
    next: form.get(RETURN_TO_PARAM)
  });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const isFormPost = !(request.headers.get('content-type') ?? '').includes('application/json');
  const credentials = await parseRequest(request);

  /** JSON callers get a status code; form callers get a redirect back. */
  function failure(code: LoginErrorCode, status: number, returnTo: string | null): NextResponse {
    if (!isFormPost) return NextResponse.json<LoginFailure>({error: code}, {status});

    const login = new URL(adminLoginPath(localeFromPath(returnTo), returnTo), request.url);
    login.searchParams.set('error', code);
    // 303 so the browser follows with GET and the password is not re-posted.
    return NextResponse.redirect(login, 303);
  }

  if (!credentials) return failure('invalid_request', 400, null);

  try {
    const tokens = await obtainTokens(credentials.username, credentials.password);
    const user = await fetchCurrentUser(tokens.access);

    // A valid token whose owner cannot be read back means the account is not
    // usable for the panel; refusing here keeps a half-session off the browser.
    if (!user) return failure('invalid_credentials', 401, credentials.returnTo);

    writeSessionCookies(await cookies(), tokens);

    if (isFormPost) {
      const target = credentials.returnTo ?? adminHome(localeFromPath(credentials.returnTo));
      return NextResponse.redirect(new URL(target, request.url), 303);
    }

    return NextResponse.json<LoginSuccess>({user});
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 400)) {
      // Deliberately the same code for "no such user" and "wrong password".
      return failure('invalid_credentials', 401, credentials.returnTo);
    }
    if (error instanceof ApiError && error.status === 429) {
      return failure('unavailable', 429, credentials.returnTo);
    }
    return failure('unavailable', 502, credentials.returnTo);
  }
}
