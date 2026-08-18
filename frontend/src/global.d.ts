import type {AppMessages} from '@/i18n/messages';
import type {AppLocale} from '@/i18n/routing';

declare module 'next-intl' {
  interface AppConfig {
    Locale: AppLocale;
    Messages: AppMessages;
  }
}

export {};
