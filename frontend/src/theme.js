import { createTheme } from '@mui/material/styles';
import { workspaceCssVariables, workspacePalettes } from './themeTokens';

export const createWorkspaceTheme = (mode = 'dark') => {
  const p = workspacePalettes[mode];
  return createTheme({
    palette: {
      mode,
      primary: { main: p.accent, contrastText: p.onAccent },
      secondary: { main: p.accent },
      background: { default: p.background, paper: p.surface },
      text: { primary: p.text, secondary: p.muted },
      divider: p.border,
      action: { selected: p.selection, hover: p.hover },
      // The accent identifies interaction, never profit/loss or confidence.
      success: { main: p.text }, error: { main: p.text },
      warning: { main: p.text }, info: { main: p.accent },
    },
    shape: { borderRadius: 3 },
    typography: {
      fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      h4: { fontWeight: 650, letterSpacing: '-0.035em' },
      h6: { fontWeight: 600, fontSize: '1.05rem' },
      body2: { lineHeight: 1.6 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: { styleOverrides: {
        ':root': { ...workspaceCssVariables(mode), colorScheme: mode },
        body: { fontVariantNumeric: 'tabular-nums', colorScheme: mode },
      } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none', border: `1px solid ${p.border}` } } },
      MuiButton: { styleOverrides: {
        root: { minHeight: 40 },
        contained: { boxShadow: `0 4px 14px ${p.shadow}40` },
        containedPrimary: { '&:hover': { backgroundColor: p.accentHover } },
      } },
      MuiOutlinedInput: { styleOverrides: { root: { background: p.control, borderRadius: 2 }, notchedOutline: { borderColor: p.border } } },
      MuiTab: { styleOverrides: { root: { textTransform: 'none', minHeight: 52, fontWeight: 600 } } },
      MuiTabs: { styleOverrides: { indicator: { transition: 'left 260ms cubic-bezier(.22, 1, .36, 1), width 260ms cubic-bezier(.22, 1, .36, 1)' } } },
      MuiAlert: { styleOverrides: { root: { backgroundColor: p.surface, color: p.text }, icon: { color: p.muted } } },
      MuiTooltip: { styleOverrides: { tooltip: { background: p.surface, color: p.text, border: `1px solid ${p.border}`, fontSize: '.8rem', padding: '10px 12px' }, arrow: { color: p.surface } } },
    },
  });
};
export default createWorkspaceTheme();
