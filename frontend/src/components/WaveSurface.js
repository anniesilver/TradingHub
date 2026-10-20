import React, { useEffect, useId, useRef, useState } from 'react';

// A cut optical lens, rather than broad wallpaper ribbons. The aperture is a
// real hole (even-odd fill); ribs are clipped to the material, not the charts.
// Compatible commands retain the existing finite scene-morph contract.
const lens = (x, y, radius, aperture) => {
  const oval = r => `M ${x + r} ${y} C ${x + r} ${y + r * .56} ${x + r * .56} ${y + r} ${x} ${y + r} C ${x - r * .56} ${y + r} ${x - r} ${y + r * .56} ${x - r} ${y} C ${x - r} ${y - r * .56} ${x - r * .56} ${y - r} ${x} ${y - r} C ${x + r * .56} ${y - r} ${x + r} ${y - r * .56} ${x + r} ${y} Z`;
  return `${oval(radius)} ${oval(aperture)}`;
};
const poses = [
  [1080, 140, 1340, 430, 400, 680, 980, 350],
  [990, 210, 1410, 370, 480, 730, 1050, 310],
  [1160, 100, 1300, 490, 330, 610, 900, 410],
  [1030, 170, 1460, 450, 440, 650, 1120, 390],
  [1130, 230, 1380, 340, 360, 750, 950, 280],
  [1000, 90, 1280, 400, 520, 660, 1060, 450],
];
export const foldedScenes = poses.map(([cx, cy, fx, fy, lx, ly, mx, my]) => ({
  upper: lens(1260 + (cx - 1080) * .5, 100 + (cy - 140) * .5, 350 + (fx - 1340) * .2, 220 + (fy - 430) * .15),
  lower: lens(-60 + (lx - 400) * .5, 770 + (ly - 680) * .5, 290, 235),
  middle: `M ${mx} -120 L ${mx + 80} -120 L ${mx + 470} 900 L ${mx + 435} 900 Z`,
}));
const stillQueries = ['(prefers-reduced-motion: reduce)', '(prefers-contrast: more)', '(forced-colors: active)'];
const systemWantsStill = () => stillQueries.some(query => window.matchMedia?.(query).matches);

