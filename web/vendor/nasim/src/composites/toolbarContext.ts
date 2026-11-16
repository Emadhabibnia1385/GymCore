'use client';

import { createContext, use } from 'react';

// What the frame of a list toolbar tells every control in it, so no control is handed it by hand.
type ToolbarState = { isDisabled: boolean };

const ToolbarContext = createContext<ToolbarState>({ isDisabled: false });

export const ToolbarProvider = ToolbarContext;

export function useToolbar(): ToolbarState {
  return use(ToolbarContext);
}
