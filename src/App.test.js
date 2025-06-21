import { render, screen } from '@testing-library/react';
import App from './App';

test('renders learn react link', () => {
  render(<App />);
  // This is a basic test to ensure the canvas is rendered.
  // A more thorough test would require a WebGL context, which is complex to set up in jsdom.
  const canvasElement = document.querySelector('canvas');
  expect(canvasElement).toBeInTheDocument();
});
