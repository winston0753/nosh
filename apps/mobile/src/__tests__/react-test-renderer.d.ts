// Minimal typings for the parts of react-test-renderer (an explicit dev
// dependency pinned to the React version; it ships without bundled types) that
// the screen tests use.  Declared locally to avoid adding
// @types/react-test-renderer as a dependency.
declare module 'react-test-renderer' {
  import type { ElementType, ReactElement } from 'react';

  export interface ReactTestInstance {
    readonly type: ElementType;
    readonly props: Record<string, unknown> & {
      testID?: string;
      onPress?: () => void;
      children?: unknown;
    };
    find(predicate: (node: ReactTestInstance) => boolean): ReactTestInstance;
    findAll(predicate: (node: ReactTestInstance) => boolean): ReactTestInstance[];
    findAllByType(type: ElementType): ReactTestInstance[];
  }

  export interface ReactTestRenderer {
    readonly root: ReactTestInstance;
    unmount(): void;
  }

  export function create(element: ReactElement): ReactTestRenderer;
  export function act(callback: () => void | Promise<void>): Promise<void>;
}
