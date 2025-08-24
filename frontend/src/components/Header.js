import React from 'react';

const Header = () => {
  return (
    <div className="text-center mb-8">
      <div className="flex items-center justify-center mb-4">
        <svg 
          className="w-12 h-12 text-blue-600 mr-3" 
          fill="currentColor" 
          viewBox="0 0 20 20"
        >
          <path 
            fillRule="evenodd" 
            d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" 
            clipRule="evenodd" 
          />
        </svg>
        <h1 className="text-4xl font-bold text-gray-900">
          Habr Search Engine
        </h1>
      </div>
      <p className="text-lg text-gray-600 max-w-2xl mx-auto">
         система поиска статей с использованием BM25 и машинного обучения
      </p>
    </div>
  );
};

export default Header;
