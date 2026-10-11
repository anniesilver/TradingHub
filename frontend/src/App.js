import React, { useMemo, useState } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Dashboard from './pages/Dashboard';
import './App.css';
import { createWorkspaceTheme } from './theme';
import AppearanceContext from './AppearanceContext';

function App() {
  const [mode, setMode] = useState('dark');
  const theme = useMemo(() => createWorkspaceTheme(mode), [mode]);
  return (
    <AppearanceContext.Provider value={{ mode, setMode }}>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="app" data-theme={mode}>
        <Dashboard />
      </div>
    </ThemeProvider>
    </AppearanceContext.Provider>
  );
}

export default App;
