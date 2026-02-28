import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { Menu, Bell, Settings, X, CheckCircle, AlertCircle, LogOut } from 'lucide-react'
import Sidebar, { SIDEBAR_W } from './Sidebar'
import { useAuth } from '../context/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'

// Données de notifications fictives pour la démo
const MOCK_NOTIFICATIONS = [
  { id: 1, title: 'Nouveau dossier', message: 'Un nouveau dossier a été créé', time: '5 min', read: false, type: 'info' },
  { id: 2, title: 'Dossier non conforme', message: 'Le dossier DOS-2024-0140 a été marqué comme non conforme', time: '1 heure', read: false, type: 'warning' },
  { id: 3, title: 'SMS envoyé', message: 'Notification envoyée au propriétaire du dossier DOS-2024-0139', time: '3 heures', read: true, type: 'success' },
  { id: 4, title: 'Maintenance prévue', message: 'Une maintenance est prévue ce soir à 22h', time: '1 jour', read: true, type: 'info' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS)
  const { user } = useAuth()
  const navigate = useNavigate()
  
  const unreadCount = notifications.filter(n => !n.read).length
  
  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })))
  }
  
  const goToSettings = () => {
    setNotificationsOpen(false)
    navigate('/parametres')
  }

  // Composant pour le widget de notifications
  const NotificationsWidget = () => (
    <AnimatePresence>
      {notificationsOpen && (
        <motion.div 
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className="absolute top-full right-0 mt-2 w-80 bg-white rounded-lg shadow-lg overflow-hidden z-50"
          style={{ boxShadow: 'var(--shadow-lg)' }}
        >
          <div className="p-3 border-b border-neutral-100 flex items-center justify-between">
            <h3 className="font-display font-bold text-sm text-neutral-800">Notifications</h3>
            <div className="flex gap-1">
              <button 
                onClick={markAllAsRead}
                className="text-xs text-neutral-500 hover:text-neutral-700 px-2 py-1 rounded hover:bg-neutral-100 transition-colors"
              >
                Tout marquer comme lu
              </button>
              <button 
                onClick={() => setNotificationsOpen(false)}
                className="text-neutral-400 hover:text-neutral-600 p-1 rounded-full hover:bg-neutral-100 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          </div>
          
          <div className="max-h-[300px] overflow-y-auto">
            {notifications.length > 0 ? (
              <div className="divide-y divide-neutral-100">
                {notifications.map(notif => (
                  <div 
                    key={notif.id} 
                    className={`p-3 hover:bg-neutral-50 transition-colors cursor-pointer ${!notif.read ? 'bg-blue-50/30' : ''}`}
                  >
                    <div className="flex gap-3">
                      <div className="shrink-0 mt-0.5">
                        {notif.type === 'success' && <CheckCircle size={18} className="text-green-500" />}
                        {notif.type === 'warning' && <AlertCircle size={18} className="text-orange-500" />}
                        {notif.type === 'info' && <Bell size={18} className="text-blue-500" />}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-neutral-800">{notif.title}</p>
                        <p className="text-xs text-neutral-600 mt-0.5">{notif.message}</p>
                        <p className="text-[10px] text-neutral-400 mt-1">{notif.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-neutral-400">
                <p className="text-sm">Aucune notification</p>
              </div>
            )}
          </div>
          
          <div className="p-2 border-t border-neutral-100 bg-neutral-50">
            <button 
              onClick={goToSettings}
              className="w-full text-xs text-neutral-600 py-2 rounded hover:bg-neutral-100 transition-colors flex items-center justify-center gap-1"
            >
              <Settings size={12} />
              Paramètres de notifications
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )

  return (
    <div className="min-h-screen bg-[#F0F4F8]">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Contenu principal décalé à droite sur desktop */}
      <div
        className="min-h-screen flex flex-col transition-all duration-300 w-full"
        style={{ marginLeft: 0 }}
      >
        {/* Topbar mobile */}
        <header
          className="md:hidden fixed top-0 left-0 right-0 z-20 flex items-center justify-between px-4 h-14 bg-white"
          style={{ borderBottom: '1px solid var(--neutral-200)', boxShadow: 'var(--shadow-sm)' }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="w-9 h-9 flex items-center justify-center rounded-md text-neutral-700 hover:bg-neutral-100 transition-colors"
            aria-label="Ouvrir le menu"
          >
            <Menu size={22} />
          </button>

          <span className="font-display font-bold text-base text-neutral-900">
            Dos<span style={{ color: 'var(--ci-orange)' }}>Tracker</span>
          </span>

          <div className="relative">
            <button
              className="w-9 h-9 flex items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-100 transition-colors"
              aria-label="Notifications"
              onClick={() => setNotificationsOpen(!notificationsOpen)}
            >
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            <NotificationsWidget />
          </div>
        </header>

        {/* Topbar desktop (après sidebar) */}
        <header
          className={`hidden md:flex fixed top-0 right-0 z-10 h-14 items-center justify-between px-6 bg-white`}
          style={{
            left: SIDEBAR_W,
            borderBottom: '1px solid var(--neutral-200)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <p className="font-display font-bold text-sm text-neutral-800">
            {user?.label ?? ''}
          </p>
          <div className="relative">
            <button
              className="w-9 h-9 flex items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-100 transition-colors"
              aria-label="Notifications"
              onClick={() => setNotificationsOpen(!notificationsOpen)}
            >
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            <NotificationsWidget />
          </div>
        </header>

        {/* Zone page */}
        <main
          className="flex-1 pt-14 w-full overflow-x-hidden md:pl-64"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
