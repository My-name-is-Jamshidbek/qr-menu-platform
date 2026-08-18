/**
 * The table cookie written by the QR landing route.
 *
 * A guest who scanned the code at table 7 keeps that context for the length of
 * a long meal; a future ordering feature reads the cookie server-side to know
 * where the food is going. The value is httpOnly, so no client script can claim
 * a table the guest never scanned.
 */

/** Cookie name fixed by `docs/DATA_MODEL.md`. */
export const TABLE_COOKIE_NAME = 'table';

/** Four hours — longer than any sitting, shorter than a shift. */
export const TABLE_COOKIE_MAX_AGE_SECONDS = 4 * 60 * 60;

/** Separates the two fields of the cookie value. */
const SEPARATOR = ':';

/** What the cookie carries: enough to address the table without a lookup. */
export interface TableSession {
  /** The scanned token, so a write can be authorised against the same table. */
  token: string;
  /** The number printed on the table, for display. */
  number: number;
}

/**
 * Encodes a session for cookie transport as `<number>:<token>`.
 *
 * Both halves are already cookie-safe — digits and a UUID — so the value needs
 * no percent-encoding. JSON would have needed it, and the encoding then happens
 * twice: once here and once in whichever cookie API writes the header.
 */
export function serializeTableSession(session: TableSession): string {
  return `${session.number}${SEPARATOR}${session.token}`;
}

/**
 * Decodes a cookie written by {@link serializeTableSession}.
 *
 * @returns the session, or `null` for a missing, truncated or tampered value —
 * callers then behave as if the guest had never scanned anything.
 */
export function parseTableSession(raw: string | undefined): TableSession | null {
  if (!raw) return null;

  const separatorAt = raw.indexOf(SEPARATOR);
  if (separatorAt <= 0) return null;

  const number = Number(raw.slice(0, separatorAt));
  const token = raw.slice(separatorAt + 1);

  if (!Number.isInteger(number) || number <= 0 || token.length === 0) return null;

  return {token, number};
}
