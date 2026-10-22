// Shared MUI/CSS/SVG materials; data-series colors stay independent.
export const defaultWorkspaceMode = 'light';
export const workspacePalettes = {
  dark: {
    // Blue surfaces stay distinct from inputs and secondary text.
    background: '#1B385A', surface: '#23476B', raised: '#2C5278', highlight: '#BAD7F2',
    accent: '#ADD7FF', accentHover: '#D1E8FF', onAccent: '#102940',
    text: '#F5F9FF', muted: '#DFEAF6', border: '#A1BBD7', control: '#1C3B5C',
    glass: 'rgba(35, 71, 107, .97)', glassBorder: 'rgba(173, 215, 255, .5)',
    selection: '#30557A', hover: '#2A4E72', shadow: '#183552',
    reflection: '#5789BA', paper: '#3D648B', texture: '#D9E9FA',
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

export function workspaceCssVariables(mode = defaultWorkspaceMode) {
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
    // A brighter opaque plot keeps the artwork away from chart data.
    '--chart-surface': mode === 'light' ? '#FFFFFF' : '#2B5278',
    '--chart-label': mode === 'light' ? '#39465C' : '#F5F9FF',
    '--chart-grid': mode === 'light' ? '#8995AD' : '#B5CAE0',
    '--chart-strategy': mode === 'light' ? '#1761ac' : '#96CEFF',
    '--chart-benchmark': mode === 'light' ? '#956000' : '#FFD28A',
    '--chart-margin': mode === 'light' ? '#7551a5' : '#D4C0FF',
    '--chart-cash': mode === 'light' ? '#087563' : '#89E6D0',
  };
}
