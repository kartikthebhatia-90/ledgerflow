import {
  BookOpenCheck,
  BrainCircuit,
  Calculator,
  ChartNoAxesCombined,
  Database,
  Gauge,
  Megaphone,
  Moon,
  PackageSearch,
  RefreshCw,
  Settings2,
  Sun,
  UsersRound,
  Waypoints,
} from 'lucide-react'
import type { Workspace } from './types'

const items: Array<{ id: Workspace; label: string; icon: typeof Gauge }> = [
  { id: 'overview', label: 'Overview', icon: Gauge },
  { id: 'money-map', label: 'Money map', icon: Waypoints },
  { id: 'accounts', label: 'Accounts', icon: BookOpenCheck },
  { id: 'inventory', label: 'Inventory', icon: PackageSearch },
  { id: 'tax', label: 'Tax', icon: Calculator },
  { id: 'hr', label: 'HR', icon: UsersRound },
  { id: 'marketing', label: 'Marketing', icon: Megaphone },
  { id: 'intelligence', label: 'Intelligence', icon: BrainCircuit },
  { id: 'decisions', label: 'Data management', icon: Database },
  { id: 'settings', label: 'Settings', icon: Settings2 },
]

interface Props {
  active: Workspace
  companyName: string
  modelLabel: string
  darkMode: boolean
  onNavigate: (workspace: Workspace) => void
  onToggleTheme: () => void
  onRefresh: () => void
}

export default function Sidebar({ active, companyName, modelLabel, darkMode, onNavigate, onToggleTheme, onRefresh }: Props) {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-mark">L</span>
        <div>
          <strong>LedgerFlow</strong>
          <small>{companyName || 'Local workspace'}</small>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Workspace sections">
        {items.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="sidebar-nav-tab" />
              <Icon size={17} />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-footer-row" onClick={onRefresh} title="Refresh data">
          <RefreshCw size={14} />
          <span>Refresh data</span>
        </button>
        <button className="sidebar-footer-row" onClick={onToggleTheme} title="Change appearance">
          {darkMode ? <Sun size={14} /> : <Moon size={14} />}
          <span>{darkMode ? 'Light mode' : 'Dark mode'}</span>
        </button>
        <div className="sidebar-model-status">
          <i />
          <small>{modelLabel}</small>
        </div>
      </div>
    </aside>
  )
}
