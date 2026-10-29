import { createTheme } from '@mui/material/styles';
import { defaultWorkspaceMode, workspaceCssVariables, workspacePalettes } from './themeTokens';

export const createWorkspaceTheme = (mode = defaultWorkspaceMode) => {
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
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: '"Segoe UI", system-ui, sans-serif',
      h4: { fontWeight: 600, letterSpacing: '-0.03em', fontSize: '1.75rem' },
      h6: { fontWeight: 600, fontSize: '1rem', letterSpacing: '-0.015em' },
      body2: { lineHeight: 1.6 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: { styleOverrides: {
        ':root': { ...workspaceCssVariables(mode), colorScheme: mode },
        body: { fontVariantNumeric: 'tabular-nums', colorScheme: mode },
      } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none', border: `1px solid ${p.border}`, borderRadius: 20, boxShadow: 'none' } } },
      MuiButton: { styleOverrides: {
        root: { minHeight: 42, borderRadius: 12, paddingInline: 18 },
        contained: { boxShadow: 'none', '&:hover': { boxShadow: 'none' } },
        containedPrimary: { '&:hover': { backgroundColor: p.accentHover } },
      } },
      MuiOutlinedInput: { styleOverrides: {
        root: { background: p.control, borderRadius: 12, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: p.accent }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderWidth: 2 } },
        notchedOutline: { borderColor: p.controlBorder },
      } },
      MuiInputLabel: { styleOverrides: { root: { color: p.muted } } },
      MuiTab: { styleOverrides: { root: { textTransform: 'none', minHeight: 44, fontWeight: 600, fontSize: '.8125rem', borderRadius: 12 } } },
      MuiTabs: { styleOverrides: { indicator: { transition: 'left 260ms cubic-bezier(.22, 1, .36, 1), width 260ms cubic-bezier(.22, 1, .36, 1)' } } },
      MuiAlert: { styleOverrides: { root: { backgroundColor: p.raised, color: p.text, borderRadius: 16 }, icon: { color: p.muted } } },
      MuiTooltip: { styleOverrides: { tooltip: { background: p.surface, color: p.text, border: `1px solid ${p.border}`, borderRadius: 12, boxShadow: `0 8px 24px ${p.shadow}24`, fontSize: '.8rem', padding: '10px 12px' }, arrow: { color: p.surface } } },
    },
  });
};
export default createWorkspaceTheme();
