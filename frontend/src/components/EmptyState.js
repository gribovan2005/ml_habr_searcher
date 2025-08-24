import React from 'react';

const EmptyState = () => {
  return (
    <div className="text-center py-16">
      <div className="max-w-md mx-auto">
        <svg 
          className="w-16 h-16 text-gray-400 mx-auto mb-4" 
          fill="currentColor" 
          viewBox="0 0 20 20"
        >
          <path 
            fillRule="evenodd" 
            d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" 
            clipRule="evenodd" 
          />
        </svg>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Начните поиск
        </h3>
        <p className="text-gray-600">
          Введите запрос для поиска статей на Habr.com. Система использует BM25 для поиска и машинное обучение для ранжирования результатов.
        </p>
      </div>
    </div>
  );
};

export default EmptyState;
