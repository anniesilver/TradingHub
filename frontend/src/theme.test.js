import { createWorkspaceTheme } from './theme';
import { workspaceCssVariables, workspacePalettes } from './themeTokens';

function luminance(hex) {
  const channels = hex.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255)
    .map(channel => channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4);
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
}
function contrast(a, b) {
  const [first, second] = [luminance(a), luminance(b)];
  return (Math.max(first, second) + .05) / (Math.min(first, second) + .05);
}

test.each(['dark', 'light'])('%s materials and interactive text meet AA contrast targets', mode => {
  const p = workspacePalettes[mode];
  [p.background, p.surface, p.raised, p.control].forEach(background => {
    expect(contrast(p.text, background)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(p.muted, background)).toBeGreaterThanOrEqual(4.5);
  });
  [p.background, p.surface, p.selection, p.hover].forEach(background => {
    expect(contrast(p.accent, background)).toBeGreaterThanOrEqual(4.5);
  });
  expect(contrast(p.onAccent, p.accent)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(p.onAccent, p.accentHover)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(p.border, p.control)).toBeGreaterThanOrEqual(3);
  const theme = createWorkspaceTheme(mode);
  expect(theme.palette.primary.main).toBe(p.accent);
  expect(theme.palette.background.paper).toBe(p.surface);
  expect(theme.shape.borderRadius).toBe(3);
  expect(theme.components.MuiCssBaseline.styleOverrides[':root']).toEqual(expect.objectContaining(workspaceCssVariables(mode)));
});

test('light mode has its own paper materials, not a filter inversion', () => {
  const dark = workspaceCssVariables('dark');
  const light = workspaceCssVariables('light');
  expect(dark['--workspace-bg']).toBe('#0C0E16');
  expect(light['--workspace-bg']).toBe('#F5F5FB');
  expect(light['--fold-raised']).toBe('#E7EAF4');
  expect(light['--workspace-accent']).toBe('#4F46E5');
  expect(dark['--chart-strategy']).toBe('#72b7ff');
  expect(light['--chart-strategy']).toBe('#1761ac');
  expect(dark['--chart-benchmark']).toBe('#ffc16e');
  expect(light['--chart-benchmark']).toBe('#956000');
});
