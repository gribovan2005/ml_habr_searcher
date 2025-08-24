import React from 'react';
import ArticleCard from './ArticleCard';

const SearchResults = ({ query, results, loading }) => {
  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Поиск статей</p>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          Результаты поиска для "{query}"
        </h2>
        <span className="text-gray-600">
          Найдено: {results.length} статей
        </span>
      </div>
      
      <div className="grid gap-6">
        {results.map((result, index) => (
          <ArticleCard
            key={result.id || index}
            article={result}
            index={index}
            variant="default"
            showFullStats={true}
          />
        ))}
      </div>
    </div>
  );
};

export default SearchResults;
