import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// import the application-wide context providers
import { SettingsProvider } from './context/SettingsContext.tsx'
import { JobProvider } from './context/JobContext.tsx'
import { ToolsProvider } from './context/ToolsContext.tsx'


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SettingsProvider>
      <ToolsProvider>
        <JobProvider>
          <App />
        </JobProvider>
      </ToolsProvider>
    </SettingsProvider>
  </React.StrictMode>,
)
