import { Shield, LayoutDashboard, Activity, Usb, AlertTriangle, FileText, Brain, Archive, Settings } from 'lucide-react';

interface SidebarProps {
  activeScreen: string;
  onNavigate: (screen: string) => void;
}

const menuItems = [
  { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'process-monitor', icon: Activity, label: 'Process Monitor' },
  { id: 'usb-protection', icon: Usb, label: 'USB Protection' },
  { id: 'ransomware', icon: AlertTriangle, label: 'Ransomware Detection' },
  { id: 'threat-logs', icon: FileText, label: 'Threat Logs' },
  { id: 'ai-analysis', icon: Brain, label: 'AI Threat Analysis' },
  { id: 'quarantine', icon: Archive, label: 'Quarantine' },
  { id: 'settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar({ activeScreen, onNavigate }: SidebarProps) {
  return (
    <div className="w-64 h-screen flex flex-col" style={{ backgroundColor: '#111827' }}>
      {/* Logo */}
      <div className="p-6 flex items-center gap-3 border-b" style={{ borderColor: '#1F2937' }}>
        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-500 to-cyan-500">
          <Shield className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-white font-semibold text-lg">AllSafe</h1>
          <p className="text-xs" style={{ color: '#94A3B8' }}>All Safe</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeScreen === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200"
              style={{
                backgroundColor: isActive ? '#1E293B' : 'transparent',
                color: isActive ? '#3B82F6' : '#94A3B8',
                borderLeft: isActive ? '3px solid #3B82F6' : '3px solid transparent',
              }}
            >
              <Icon className="w-5 h-5" />
              <span className="text-sm">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Protection Status */}
      <div className="p-4 m-4 rounded-lg" style={{ backgroundColor: '#1E293B' }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm" style={{ color: '#F8FAFC' }}>Real-time Protection</span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-xs" style={{ color: '#10B981' }}>Active</span>
          </div>
        </div>
        <div className="w-full h-1 rounded-full" style={{ backgroundColor: '#0F172A' }}>
          <div className="h-full w-full rounded-full bg-gradient-to-r from-green-500 to-emerald-500"></div>
        </div>
      </div>
    </div>
  );
}