export function WaveBackdrop({ scene = 0, reducedMotion = false }) {
  const id = useId();
  const artwork = useRef(null);
  const [systemStill, setSystemStill] = useState(systemWantsStill);
  const canMorph = !reducedMotion && !systemStill && !document.hidden;
  const [morph, setMorph] = useState({ from: scene, to: scene });
  useEffect(() => {
    setMorph(previous => previous.to === scene && canMorph ? previous : { from: canMorph ? previous.to : scene, to: scene });
  }, [scene, canMorph]);
  const destination = foldedScenes[morph.to % foldedScenes.length];
  const origin = foldedScenes[morph.from % foldedScenes.length];
  const contourMotion = plane => canMorph && morph.from !== morph.to ? (
    <animate key={morph.to} attributeName="d" values={`${origin[plane]};${destination[plane]}`}
      dur=".72s" repeatCount="1" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".35 0 .65 1" />
  ) : null;
  useEffect(() => {
    // Restart finite native animations on the long-lived SVG's current clock.
    // Merely inserting begin="0s" after the SVG has loaded may skip a morph.
    artwork.current?.querySelectorAll('animate').forEach(animation => animation.beginElement?.());
  }, [morph]);

  useEffect(() => {
    const media = stillQueries.map(query => window.matchMedia?.(query)).filter(Boolean);
    let frame = 0;
    const still = () => reducedMotion || media.some(query => query.matches) || document.hidden;
    const syncScroll = () => {
      frame = 0;
      const range = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.max(0, Math.min(1, window.scrollY / range));
      // 1vh parallax leaves room for the bounded opposing plane movement.
      const displacement = Math.min(16, window.innerHeight * .01) * progress;
      artwork.current?.style.setProperty('--scroll-y', still() ? '0px' : `${-displacement}px`);
    };
    const schedule = () => {
      if (!frame && !still()) frame = window.requestAnimationFrame(syncScroll);
    };
    const update = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
      setSystemStill(media.some(query => query.matches));
      if (artwork.current) artwork.current.dataset.paused = String(still());
      if (still()) artwork.current?.pauseAnimations?.();
      else artwork.current?.unpauseAnimations?.();
      syncScroll();
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    document.addEventListener('visibilitychange', update);
    media.forEach(query => query.addEventListener('change', update));
    update();
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', update);
      document.removeEventListener('visibilitychange', update);
      media.forEach(query => query.removeEventListener('change', update));
    };
  }, [reducedMotion, scene]);

  return (
    <svg ref={artwork} data-scene={scene} className="workspace-wave-backdrop" viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={`${id}-light`} cx=".85" cy=".08" r=".85">
          <stop stopColor="var(--workspace-accent)" stopOpacity=".2" /><stop offset="1" stopColor="var(--workspace-bg)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}-metal`} x1="0" y1="0" x2="1" y2=".7">
          <stop stopColor="var(--fold-shadow)" /><stop offset=".3" stopColor="var(--fold-raised)" />
          <stop offset=".49" stopColor="var(--fold-highlight)" /><stop offset=".515" stopColor="var(--fold-paper)" />
          <stop offset=".65" stopColor="var(--fold-raised)" /><stop offset="1" stopColor="var(--workspace-bg)" />
        </linearGradient>
        <linearGradient id={`${id}-paper`} x1="0" y1="1" x2=".9" y2="0">
          <stop stopColor="var(--workspace-bg)" /><stop offset=".45" stopColor="var(--fold-paper)" />
          <stop offset=".7" stopColor="var(--fold-reflection)" /><stop offset=".72" stopColor="var(--fold-raised)" />
          <stop offset="1" stopColor="var(--fold-shadow)" />
        </linearGradient>
        <linearGradient id={`${id}-sheen`}>
          <stop stopColor="var(--fold-highlight)" stopOpacity="0" />
          <stop offset=".5" stopColor="var(--fold-highlight)" stopOpacity=".45" />
          <stop offset="1" stopColor="var(--workspace-accent)" stopOpacity="0" />
        </linearGradient>
        <pattern id={`${id}-grain`} width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M8 5h1 M26 17h1 M15 39h1 M42 32h1" stroke="var(--fold-texture)" strokeWidth=".7" />
        </pattern>
        <pattern id={`${id}-flutes`} width="13" height="13" patternUnits="userSpaceOnUse" patternTransform="rotate(-28)">
          <rect width="13" height="13" fill={`url(#${id}-rib)`} />
        </pattern>
        <linearGradient id={`${id}-rib`}>
          <stop stopColor="var(--fold-shadow)" stopOpacity=".7" />
          <stop offset=".4" stopColor="var(--fold-highlight)" stopOpacity=".04" />
          <stop offset=".72" stopColor="var(--fold-highlight)" stopOpacity=".7" />
          <stop offset="1" stopColor="var(--fold-shadow)" stopOpacity=".85" />
        </linearGradient>
        <pattern id={`${id}-registration`} width="80" height="80" patternUnits="userSpaceOnUse">
          <path d="M37 40h6 M40 37v6" fill="none" stroke="var(--fold-highlight)" strokeWidth=".7" />
        </pattern>
        <clipPath id={`${id}-upper-clip`}><use href={`#${id}-upper`} clipRule="evenodd" /></clipPath>
        <linearGradient id={`${id}-quiet`}>
          <stop stopColor="var(--workspace-bg)" stopOpacity=".96" />
          <stop offset=".18" stopColor="var(--workspace-bg)" stopOpacity=".88" />
          <stop offset=".55" stopColor="var(--workspace-bg)" stopOpacity=".12" />
          <stop offset="1" stopColor="var(--workspace-bg)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="var(--workspace-bg)" />
      <rect width="1600" height="900" fill={`url(#${id}-light)`} />
      <rect className="optical-registration" width="1600" height="900" fill={`url(#${id}-registration)`} opacity=".18" />
      <g className="fold-plane fold-plane-middle" opacity=".28">
        <path data-fold="middle" d={destination.middle} fill={`url(#${id}-paper)`} stroke="var(--fold-highlight)" strokeOpacity=".18">{contourMotion('middle')}</path>
      </g>
      <g className="fold-plane fold-plane-upper">
        <path id={`${id}-upper`} data-fold="upper" data-testid="background-contour" d={destination.upper}
          fill={`url(#${id}-metal)`} fillRule="evenodd" stroke="var(--fold-highlight)" strokeOpacity=".6" strokeWidth="1">{contourMotion('upper')}</path>
        <g clipPath={`url(#${id}-upper-clip)`}>
          <rect className="optical-flutes" width="1800" height="1000" y="-100" fill={`url(#${id}-flutes)`} />
          <rect className="fold-highlight" x="800" y="-250" width="300" height="1500" fill={`url(#${id}-sheen)`} />
        </g>
      </g>
      <g className="fold-plane fold-plane-lower">
        <path data-fold="lower" d={destination.lower} fill={`url(#${id}-paper)`}
          fillRule="evenodd" stroke="var(--fold-highlight)" strokeOpacity=".25" strokeWidth="1">{contourMotion('lower')}</path>
      </g>
      <rect className="fold-grain" width="1600" height="900" fill={`url(#${id}-grain)`} opacity=".055" />
      <rect width="1600" height="900" fill={`url(#${id}-quiet)`} />
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
          <stop stopColor="var(--wipe-base)" /><stop offset=".32" stopColor="var(--wipe-light)" /><stop offset=".49" stopColor="var(--wipe-mid)" /><stop offset=".52" stopColor="var(--wipe-base)" /><stop offset="1" stopColor="var(--wipe-base)" />
        </linearGradient>
      </defs>
      <path fill={`url(#${id}-wipe)`} d="M0 0 H1000 V780 C700 690 460 1010 0 870 Z">
        <animate attributeName="d" dur=".72s" repeatCount="1" fill="freeze" values="M0 0 H1000 V780 C700 690 460 1010 0 870 Z;M0 0 H1000 V920 C700 1080 460 640 0 950 Z;M0 0 H1000 V810 C700 740 460 1080 0 880 Z" />
      </path>
      <path fill="none" stroke="var(--fold-highlight)" strokeOpacity=".4" strokeWidth="1.5" d="M0 720 C360 860 680 560 1000 710">
        <animate attributeName="d" dur=".72s" repeatCount="1" fill="freeze" values="M0 720 C360 860 680 560 1000 710;M0 760 C360 500 680 930 1000 810;M0 780 C360 940 680 610 1000 720" />
      </path>
    </svg>
  );
}
