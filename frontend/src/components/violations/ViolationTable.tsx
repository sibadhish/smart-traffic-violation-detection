import { format } from 'date-fns';
import type { Violation } from '../../types/violation';

interface ViolationTableProps {
  violations: Violation[];
  onSelect: (violation: Violation) => void;
}

const statusColors: Record<string, string> = {
  detected: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  rejected: 'bg-gray-100 text-gray-800',
  evidence_generated: 'bg-green-100 text-green-800',
  sent_to_authority: 'bg-purple-100 text-purple-800',
};

const typeLabels: Record<string, string> = {
  helmet_violation: 'No Helmet',
  signal_jump: 'Signal Jump',
  wrong_way: 'Wrong Way',
  speeding: 'Speeding',
  no_seatbelt: 'No Seatbelt',
  illegal_parking: 'Illegal Parking',
};

export default function ViolationTable({
  violations,
  onSelect,
}: ViolationTableProps) {
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Camera
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Plate
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Confidence
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Detected
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {violations.map((v) => (
            <tr
              key={v.id}
              onClick={() => onSelect(v)}
              className="cursor-pointer hover:bg-gray-50"
            >
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                {typeLabels[v.violation_type] ?? v.violation_type}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {v.camera_id}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-mono text-gray-900">
                {v.license_plate ?? '—'}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {(v.confidence * 100).toFixed(1)}%
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                <span
                  className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${statusColors[v.status] ?? ''}`}
                >
                  {v.status.replace(/_/g, ' ')}
                </span>
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {format(new Date(v.detected_at), 'MMM d, yyyy HH:mm')}
              </td>
            </tr>
          ))}
          {violations.length === 0 && (
            <tr>
              <td
                colSpan={6}
                className="px-6 py-12 text-center text-sm text-gray-500"
              >
                No violations found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
