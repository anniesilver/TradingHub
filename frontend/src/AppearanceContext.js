import { createContext } from 'react';
import { defaultWorkspaceMode } from './themeTokens';
// Session-only display preferences; never change scenario or saved user data.
export default createContext({ mode: defaultWorkspaceMode, setMode: () => {} });
