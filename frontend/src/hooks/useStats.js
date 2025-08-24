import { useState, useEffect } from 'react';
import ApiService from '../services/api';

export const useStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ApiService.getStats();
      setStats(data);
    } catch (err) {
      setError('Не удалось загрузить статистику');
      console.error('Stats loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return {
    stats,
    loading,
    error,
    refetch: loadStats
  };
};
