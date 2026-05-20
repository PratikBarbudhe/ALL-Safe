import { Search, Bell, User, ShieldCheck } from 'lucide-react';

export default function Header() {
  return (
    <header className="h-16 flex items-center justify-between px-6 border-b" style={{ backgroundColor: '#0F172A', borderColor: '#1E293B' }}>
      {/* Search Bar */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" style={{ color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search threats, processes, logs..."
            className="w-full pl-10 pr-4 py-2 rounded-lg outline-none transition-all"
            style={{
              backgroundColor: '#1E293B',
              color: '#F8FAFC',
              border: '1px solid #334155',
            }}
          />
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Protection Status */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg" style={{ backgroundColor: '#1E293B' }}>
          <ShieldCheck className="w-5 h-5" style={{ color: '#10B981' }} />
          <div className="flex flex-col">
            <span className="text-xs" style={{ color: '#94A3B8' }}>Protection</span>
            <span className="text-sm" style={{ color: '#10B981' }}>Active</span>
          </div>
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg transition-colors hover:bg-opacity-80" style={{ backgroundColor: '#1E293B' }}>
          <Bell className="w-5 h-5" style={{ color: '#94A3B8' }} />
          <div className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></div>
        </button>

        {/* User Profile */}
        <button className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors" style={{ backgroundColor: '#1E293B' }}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <p className="text-sm" style={{ color: '#F8FAFC' }}>Admin</p>
            <p className="text-xs" style={{ color: '#94A3B8' }}>System Admin</p>
          </div>
        </button>
      </div>
    </header>
  );
}
