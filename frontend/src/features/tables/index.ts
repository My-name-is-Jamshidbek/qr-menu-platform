/**
 * Public surface of the tables feature's admin screen.
 *
 * The QR landing route imports `./api`, `./cookie` and `./negotiate-locale` by
 * path instead of through this barrel: those modules are tiny and run on the
 * request path of every scan, while this file pulls in the whole client-side
 * admin bundle behind `TablesManager`.
 */
export {TablesManager, type TablesManagerProps} from './components/TablesManager';
export type {AdminTable} from './types';
