import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useViolations } from '../../hooks/useViolations';
import ViolationTable from './ViolationTable';

export default function ViolationList() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<{
    violation_type?: string;
    status?: string;
  }>({});
  const [plateSearch, setPlateSearch] = useState('');
  const { violations, loading, error } = useViolations(filters);

  // Client-side plate filter (the API also supports server-side in the future)
  const filtered = plateSearch
    ? violations.filter((v) =>
        v.license_plate?.toLowerCase().includes(plateSearch.toLowerCase())
      )
    : violations;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Violations</h2>
        <div className="flex flex-wrap items-center gap-3">
          {/* Plate search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search plate..."
              value={plateSearch}
              onChange={(e) => setPlateSearch(e.target.value)}
              className="rounded-md border-gray-300 pl-9 text-sm"
            />
          </div>

          {/* Type filter */}
          <select
            className="rounded-md border-gray-300 text-sm"
            value={filters.violation_type ?? ''}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                violation_type: e.target.value || undefined,
              }))
            }
          >
            <option value="">All Types</option>
            <option value="helmet_violation">No Helmet</option>
            <option value="signal_jump">Signal Jump</option>
            <option value="wrong_way">Wrong Way</option>
            <option value="speeding">Speeding</option>
          </select>

          {/* Status filter */}
          <select
            className="rounded-md border-gray-300 text-sm"
            value={filters.status ?? ''}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                status: e.target.value || undefined,
              }))
            }
          >
            <option value="">All Statuses</option>
            <option value="detected">Detected</option>
            <option value="confirmed">Confirmed</option>
            <option value="rejected">Rejected</option>
            <option value="evidence_generated">Evidence Generated</option>
          </select>
        </div>
      </div>

      {loading && <p className="text-gray-500">Loading...</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {!loading && (
        <ViolationTable
          violations={filtered}
          onSelect={(v) => navigate(`/violations/${v.id}`)}
        />
      )}
    </div>
  );
}
