import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import ProcessMonitor from './components/ProcessMonitor';
import UsbProtection from './components/UsbProtection';
import RansomwareDetection from './components/RansomwareDetection';
import ThreatLogs from './components/ThreatLogs';
import AiAnalysis from './components/AiAnalysis';
import Quarantine from './components/Quarantine';
import Settings from './components/Settings';
import AllSafeToaster from './components/AllSafeToaster';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { SettingsProvider } from '@/contexts/SettingsContext';
import { AppStatusProvider } from '@/contexts/AppStatusContext';
import AppConnectivityBanner from './components/AppConnectivityBanner';

export default function App() {
  const [activeScreen, setActiveScreen] = useState('dashboard');

  const renderScreen = () => {
    switch (activeScreen) {
      case 'dashboard':
        return <Dashboard />;
      case 'process-monitor':
        return <ProcessMonitor />;
      case 'usb-protection':
        return <UsbProtection />;
      case 'ransomware':
        return <RansomwareDetection />;
      case 'threat-logs':
        return <ThreatLogs />;
      case 'ai-analysis':
        return <AiAnalysis />;
      case 'quarantine':
        return <Quarantine />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <SettingsProvider>
      <AppStatusProvider>
        <NotificationProvider enableToasts>
          <div className="flex h-screen w-full" style={{ backgroundColor: '#0F172A' }}>
          <AllSafeToaster />
          <Sidebar activeScreen={activeScreen} onNavigate={setActiveScreen} />
          <div className="flex-1 flex flex-col overflow-hidden">
            <AppConnectivityBanner />
            <Header />
          <main className="flex-1 overflow-hidden">
            {renderScreen()}
          </main>
        </div>
          </div>
        </NotificationProvider>
      </AppStatusProvider>
    </SettingsProvider>
  );
}