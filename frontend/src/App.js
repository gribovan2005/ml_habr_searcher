import React from 'react';
import { 
  Header, 
  StatsGrid, 
  SearchForm, 
  ErrorAlert, 
  SearchResults, 
  ComparisonResults, 
  EmptyState 
} from './components';
import { useStats } from './hooks/useStats';
import { useSearch } from './hooks/useSearch';

function App() {
  const { stats, loading: statsLoading, error: statsError } = useStats();
  const { 
    query, 
    results, 
    comparisonResults, 
    loading: searchLoading, 
    error: searchError,
    search,
    hasResults
  } = useSearch();

  const handleSearch = (searchQuery, compareMode) => {
    search(searchQuery, compareMode);
  };

  const handleErrorClose = () => {
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <Header />

        <StatsGrid stats={stats} loading={statsLoading} />

        <SearchForm onSearch={handleSearch} loading={searchLoading} />

        <ErrorAlert 
          error={searchError || statsError} 
          onClose={handleErrorClose} 
        />

        {comparisonResults && (
          <ComparisonResults
            query={query}
            comparisonResults={comparisonResults}
            loading={searchLoading}
          />
        )}

        {results.length > 0 && !comparisonResults && (
          <SearchResults
            query={query}
            results={results}
            loading={searchLoading}
          />
        )}

        {!hasResults && !searchLoading && !searchError && (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

export default App;
