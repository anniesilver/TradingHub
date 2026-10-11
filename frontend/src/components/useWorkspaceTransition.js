import { useEffect } from 'react';

// Give each information surface its own entrance; never remount the form, lose focus,
// resize chart coordinates, or interpolate recorded market data.
export default function useWorkspaceTransition(content, run, reducedMotion) {
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!run || reducedMotion || media?.matches || document.hidden) return;
    const entrances = [
      ['.context-strip', { opacity: 0.5, transform: 'translateX(-12px)' }, 320],
      ['.workspace-status', { opacity: 0.4, transform: 'translateY(-6px)' }, 240],
      ['.scenario-surface', { opacity: 0.65, transform: 'translateY(14px)' }, 420],
      ['.analysis-results, .sample-preview', { opacity: 0.35, transform: 'translateX(8px)' }, 360],
    ];
    const animations = entrances.flatMap(([selector, start, duration]) =>
      Array.from(content.current?.querySelectorAll(selector) ?? [], element => element.animate?.([
        start, { opacity: 1, transform: 'translate(0, 0)' },
      ], { duration, easing: 'cubic-bezier(.22, 1, .36, 1)' })).filter(Boolean));
    const cancel = () => animations.forEach(animation => animation.cancel());
    const hide = () => { if (document.hidden) cancel(); };
    const escape = event => { if (event.key === 'Escape') cancel(); };
    const change = event => { if (event.matches) cancel(); };
    document.addEventListener('visibilitychange', hide);
    document.addEventListener('keydown', escape);
    media?.addEventListener('change', change);
    return () => {
      cancel();
      document.removeEventListener('visibilitychange', hide);
      document.removeEventListener('keydown', escape);
      media?.removeEventListener('change', change);
    };
  }, [content, run, reducedMotion]);
}
