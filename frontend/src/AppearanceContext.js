import { createContext } from 'react';
// Session-only display preferences; never change scenario or saved user data.
export default createContext({ mode: 'dark', setMode: () => {} });
