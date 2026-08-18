import type {ElementType, HTMLAttributes} from 'react';

import {cn} from '@/lib/cn';

export interface ContainerProps extends HTMLAttributes<HTMLElement> {
  /** Rendered element. Use `main`, `section` or `header` to keep the outline honest. */
  as?: ElementType;
  /** Drops the max-width so the content runs full-bleed, keeping the gutters. */
  wide?: boolean;
}

/**
 * The one content column: max-width 1200px with fluid gutters. Every page-level
 * region goes through this, which is what keeps left edges aligned between the
 * header, the menu grid and the footer.
 */
export function Container({as: Component = 'div', wide = false, className, ...props}: ContainerProps) {
  return (
    <Component
      className={cn('mx-auto w-full gutter-x', wide ? 'max-w-none' : 'max-w-content', className)}
      {...props}
    />
  );
}
