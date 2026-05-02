import { useViolations } from '../../hooks/useViolations';
import StatsCards from './StatsCards';
import ViolationChart from './ViolationChart';

export default function Dashboard() {
  const { stats, loading, error } = useViolations();

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500">Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-800">Error: {error}</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-8">
      <StatsCards stats={stats} />
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ViolationChart data={stats.by_type} title="Violations by Type" />
        <ViolationChart data={stats.by_camera} title="Violations by Camera" />
      </div>
    </div>
  );
}
