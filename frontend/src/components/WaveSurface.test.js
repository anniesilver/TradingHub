import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SimulationTransition, { WaveBackdrop } from './WaveSurface';

const originalMatchMedia = window.matchMedia;
test('all monochrome strata morph from the previous tab contour to the destination', () => {
  const { container, rerender } = render(<WaveBackdrop scene={0} />);
  const origin = screen.getByTestId('background-contour').getAttribute('d');
  rerender(<WaveBackdrop scene={2} />);
  const destination = screen.getByTestId('background-contour').getAttribute('d');
  expect(destination).not.toBe(origin);
  const animations = container.querySelectorAll('animate');
  expect(animations).toHaveLength(5);
  animations.forEach(animation => {
    expect(animation).toHaveAttribute('values', `${origin};${destination}`);
    expect(animation).toHaveAttribute('dur', '.72s');
  });
  rerender(<WaveBackdrop scene={1} reducedMotion />);
  expect(container.querySelector('animate')).toBeNull();
});
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
  expect(container.querySelector('svg').style.getPropertyValue('--scroll-y')).toBe('-64px');
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
