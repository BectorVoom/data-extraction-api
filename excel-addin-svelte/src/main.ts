import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

// Initialize Office.js and mount Svelte app when ready
function initializeApp() {
  const app = mount(App, {
    target: document.getElementById('app')!,
  })
  return app
}

// Check if Office.js is available (for Excel Add-in mode)
if (typeof (globalThis as any).Office !== 'undefined') {
  // Wait for Office.js to be ready before mounting the app
  (globalThis as any).Office.onReady(() => {
    console.log('Office.js is ready, mounting Svelte app');
    initializeApp();
  });
} else {
  // Fallback for standalone development mode
  console.log('Office.js not available, mounting Svelte app in standalone mode');
  initializeApp();
}

export default null
