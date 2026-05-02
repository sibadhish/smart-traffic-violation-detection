import { Link, Route, Routes, useLocation } from 'react-router-dom';
import Dashboard from './components/dashboard/Dashboard';
import ViolationList from './components/violations/ViolationList';
import ViolationDetail from './components/violations/ViolationDetail';
import UploadPage from './components/upload/UploadPage';
import CameraManagement from './components/cameras/CameraManagement';

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/violations', label: 'Violations' },
  { to: '/upload', label: 'Upload' },
  { to: '/cameras', label: 'Cameras' },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-gray-900">
                Traffic Violation Detection
              </Link>
            </div>
            <div className="flex items-center space-x-1">
              {navLinks.map((link) => {
                const active =
                  link.to === '/'
                    ? location.pathname === '/'
                    : location.pathname.startsWith(link.to);
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/violations" element={<ViolationList />} />
          <Route path="/violations/:id" element={<ViolationDetail />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/cameras" element={<CameraManagement />} />
        </Routes>
      </main>
    </div>
  );
}
