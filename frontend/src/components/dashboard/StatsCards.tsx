import { AlertTriangle, Camera, CheckCircle, TrendingUp } from 'lucide-react';
import type { ViolationStats } from '../../types/violation';

interface StatsCardsProps {
  stats: ViolationStats;
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: 'Total Violations',
      value: stats.total_violations,
      icon: AlertTriangle,
      color: 'text-red-600 bg-red-100',
    },
    {
      title: 'Today',
      value: stats.today_count,
      icon: TrendingUp,
      color: 'text-blue-600 bg-blue-100',
    },
    {
      title: 'This Week',
      value: stats.this_week_count,
      icon: CheckCircle,
      color: 'text-green-600 bg-green-100',
    },
    {
      title: 'Active Cameras',
      value: Object.keys(stats.by_camera).length,
      icon: Camera,
      color: 'text-purple-600 bg-purple-100',
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.title} className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center">
            <div className={`rounded-md p-3 ${card.color}`}>
              <card.icon className="h-6 w-6" />
            </div>
            <div className="ml-5">
              <p className="text-sm font-medium text-gray-500">{card.title}</p>
              <p className="text-2xl font-semibold text-gray-900">
                {card.value.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
