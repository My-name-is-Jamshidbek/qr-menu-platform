/**
 * Public surface of the admin feature. Pages import from here rather than from
 * individual files, so the internal layout of the feature can change without
 * touching the route segments.
 */
export {AdminShell, type AdminShellProps} from './components/AdminShell';
export {DeleteProductButton, type DeleteProductButtonProps} from './components/DeleteProductButton';
export {ImageManager, type ImageManagerProps} from './components/ImageManager';
export {LoginForm, type LoginFormProps} from './components/LoginForm';
export {ProductForm, type ProductFormProps} from './components/ProductForm';
export {ProductPagination, type ProductPaginationProps} from './components/ProductPagination';
export {ProductTable, type ProductTableProps} from './components/ProductTable';
export {ProductToolbar, type ProductToolbarProps} from './components/ProductToolbar';
export {StatCard, type StatCardProps} from './components/StatCard';

export {
  fetchCategories,
  fetchProduct,
  fetchProductPage,
  fetchStats,
  toCategoryOptions,
  translatedName
} from './data';

export {
  LIST_PARAMS,
  PRODUCTS_PAGE_SIZE,
  loginErrorKeyFromParam,
  type LoginErrorKey
} from './constants';
export type {AdminProduct, CategoryOption, ProductPage, ProductQuery} from './types';
