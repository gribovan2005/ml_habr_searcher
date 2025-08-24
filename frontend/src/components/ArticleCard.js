import React from 'react';

const ArticleCard = ({ 
  article, 
  index, 
  variant = 'default',
  showFullStats = true 
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'ml':
        return {
          border: 'border-blue-200',
          badge: 'bg-blue-50 text-blue-800',
          label: 'ML'
        };
      case 'bm25':
        return {
          border: 'border-green-200',
          badge: 'bg-green-50 text-green-800',
          label: 'BM25'
        };
      default:
        return {
          border: 'border-gray-200',
          badge: 'bg-blue-100 text-blue-800',
          label: null
        };
    }
  };

  const variantClasses = getVariantClasses();

  return (
    <div className={`bg-white rounded-lg shadow-md border ${variantClasses.border} hover:shadow-lg transition-shadow duration-200`}>
      <div className={showFullStats ? 'p-6' : 'p-4'}>
        <div className="flex items-start justify-between mb-3">
          <h3 className={`font-semibold text-gray-900 hover:text-blue-600 transition-colors ${showFullStats ? 'text-xl' : 'text-lg'}`}>
            <a 
              href={article.url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="hover:underline"
            >
              {article.title}
            </a>
          </h3>
          <span className={`${variantClasses.badge} text-xs font-medium px-2.5 py-0.5 rounded-full`}>
            {variantClasses.label ? `${variantClasses.label} #${index + 1}` : `#${index + 1}`}
          </span>
        </div>
        
        <div className={`flex items-center space-x-6 text-sm text-gray-600 mb-4 ${!showFullStats && 'text-xs space-x-4'}`}>
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
            </svg>
            <span>{article.views?.toLocaleString() || 0}</span>
          </div>
          <div className="flex items-center space-x-1">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
            </svg>
            <span>{article.comments_count || 0}</span>
          </div>
          {variant !== 'comparison' && (
            <div className="flex items-center space-x-1">
              <span className={variant === 'ml' ? 'text-blue-600' : variant === 'bm25' ? 'text-green-600' : 'text-purple-600'}>
                {variant === 'ml' ? 'ML' : variant === 'bm25' ? 'BM25' : 'Score'}: {(article.score || article.ml_score || 0).toFixed(2)}
              </span>
            </div>
          )}
        </div>
        
        {showFullStats && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-500 mb-1">ML Score</p>
              <p className="text-lg font-semibold text-green-600">
                {(article.ml_score || 0).toFixed(4)}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs font-medium text-gray-500 mb-1">BM25 Score</p>
              <p className="text-lg font-semibold text-blue-600">
                {(article.bm25_score || 0).toFixed(4)}
              </p>
            </div>
          </div>
        )}
        
        {article.tags && article.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {(showFullStats ? article.tags : article.tags.slice(0, 3)).map((tag, tagIndex) => (
              <span key={tagIndex} className={`text-xs font-medium px-2.5 py-1 rounded-full ${showFullStats ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-700'}`}>
                {tag}
              </span>
            ))}
            {!showFullStats && article.tags.length > 3 && (
              <span className="text-xs text-gray-500">
                +{article.tags.length - 3}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ArticleCard;
