import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import TestCases from './pages/TestCases'
import Evaluations from './pages/Evaluations'
import EvaluationDetail from './pages/EvaluationDetail'
import Annotations from './pages/Annotations'
import VersionComparison from './pages/VersionComparison'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/test-cases" element={<TestCases />} />
        <Route path="/evaluations" element={<Evaluations />} />
        <Route path="/evaluations/:id" element={<EvaluationDetail />} />
        <Route path="/annotations" element={<Annotations />} />
        <Route path="/version-comparison" element={<VersionComparison />} />
      </Routes>
    </Layout>
  )
}

export default App
