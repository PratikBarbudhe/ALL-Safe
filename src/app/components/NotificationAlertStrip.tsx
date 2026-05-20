import { Bell } from 'lucide-react';
import { notificationSeverityColors } from '@/lib/api';

interface NotificationAlertStripProps {
  message: string;
  severity?: string;
}

export default function NotificationAlertStrip({
  message,
  severity = 'warning',
}: NotificationAlertStripProps) {
  const colors = notificationSeverityColors(severity);
  return (
    <div
      className="mb-4 p-3 rounded-lg border text-sm flex items-center gap-2 transition-opacity duration-300"
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.color,
        color: colors.color,
      }}
    >
      <Bell className="w-4 h-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
