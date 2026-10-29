// Shared MUI/CSS/SVG materials; data-series colors stay independent.
export const defaultWorkspaceMode = 'light';
export const workspacePalettes = {
  dark: {
    background: '#021024', shell: '#06172E', sidebar: '#071A32',
    surface: '#0A203C', raised: '#102D4D', highlight: '#C1E8FF',
    accent: '#C1E8FF', accentHover: '#E0F3FF', onAccent: '#052659',
    text: '#ECF6FF', muted: '#ADC4DB', border: '#294664', controlBorder: '#577594',
    control: '#071A32', glass: 'rgba(10, 32, 60, .88)',
    glassBorder: 'rgba(193, 232, 255, .2)', inset: 'rgba(193, 232, 255, .1)',
    selection: '#163C60', hover: '#113453', shadow: '#010A18',
    reflection: '#5483B3', paper: '#052659', texture: '#7DA0CA',
    chart: '#071A32', chartLabel: '#C9DDEF', chartGrid: '#426181',
  },
  light: {
    background: '#DBE9F4', shell: '#E9F2F9', sidebar: '#E2EEF8',
    surface: '#F8FCFF', raised: '#EDF5FB', highlight: '#FFFFFF',
    accent: '#052659', accentHover: '#123F70', onAccent: '#F8FCFF',
    text: '#092541', muted: '#4D6680', border: '#CBDDEB', controlBorder: '#829BB3',
    control: '#F7FBFF', glass: 'rgba(248, 252, 255, .88)',
    glassBorder: 'rgba(255, 255, 255, .88)', inset: 'rgba(255, 255, 255, .9)',
    selection: '#CBDFEF', hover: '#D9EAF6', shadow: '#284E73',
    reflection: '#7DA0CA', paper: '#C1E8FF', texture: '#5483B3',
    chart: '#F8FCFF', chartLabel: '#425D77', chartGrid: '#AEC4D8',
  },
};

export function workspaceCssVariables(mode = defaultWorkspaceMode) {
  const p = workspacePalettes[mode];
  return {
    '--workspace-bg': p.background, '--surface': p.surface,
    '--shell-bg': p.shell, '--sidebar-bg': p.sidebar, '--surface-raised': p.raised,
    '--control-bg': p.control, '--control-border': p.controlBorder,
    '--selection-bg': p.selection, '--hover-bg': p.hover,
    '--radius-card': '20px', '--radius-control': '12px', '--radius-pill': '999px',
    '--workspace-text': p.text, '--workspace-muted': p.muted,
    '--workspace-border': p.border, '--workspace-accent': p.accent,
    '--accent-hover': p.accentHover, '--on-accent': p.onAccent,
    '--glass-bg': p.glass, '--glass-border': p.glassBorder,
    '--glass-inset': p.inset, '--glass-shadow': `0 14px 38px ${p.shadow}16`,
    '--shell-shadow': `0 8px 24px ${p.shadow}0F`,
    '--tooltip-bg': p.surface, '--fold-raised': p.raised,
    '--fold-highlight': p.highlight, '--fold-reflection': p.reflection,
    '--fold-paper': p.paper, '--fold-shadow': p.shadow, '--fold-texture': p.texture,
    '--wipe-base': p.raised, '--wipe-light': p.highlight, '--wipe-mid': p.reflection,
    // Financial plots stay opaque, even when their surrounding panel is glass.
    '--chart-surface': p.chart, '--chart-label': p.chartLabel, '--chart-grid': p.chartGrid,
    '--chart-strategy': mode === 'light' ? '#2368A4' : '#8FCCFF',
    '--chart-benchmark': mode === 'light' ? '#8B5C17' : '#E5BF81',
    '--chart-margin': mode === 'light' ? '#7354A0' : '#C8B8EA',
    '--chart-cash': mode === 'light' ? '#177563' : '#81D6C0',
  };
}
