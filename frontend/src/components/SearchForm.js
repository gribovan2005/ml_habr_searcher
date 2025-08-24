import React, { useState } from 'react';

const SearchForm = ({ onSearch, loading }) => {
  const [query, setQuery] = useState('');
  const [compareMode, setCompareMode] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query, compareMode);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-8 mb-8 border border-gray-200">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <svg 
            className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path 
              fillRule="evenodd" 
              d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" 
              clipRule="evenodd" 
            />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Введите запрос для поиска статей..."
            className="w-full pl-12 pr-4 py-4 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
            disabled={loading}
          />
        </div>
        
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="compare-mode"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
            disabled={loading}
          />
          <label htmlFor="compare-mode" className="text-sm font-medium text-gray-700">
            Сравнить с базовым поиском (BM25)
          </label>
        </div>
        
        <button 
          type="submit" 
          disabled={loading || !query.trim()}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-4 px-6 rounded-lg transition-all duration-200 flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Поиск...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path 
                  fillRule="evenodd" 
                  d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" 
                  clipRule="evenodd" 
                />
              </svg>
              <span>Найти статьи</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default SearchForm;
