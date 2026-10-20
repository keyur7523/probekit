import { Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Test Cases', href: '/test-cases', icon: DocumentIcon },
  { name: 'Evaluations', href: '/evaluations', icon: ChartIcon },
  { name: 'Annotations', href: '/annotations', icon: TagIcon },
  { name: 'Version Comparison', href: '/version-comparison', icon: CompareIcon },
]

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
    </svg>
  )
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  )
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  )
}

function TagIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.568 3.444a2.25 2.25 0 00-1.591.659L3.72 8.363a2.25 2.25 0 00-.659 1.591V15a2.25 2.25 0 002.25 2.25h5.046a2.25 2.25 0 001.591-.659l6.313-6.313a2.25 2.25 0 000-3.182L12.75 3.444a2.25 2.25 0 00-3.182 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h.008v.008H7.5V7.5z" />
    </svg>
  )
}

function CompareIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7.5h6m-6 9h6m6-9h6m-6 9h6M9 3.75v16.5m6-16.5v16.5" />
    </svg>
  )
}

// h-10 link + mb-1 gap: the pill moves in steps of one row
const NAV_ROW_PX = 44

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const activeIndex = navigation.findIndex((item) =>
    item.href === '/' ? location.pathname === '/' : location.pathname.startsWith(item.href)
  )

  return (
    <div className="min-h-screen">
      {/* Sidebar: a translucent material layer */}
      <div className="material fixed inset-y-0 left-0 z-50 w-64 bg-white/70 backdrop-blur-xl backdrop-saturate-150 border-r border-black/5">
        <div className="flex h-16 items-center gap-2.5 px-6">
          <div className="w-8 h-8 bg-gradient-to-b from-indigo-500 to-indigo-700 rounded-lg shadow-sm flex items-center justify-center">
            <span className="text-white font-semibold text-sm">BE</span>
          </div>
          <span className="text-lg font-semibold tracking-tight text-gray-900">Behavioral Eval</span>
        </div>
        <nav className="relative mt-4 px-3">
          <div
            aria-hidden="true"
            className="nav-pill absolute left-3 right-3 top-0 h-10 rounded-lg bg-indigo-600/10"
            style={{ transform: `translateY(${Math.max(activeIndex, 0) * NAV_ROW_PX}px)`, opacity: activeIndex < 0 ? 0 : 1 }}
          />
          {navigation.map((item, index) => {
            const isActive = index === activeIndex
            return (
              <Link
                key={item.name}
                to={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={`relative flex h-10 items-center gap-3 px-3 rounded-lg mb-1 ${
                  isActive ? 'text-indigo-700' : 'text-gray-600 hover:bg-black/[0.04] hover:text-gray-900'
                }`}
              >
                <item.icon className={`w-5 h-5 ${isActive ? 'text-indigo-600' : 'text-gray-400'}`} />
                <span className="font-medium text-[15px]">{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main content: re-keyed per route so each page fades in */}
      <div className="pl-64">
        <main key={location.pathname} className="page-enter p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
