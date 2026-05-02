import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Play, Shield, AlertTriangle } from 'lucide-react';
import { format } from 'date-fns';
import { getViolation, updateViolation } from '../../services/api';
import type { Violation } from '../../types/violation';

const typeLabels: Record<string, string> = {
  helmet_violation: 'No Helmet',
  signal_jump: 'Signal Jump',
  wrong_way: 'Wrong Way',
  speeding: 'Speeding',
  no_seatbelt: 'No Seatbelt',
  illegal_parking: 'Illegal Parking',
};

const statusColors: Record<string, string> = {
  detected: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  rejected: 'bg-gray-100 text-gray-800',
  evidence_generated: 'bg-green-100 text-green-800',
  sent_to_authority: 'bg-purple-100 text-purple-800',
};

export default function ViolationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [violation, setViolation] = useState<Violation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getViolation(id)
      .then(setViolation)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleStatusUpdate = async (newStatus: string) => {
    if (!id || !violation) return;
    try {
      const updated = await updateViolation(id, { status: newStatus });
      setViolation(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><p className="text-gray-500">Loading...</p></div>;
  }

  if (error || !violation) {
    return (
      <div className="space-y-4">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="rounded-md bg-red-50 p-4"><p className="text-sm text-red-800">{error || 'Violation not found'}</p></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <h2 className="text-2xl font-bold text-gray-900">
            {typeLabels[violation.violation_type] || violation.violation_type}
          </h2>
          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusColors[violation.status] || ''}`}>
            {violation.status.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Video / Thumbnail */}
        <div className="lg:col-span-2">
          <div className="overflow-hidden rounded-lg bg-black">
            {violation.clip_url ? (
              <video
                controls
                className="w-full"
                poster={violation.thumbnail_url || undefined}
              >
                <source src={violation.clip_url} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            ) : violation.thumbnail_url ? (
              <img
                src={violation.thumbnail_url}
                alt="Violation thumbnail"
                className="w-full"
              />
            ) : (
              <div className="flex h-64 items-center justify-center text-gray-400">
                <Play className="h-12 w-12" />
              </div>
            )}
          </div>
        </div>

        {/* Details panel */}
        <div className="space-y-4">
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="mb-4 text-lg font-medium text-gray-900">Details</h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Violation Type</dt>
                <dd className="mt-1 flex items-center gap-2 text-sm text-gray-900">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  {typeLabels[violation.violation_type] || violation.violation_type}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Camera</dt>
                <dd className="mt-1 text-sm text-gray-900">{violation.camera_id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">License Plate</dt>
                <dd className="mt-1 font-mono text-sm text-gray-900">
                  {violation.license_plate || 'Not detected'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Confidence</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {(violation.confidence * 100).toFixed(1)}%
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Detected At</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {format(new Date(violation.detected_at), 'MMM d, yyyy HH:mm:ss')}
                </dd>
              </div>
              {violation.location && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Location</dt>
                  <dd className="mt-1 text-sm text-gray-900">{violation.location}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Actions */}
          <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="mb-4 text-lg font-medium text-gray-900">Actions</h3>
            <div className="space-y-2">
              {violation.status === 'detected' && (
                <>
                  <button
                    onClick={() => handleStatusUpdate('confirmed')}
                    className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    <Shield className="h-4 w-4" /> Confirm Violation
                  </button>
                  <button
                    onClick={() => handleStatusUpdate('rejected')}
                    className="flex w-full items-center justify-center gap-2 rounded-md bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
                  >
                    Reject
                  </button>
                </>
              )}
              {violation.evidence_package_url && (
                <a
                  href={violation.evidence_package_url}
                  download
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                >
                  <Download className="h-4 w-4" /> Download Evidence
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
