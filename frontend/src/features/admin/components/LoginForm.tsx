'use client';

import {useRouter} from 'next/navigation';
import {useTranslations} from 'next-intl';
import {useState, type FormEvent} from 'react';

import {Button, Input, Toast} from '@/components/ui';
import {RETURN_TO_PARAM} from '@/middleware-auth';

import type {LoginErrorKey} from '../constants';

/**
 * The only place credentials are typed.
 *
 * They are posted to `/api/auth/login`, which performs the token exchange on
 * the server; this component never sees, stores or forwards a token. The whole
 * client-side result of a successful login is a navigation.
 */

export interface LoginFormProps {
  /** Path to return to, already validated on the server. */
  returnTo: string;
  /** Failure reported by the no-script POST, echoed back in the query string. */
  initialError?: LoginErrorKey | null;
}

function errorKeyFor(status: number, code: unknown): LoginErrorKey {
  if (status === 429) return 'throttled';
  if (code === 'invalid_request') return 'invalidRequest';
  if (code === 'invalid_credentials') return 'invalidCredentials';
  return 'unavailable';
}

export function LoginForm({returnTo, initialError = null}: LoginFormProps) {
  const t = useTranslations('admin.login');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const [pending, setPending] = useState(false);
  const [errorKey, setErrorKey] = useState<LoginErrorKey | null>(initialError);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;

    const form = new FormData(event.currentTarget);
    setPending(true);
    setErrorKey(null);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          username: form.get('username'),
          password: form.get('password'),
          next: returnTo
        })
      });

      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        const code = typeof body === 'object' && body !== null ? Reflect.get(body, 'error') : null;
        setErrorKey(errorKeyFor(response.status, code));
        return;
      }

      // `refresh()` discards the router cache so the admin layout re-renders on
      // the server, this time with a session.
      router.replace(returnTo);
      router.refresh();
    } catch {
      setErrorKey('unavailable');
    } finally {
      setPending(false);
    }
  }

  return (
    /*
     * A real `POST` to the route handler, upgraded by `onSubmit` when the
     * script is running. Without the method and action a submit that outran
     * hydration — or a chunk that failed to load — would fall back to the
     * browser default of `GET`, putting the password in the URL and in
     * history. The two paths hit the same handler.
     */
    <form
      method="post"
      action="/api/auth/login"
      onSubmit={handleSubmit}
      noValidate
      className="flex flex-col gap-5"
    >
      <input type="hidden" name={RETURN_TO_PARAM} value={returnTo} />

      <Input
        label={t('username')}
        name="username"
        autoComplete="username"
        autoCapitalize="none"
        spellCheck={false}
        required
        autoFocus
      />

      <Input
        label={t('password')}
        name="password"
        type="password"
        autoComplete="current-password"
        required
      />

      {/* `role="alert"` so the failure is announced, not just repainted. */}
      <div role="alert">
        {errorKey ? (
          <Toast
            message={t(`errors.${errorKey}`)}
            tone="danger"
            closeLabel={tCommon('actions.close')}
            className="w-full"
          />
        ) : null}
      </div>

      <Button
        type="submit"
        variant="primary"
        size="lg"
        block
        data-testid="admin-login-submit"
        disabled={pending}
      >
        {pending ? t('submitting') : t('submit')}
      </Button>
    </form>
  );
}
