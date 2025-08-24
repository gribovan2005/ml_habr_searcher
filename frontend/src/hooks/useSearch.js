import { useState } from 'react';
import ApiService from '../services/api';

export const useSearch = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [comparisonResults, setComparisonResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = async (searchQuery, compareMode = false) => {
    if (!searchQuery?.trim()) return;

    try {
      setLoading(true);
      setError(null);
      setQuery(searchQuery);

      if (compareMode) {
        const data = await ApiService.compareSearch(searchQuery, 10);
        setComparisonResults(data);
        setResults([]);
      } else {
        const data = await ApiService.search(searchQuery, 10, false);
        setResults(data.results);
        setComparisonResults(null);
      }
    } catch (err) {
      setError('Ошибка при выполнении поиска');
      setResults([]);
      setComparisonResults(null);
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setResults([]);
    setComparisonResults(null);
    setQuery('');
    setError(null);
  };

  return {
    query,
    results,
    comparisonResults,
    loading,
    error,
    search,
    clearResults,
    hasResults: results.length > 0 || comparisonResults !== null
  };
};
