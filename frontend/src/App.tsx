import { createBrowserRouter, RouterProvider } from 'react-router-dom'

// import pages
import JobListPage from './pages/JobListPage'
import ToolsListPage from './pages/ToolsListPage'

import MainLayout from './MainLayout'
import ToolDetailPage from './pages/ToolDetailPage'
import CreateJobPage from './pages/CreateJobPage'


const router = createBrowserRouter([
  {element: <MainLayout />, children: [
    {index: true, path: '/', element: <JobListPage />},
    {index: true, path: '/jobs', element: <JobListPage />},
    {path: '/tools', element: <ToolsListPage />},
    {path: '/tools/:toolName', element: <ToolDetailPage />},
    {path: '/tools/:toolName/create', element: <CreateJobPage />}
  ]}
])

function App() {
  return <RouterProvider router={router} />
}

export default App
