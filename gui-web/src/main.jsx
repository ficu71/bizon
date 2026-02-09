import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import "@fontsource/space-grotesk/700.css";
import "@fontsource/space-grotesk/900.css";

const container = document.getElementById('root');
const root = createRoot(container);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
