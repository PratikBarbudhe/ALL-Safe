import { Toaster } from 'sonner';

/** In-app toast layer; sound can be wired via toast onShow callbacks later. */
export default function AllSafeToaster() {
  return (
    <Toaster
      position="top-right"
      theme="dark"
      richColors
      closeButton
      toastOptions={{
        style: {
          backgroundColor: '#1E293B',
          color: '#F8FAFC',
          border: '1px solid #334155',
        },
      }}
    />
  );
}
