import React, { useEffect, useId, useRef, useState } from 'react';

// Each analysis tab has its own contour, not a simulated market movement.
const scenes = [
  'M-300 1080 C100 280 490 1100 820 420 S1300 10 1800 -250 L1800 1100 Z',
  'M-300 1100 C80 620 340 40 750 470 S1210 830 1800 -120 L1800 1100 Z',
  'M-300 1100 C170 200 570 910 1020 720 S1280 20 1800 250 L1800 1100 Z',
  'M-300 1100 C160 730 460 50 950 320 S1370 1010 1800 430 L1800 1100 Z',
  'M-300 1100 C170 390 630 1240 960 450 S1480 70 1800 220 L1800 1100 Z',
  'M-300 1100 C110 760 530 710 920 140 S1390 850 1800 520 L1800 1100 Z',
];
export function WaveBackdrop({ scene = 0, reducedMotion = false }) {
  const id = useId();
  const artwork = useRef(null);
  const [morph, setMorph] = useState({ from: scene, to: scene });
  useEffect(() => {
    setMorph(previous => previous.to === scene ? previous : { from: previous.to, to: scene });
  }, [scene]);
  const destination = scenes[morph.to % scenes.length];
  const origin = scenes[morph.from % scenes.length];
  const canMorph = !reducedMotion && !(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);
  const contourMotion = () => canMorph && morph.from !== morph.to ? <animate key={morph.to} attributeName="d" values={`${origin};${destination}`} dur=".72s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".35 0 .65 1" /> : null;
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    let frame = 0;
    const still = () => reducedMotion || media?.matches || document.hidden;
    const syncScroll = () => {
      frame = 0;
      const range = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.max(0, Math.min(1, window.scrollY / range));
      artwork.current?.style.setProperty('--scroll-y', still() ? '0px' : `${-64 * progress}px`);
    };
    // Only respond to input: no continuous JavaScript animation loop.
    const schedule = () => {
      if (!frame && !still()) frame = window.requestAnimationFrame(syncScroll);
    };
    const update = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
      if (artwork.current) artwork.current.dataset.paused = String(still());
      if (still()) artwork.current?.pauseAnimations?.();
      else artwork.current?.unpauseAnimations?.();
      syncScroll();
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    document.addEventListener('visibilitychange', update);
    media?.addEventListener('change', update);
    update();
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', update);
      document.removeEventListener('visibilitychange', update);
      media?.removeEventListener('change', update);
    };
  }, [reducedMotion, scene]);
  return (
    <svg ref={artwork} data-scene={scene} className="workspace-wave-backdrop" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-base`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="var(--wave-base, #111111)" /><stop offset="1" stopColor="var(--wave-depth, #252525)" />
        </linearGradient>
        <linearGradient id={`${id}-ridge`} x1="0" y1="1" x2="1" y2="0">
          <stop stopColor="var(--wave-depth, #1b1b1b)" /><stop offset=".48" stopColor="var(--wave-ridge, #696969)" /><stop offset=".62" stopColor="var(--wave-fold, #343434)" /><stop offset="1" stopColor="var(--wave-base, #111111)" />
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill={`url(#${id}-base)`} />
      <g className="background-current">
        <path d={destination} transform="translate(0,-180)" fill="var(--wave-band-light, #454545)">{contourMotion()}</path>
        <path d={destination} transform="translate(0,-100)" fill="var(--wave-band-mid, #292929)" stroke="var(--wave-edge, #8a8a8a)" strokeOpacity=".25">{contourMotion()}</path>
        <path data-testid="background-contour" d={destination} fill={`url(#${id}-ridge)`} stroke="var(--wave-edge, #8a8a8a)" strokeOpacity=".3" strokeWidth="2">{contourMotion()}</path>
        <path d={destination} transform="translate(0,110)" fill="var(--wave-band-dark, #151515)" stroke="var(--wave-edge, #8a8a8a)" strokeOpacity=".25">{contourMotion()}</path>
        <path d={destination} transform="translate(0,190)" fill="var(--wave-band-mid, #292929)" stroke="var(--wave-edge, #8a8a8a)" strokeOpacity=".15">{contourMotion()}</path>
      </g>
    </svg>
  );
}

export default function SimulationTransition({ reducedMotion, scene = 0 }) {
  const id = useId();
  const [active, setActive] = useState(() => !document.hidden);
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const updateMotion = event => setSystemReduced(event.matches);
    const hide = () => { if (document.hidden) setActive(false); };
    const escape = event => { if (event.key === 'Escape') setActive(false); };
    media?.addEventListener('change', updateMotion);
    document.addEventListener('visibilitychange', hide);
    document.addEventListener('keydown', escape);
    // animationend handles normal cleanup; this bounded fallback also cleans up
    // if a browser suppresses the CSS event. Never wait before starting the API.
    const cleanup = window.setTimeout(() => setActive(false), 900);
    return () => {
      window.clearTimeout(cleanup);
      media?.removeEventListener('change', updateMotion);
      document.removeEventListener('visibilitychange', hide);
      document.removeEventListener('keydown', escape);
    };
  }, []);

  useEffect(() => {
    // Turning motion back on must not resurrect a cancelled, older run.
    if (reducedMotion || systemReduced) setActive(false);
  }, [reducedMotion, systemReduced]);

  if (!active || reducedMotion || systemReduced) return null;

  return (
    <svg className="simulation-wave-transition" data-scene={scene} data-testid="simulation-transition" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true" focusable="false" onAnimationEnd={() => setActive(false)}>
      <defs>
        <linearGradient id={`${id}-wipe`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="var(--wipe-base, #131313)" /><stop offset=".32" stopColor="var(--wipe-light, #666666)" /><stop offset=".65" stopColor="var(--wipe-mid, #393939)" /><stop offset="1" stopColor="var(--wipe-base, #131313)" />
        </linearGradient>
      </defs>
      <path fill={`url(#${id}-wipe)`} d="M0 0 H1000 V780 C700 690 460 1010 0 870 Z">
        <animate attributeName="d" dur=".72s" repeatCount="1" fill="freeze" values="M0 0 H1000 V780 C700 690 460 1010 0 870 Z;M0 0 H1000 V920 C700 1080 460 640 0 950 Z;M0 0 H1000 V810 C700 740 460 1080 0 880 Z" />
      </path>
      <path fill="none" stroke="var(--wave-edge, #c6c6c6)" strokeOpacity=".4" strokeWidth="1.5" d="M0 720 C360 860 680 560 1000 710">
        <animate attributeName="d" dur=".72s" repeatCount="1" fill="freeze" values="M0 720 C360 860 680 560 1000 710;M0 760 C360 500 680 930 1000 810;M0 780 C360 940 680 610 1000 720" />
      </path>
    </svg>
  );
}
