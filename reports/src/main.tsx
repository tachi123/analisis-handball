import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './style.css'
import './sapa-theme.css'
import './sapa-theme-fixes.css'

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
