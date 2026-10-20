import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SimulationTransition, { foldedScenes, WaveBackdrop } from './WaveSurface';

const originalMatchMedia = window.matchMedia;
test('six scenes have distinct planes with compatible native morph commands', () => {
  expect(foldedScenes).toHaveLength(6);
  ['upper', 'lower', 'middle'].forEach(plane => {
    expect(new Set(foldedScenes.map(scene => scene[plane])).size).toBe(6);
    const commands = foldedScenes[0][plane].match(/[A-Za-z]/g);
    foldedScenes.forEach(scene => expect(scene[plane].match(/[A-Za-z]/g)).toEqual(commands));
  });
});

test('finite morphs restart on the persistent SVG clock', () => {
  const original = SVGElement.prototype.beginElement;
  const begin = jest.fn();
  SVGElement.prototype.beginElement = begin;
  try {
    const { rerender } = render(<WaveBackdrop scene={0} />);
    expect(begin).not.toHaveBeenCalled();
    rerender(<WaveBackdrop scene={3} />);
    expect(begin).toHaveBeenCalledTimes(3);
    rerender(<WaveBackdrop scene={4} />);
    expect(begin).toHaveBeenCalledTimes(6);
  } finally {
    if (original) SVGElement.prototype.beginElement = original;
    else delete SVGElement.prototype.beginElement;
  }
});

test('local artwork IDs keep multiple mounted backdrops independent', () => {
  const { container } = render(<><WaveBackdrop /><WaveBackdrop scene={2} /></>);
  const ids = Array.from(container.querySelectorAll('[id]'), element => element.id);
  expect(new Set(ids).size).toBe(ids.length);
  container.querySelectorAll('use').forEach(use => {
    const referenced = document.getElementById(use.getAttribute('href').slice(1));
    expect(use.closest('svg')).toContainElement(referenced);
  });
});

test('rapid scene changes replace finite morphs, without adding old layers or replaying after reduced motion', () => {
  const { container, rerender } = render(<WaveBackdrop scene={0} />);
  rerender(<WaveBackdrop scene={2} />);
  rerender(<WaveBackdrop scene={5} />);
  expect(container.querySelectorAll('[data-fold]')).toHaveLength(3);
  container.querySelectorAll('animate').forEach(animation => {
    const plane = animation.parentElement.getAttribute('data-fold');
    expect(animation).toHaveAttribute('values', `${foldedScenes[2][plane]};${foldedScenes[5][plane]}`);
    expect(animation).toHaveAttribute('repeatCount', '1');
    expect(animation).toHaveAttribute('dur', '.72s');
    expect(animation.parentElement).toHaveAttribute('d', foldedScenes[5][plane]);
  });
  rerender(<WaveBackdrop scene={5} reducedMotion />);
  rerender(<WaveBackdrop scene={5} reducedMotion={false} />);
  expect(container.querySelector('animate')).toBeNull();
});

test.each(['(prefers-reduced-motion: reduce)', '(prefers-contrast: more)', '(forced-colors: active)'])(
  'live preference %s stops ambient layers and cancels native morphs', preference => {
    const listeners = new Map();
    const queries = new Map();
    window.matchMedia = query => {
      if (!queries.has(query)) queries.set(query, { matches: false,
        addEventListener: jest.fn((_, callback) => listeners.set(query, callback)), removeEventListener: jest.fn() });
      return queries.get(query);
    };
    const { container, rerender, unmount } = render(<WaveBackdrop scene={0} />);
    rerender(<WaveBackdrop scene={1} />);
    expect(container.querySelectorAll('animate')).toHaveLength(3);
    act(() => { queries.get(preference).matches = true; listeners.get(preference)(); });
    expect(container.querySelector('svg')).toHaveAttribute('data-paused', 'true');
    expect(container.querySelector('animate')).toBeNull();
    expect(container.querySelector('.fold-highlight')).toBeInTheDocument();
    unmount();
    queries.forEach(query => expect(query.removeEventListener).toHaveBeenCalled());
  }
);
test('background pauses for hidden tabs and manual motion reduction', () => {
  const { container, rerender } = render(<WaveBackdrop />);
  const background = container.querySelector('svg');
  expect(background).toHaveAttribute('data-paused', 'false');
  const hidden = jest.spyOn(document, 'hidden', 'get').mockReturnValue(true);
  fireEvent(document, new Event('visibilitychange'));
  expect(background).toHaveAttribute('data-paused', 'true');
  hidden.mockRestore();
  rerender(<WaveBackdrop reducedMotion />);
  expect(background).toHaveAttribute('data-paused', 'true');
  expect(background.style.getPropertyValue('--scroll-y')).toBe('0px');
});

test('scroll parallax is bounded and pending frames are cleaned up', () => {
  const raf = jest.spyOn(window, 'requestAnimationFrame').mockReturnValue(123);
  const cancel = jest.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  const scroll = window.scrollY;
  window.scrollY = 999999;
  const { container, unmount } = render(<WaveBackdrop />);
  expect(container.querySelector('svg').style.getPropertyValue('--scroll-y')).toBe(`${-Math.min(16, window.innerHeight * .01)}px`);
  fireEvent.scroll(window);
  fireEvent.scroll(window);
  expect(raf).toHaveBeenCalledTimes(1);
  unmount();
  expect(cancel).toHaveBeenCalledWith(123);
  raf.mockRestore(); cancel.mockRestore(); window.scrollY = scroll;
});
afterEach(() => { window.matchMedia = originalMatchMedia; });

test('cleans up the decorative wipe after its animation ends', () => {
  render(<SimulationTransition reducedMotion={false} />);
  const wipe = screen.getByTestId('simulation-transition');
  expect(wipe).toHaveAttribute('aria-hidden', 'true');
  expect(wipe).toHaveAttribute('focusable', 'false');
  expect(wipe.querySelector('animate')).toHaveAttribute('repeatCount', '1');
  fireEvent.animationEnd(wipe);
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
});

test('Escape cancels the wipe without needing focus', () => {
  render(<SimulationTransition reducedMotion={false} />);
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
});

test('manual and system reduced motion suppress SVG animation', () => {
  const { rerender } = render(<SimulationTransition reducedMotion />);
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  window.matchMedia = () => ({ matches: true, addEventListener: jest.fn(), removeEventListener: jest.fn() });
  rerender(<SimulationTransition key="system" reducedMotion={false} />);
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
});

test('a fresh run key replays and cancels the old transition', () => {
  const { rerender } = render(<SimulationTransition key="first" reducedMotion={false} />);
  const first = screen.getByTestId('simulation-transition');
  rerender(<SimulationTransition key="second" reducedMotion={false} />);
  expect(screen.getByTestId('simulation-transition')).not.toBe(first);
  expect(first).not.toBeInTheDocument();
});

test('hiding the tab cancels rather than postpones the animation', () => {
  render(<SimulationTransition reducedMotion={false} />);
  const hidden = jest.spyOn(document, 'hidden', 'get').mockReturnValue(true);
  fireEvent(document, new Event('visibilitychange'));
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  hidden.mockReturnValue(false);
  fireEvent(document, new Event('visibilitychange'));
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
  hidden.mockRestore();
});

test('reenabling motion does not resurrect a cancelled run', () => {
  const { rerender } = render(<SimulationTransition reducedMotion={false} />);
  rerender(<SimulationTransition reducedMotion />);
  rerender(<SimulationTransition reducedMotion={false} />);
  expect(screen.queryByTestId('simulation-transition')).not.toBeInTheDocument();
});
