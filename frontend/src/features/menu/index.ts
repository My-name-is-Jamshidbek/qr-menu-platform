/**
 * Public surface of the menu feature. Routes import from `@/features/menu`;
 * everything under `components/` and the helpers stay internal so the pieces can
 * be rearranged without touching the app directory.
 */
export {getMenu} from './api';
export {CategoryNav} from './components/CategoryNav';
export {MenuBrowser} from './components/MenuBrowser';
export {formatPrice, formatPriceAmount} from './format';
export {
  menuFilterPaths,
  resolveMenuView,
  UnknownMenuFilterError,
  type MenuFilterSegments
} from './selectors';
export type {
  MenuCategory,
  MenuImage,
  MenuProduct,
  MenuResponse,
  MenuSubcategory,
  MenuView,
  ProductGroup
} from './types';
