// Shared MUI/CSS/SVG materials; data-series colors stay independent.
export const workspacePalettes = {
  dark: {
    background: '#0C0E16', surface: '#141824', raised: '#252D40', highlight: '#9CAAC5',
    accent: '#A5B4FC', accentHover: '#C7D2FE', onAccent: '#101224',
    text: '#F3F4FA', muted: '#B0B8CA', border: '#61708B', control: '#111520',
    glass: 'rgba(20, 24, 36, .91)', glassBorder: 'rgba(165, 180, 252, .23)',
    selection: '#29314B', hover: '#20273B', shadow: '#070913',
    reflection: '#6875AF', paper: '#343F57', texture: '#D9E2F5',
  },
  light: {
    background: '#F5F5FB', surface: '#FFFFFF', raised: '#E7EAF4', highlight: '#BCC6DB',
    accent: '#4F46E5', accentHover: '#4338CA', onAccent: '#FFFFFF',
    text: '#181B2A', muted: '#535E73', border: '#8995AD', control: '#FFFFFF',
    glass: 'rgba(255, 255, 255, .93)', glassBorder: 'rgba(79, 70, 229, .2)',
    selection: '#E4E6FA', hover: '#EDEFF9', shadow: '#C1C8DC',
    reflection: '#CBCDF3', paper: '#F0F2FA', texture: '#66738F',
  },
};

export function workspaceCssVariables(mode = 'dark') {
  const p = workspacePalettes[mode];
  return {
    '--workspace-bg': p.background, '--surface': p.surface,
    '--workspace-text': p.text, '--workspace-muted': p.muted,
    '--workspace-border': p.border, '--workspace-accent': p.accent,
    '--accent-hover': p.accentHover, '--on-accent': p.onAccent,
    '--glass-bg': p.glass, '--glass-border': p.glassBorder,
    '--glass-shadow': `0 12px 40px ${p.shadow}30`,
    '--tooltip-bg': p.surface, '--fold-raised': p.raised,
    '--fold-highlight': p.highlight, '--fold-reflection': p.reflection,
    '--fold-paper': p.paper, '--fold-shadow': p.shadow, '--fold-texture': p.texture,
    '--wipe-base': p.raised, '--wipe-light': p.highlight, '--wipe-mid': p.reflection,
    '--chart-strategy': mode === 'light' ? '#1761ac' : '#72b7ff',
    '--chart-benchmark': mode === 'light' ? '#956000' : '#ffc16e',
    '--chart-margin': mode === 'light' ? '#7551a5' : '#c2a2ff',
    '--chart-cash': mode === 'light' ? '#087563' : '#65d6ba',
  };
}
