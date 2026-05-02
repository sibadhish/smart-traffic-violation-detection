import { useCallback, useEffect, useState } from 'react';
import { Camera, Plus, Trash2, Play, Video } from 'lucide-react';
import { getCameras, createCamera, deleteCamera, startStreamProcessing } from '../../services/api';
import type { Camera as CameraType } from '../../types/violation';

export default function CameraManagement() {
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [formId, setFormId] = useState('');
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formLocation, setFormLocation] = useState('');

  const fetchCameras = useCallback(async () => {
    try {
      const data = await getCameras();
      setCameras(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load cameras');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createCamera({
        id: formId,
        name: formName,
        stream_url: formUrl,
        location: formLocation || undefined,
      });
      setShowForm(false);
      setFormId('');
      setFormName('');
      setFormUrl('');
      setFormLocation('');
      setSuccess('Camera added successfully');
      fetchCameras();
      setTimeout(() => setSuccess(null), 3000);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to create camera');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this camera?')) return;
    try {
      await deleteCamera(id);
      setSuccess('Camera deleted');
      fetchCameras();
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete camera');
    }
  };

  const handleStartProcessing = async (cameraId: string) => {
    try {
      const result = await startStreamProcessing(cameraId);
      setSuccess(`${result.message} (Task: ${result.task_id.slice(0, 8)}...)`);
      setTimeout(() => setSuccess(null), 5000);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start processing');
    }
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><p className="text-gray-500">Loading cameras...</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Cameras</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" /> Add Camera
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4"><p className="text-sm text-red-800">{error}</p></div>
      )}
      {success && (
        <div className="rounded-md bg-green-50 p-4"><p className="text-sm text-green-800">{success}</p></div>
      )}

      {/* Add camera form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-lg bg-white p-6 shadow">
          <h3 className="mb-4 text-lg font-medium text-gray-900">Add New Camera</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">Camera ID</label>
              <input
                type="text"
                required
                value={formId}
                onChange={(e) => setFormId(e.target.value)}
                placeholder="cam-01"
                className="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Main Street Camera"
                className="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700">Stream URL</label>
              <input
                type="text"
                required
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
                placeholder="rtsp://192.168.1.100:554/stream"
                className="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700">Location (optional)</label>
              <input
                type="text"
                value={formLocation}
                onChange={(e) => setFormLocation(e.target.value)}
                placeholder="Intersection of Main St & 1st Ave"
                className="mt-1 block w-full rounded-md border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="submit"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Add Camera
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Camera list */}
      {cameras.length === 0 ? (
        <div className="rounded-lg bg-white p-12 text-center shadow">
          <Camera className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-500">No cameras registered yet.</p>
          <p className="text-sm text-gray-400">Add a camera to start monitoring traffic.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cameras.map((cam) => (
            <div key={cam.id} className="rounded-lg bg-white p-6 shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`rounded-md p-2 ${cam.status === 'active' ? 'bg-green-100' : 'bg-gray-100'}`}>
                    <Video className={`h-5 w-5 ${cam.status === 'active' ? 'text-green-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">{cam.name}</h4>
                    <p className="text-xs text-gray-500">{cam.id}</p>
                  </div>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  cam.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  {cam.status}
                </span>
              </div>

              <div className="mt-3 space-y-1 text-sm text-gray-600">
                <p className="truncate" title={cam.stream_url}>
                  {cam.stream_url}
                </p>
                {cam.location && <p>{cam.location}</p>}
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleStartProcessing(cam.id)}
                  className="flex flex-1 items-center justify-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
                >
                  <Play className="h-3 w-3" /> Start
                </button>
                <button
                  onClick={() => handleDelete(cam.id)}
                  className="flex items-center justify-center gap-1 rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
