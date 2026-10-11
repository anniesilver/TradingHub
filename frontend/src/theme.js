import { createTheme } from '@mui/material/styles';

// Glass is limited to context/configuration; charts remain opaque.
export const createWorkspaceTheme = (mode = 'dark') => {
const light = mode === 'light';
const theme = createTheme({
  palette: {
    mode,
    primary: { main: light ? '#202020' : '#f5f5f5', contrastText: light ? '#ffffff' : '#090909' },
    secondary: { main: light ? '#353535' : '#eeeeee' },
    background: { default: light ? '#f3f3f1' : '#090909', paper: light ? '#ffffff' : '#141414' },
    text: { primary: light ? '#202020' : '#f4f4f4', secondary: light ? '#595959' : '#aaaaaa' },
    divider: light ? '#d0d0cc' : '#333333',
    success: { main: light ? '#353535' : '#dddddd' },
    error: { main: light ? '#353535' : '#eeeeee' },
    warning: { main: light ? '#353535' : '#dddddd' },
    info: { main: light ? '#353535' : '#f5f5f5' },
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
    MuiCssBaseline: { styleOverrides: { body: { fontVariantNumeric: 'tabular-nums', colorScheme: mode } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none', border: `1px solid ${light ? '#d0d0cc' : '#333333'}` } } },
    MuiButton: { styleOverrides: { root: { minHeight: 40 }, contained: { boxShadow: '0 4px 14px #0003' } } },
    MuiOutlinedInput: { styleOverrides: { root: { background: light ? '#ffffff' : '#101010', borderRadius: 2 } } },
    MuiTab: { styleOverrides: { root: { textTransform: 'none', minHeight: 52, fontWeight: 600 } } },
    MuiTabs: { styleOverrides: { indicator: { transition: 'left 260ms cubic-bezier(.22, 1, .36, 1), width 260ms cubic-bezier(.22, 1, .36, 1)' } } },
    // Status remains explicit in icons/text, not tinted backgrounds.
    MuiAlert: { styleOverrides: { root: { backgroundColor: light ? '#eeeeeb' : '#1b1b1b', color: light ? '#202020' : '#eeeeee' }, icon: { color: light ? '#353535' : '#dddddd' } } },
    MuiTooltip: { styleOverrides: { tooltip: { background: '#252525', color: '#f4f4f4', fontSize: '0.8rem', padding: '10px 12px' } } },
  },
});

return theme;
};
export default createWorkspaceTheme();
