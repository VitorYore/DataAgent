import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import App from './App'
import { AnalysisProvider } from './contexts/AnalysisContext'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><BrowserRouter><AnalysisProvider><App /></AnalysisProvider></BrowserRouter></StrictMode>,
)
