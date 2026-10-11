import React, { useRef } from 'react';
import { fireEvent, render } from '@testing-library/react';
import useWorkspaceTransition from './useWorkspaceTransition';

function Workspace({ run, reducedMotion = false }) {
  const content = useRef(null);
  useWorkspaceTransition(content, run, reducedMotion);
  return <main ref={content}><h1 className="workspace-header">Analysis</h1><div className="context-strip">Selected strategy</div><div className="workspace-status">Unavailable</div><form className="scenario-surface"><input defaultValue="321000" /></form><section className="analysis-results">Chart</section></main>;
}

test('information surfaces get distinct motion without animating the title or remounting inputs', () => {
  const original = Element.prototype.animate;
  const cancel = jest.fn();
  const animate = jest.fn(() => ({ cancel }));
  Element.prototype.animate = animate;
  const { container, rerender, unmount } = render(<Workspace run={0} />);
  const input = container.querySelector('input');
  expect(animate).not.toHaveBeenCalled();
  rerender(<Workspace run={1} />);
  expect(animate).toHaveBeenCalledTimes(4);
  expect(animate.mock.calls.map(([, options]) => options.duration)).toEqual([320, 240, 420, 360]);
  expect(new Set(animate.mock.calls.map(([frames]) => frames[0].transform)).size).toBe(4);
  rerender(<Workspace run={2} />);
  expect(cancel).toHaveBeenCalledTimes(4);
  expect(container.querySelector('input')).toBe(input);
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(cancel).toHaveBeenCalledTimes(8);
  unmount();
  Element.prototype.animate = original;
});

test('reduced motion skips shared surface animations', () => {
  const original = Element.prototype.animate;
  const animate = jest.fn();
  Element.prototype.animate = animate;
  render(<Workspace run={1} reducedMotion />);
  expect(animate).not.toHaveBeenCalled();
  Element.prototype.animate = original;
});
