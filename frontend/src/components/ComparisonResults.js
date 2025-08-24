import React from 'react';
import ArticleCard from './ArticleCard';

const ComparisonResults = ({ query, comparisonResults, loading }) => {
  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Сравнительный поиск</p>
      </div>
    );
  }

  if (!comparisonResults) {
    return null;
  }

  const { ml, bm25 } = comparisonResults;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          Сравнение результатов для "{query}"
        </h2>
        <span className="text-gray-600">
          ML: {ml?.length || 0} | BM25: {bm25?.length || 0} статей
        </span>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ML Results */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-blue-200">
          <div className="flex items-center mb-4">
            <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
            <h3 className="text-lg font-semibold text-blue-700">ML Ранжирование</h3>
          </div>
          <div className="space-y-4">
            {ml && ml.length > 0 ? (
              ml.map((result, index) => (
                <ArticleCard
                  key={`ml-${result.id || index}`}
                  article={result}
                  index={index}
                  variant="ml"
                  showFullStats={false}
                />
              ))
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Нет результатов</p>
              </div>
            )}
          </div>
        </div>
        
        {/* BM25 Results */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-green-200">
          <div className="flex items-center mb-4">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <h3 className="text-lg font-semibold text-green-700">BM25 Поиск</h3>
          </div>
          <div className="space-y-4">
            {bm25 && bm25.length > 0 ? (
              bm25.map((result, index) => (
                <ArticleCard
                  key={`bm25-${result.id || index}`}
                  article={result}
                  index={index}
                  variant="bm25"
                  showFullStats={false}
                />
              ))
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">Нет результатов</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComparisonResults;
