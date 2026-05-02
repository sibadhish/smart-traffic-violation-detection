import { useCallback, useEffect, useState } from 'react';
import type { Violation, ViolationStats } from '../types/violation';
import { getViolations, getViolationStats } from '../services/api';

export function useViolations(params?: {
  camera_id?: string;
  violation_type?: string;
  status?: string;
}) {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [stats, setStats] = useState<ViolationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [v, s] = await Promise.all([
        getViolations(params),
        getViolationStats(),
      ]);
      setViolations(v);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch violations');
    } finally {
      setLoading(false);
    }
  }, [params?.camera_id, params?.violation_type, params?.status]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { violations, stats, loading, error, refetch: fetch };
}
