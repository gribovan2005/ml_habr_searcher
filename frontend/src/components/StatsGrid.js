import React from 'react';

const StatCard = ({ icon, title, value, color = "blue" }) => {
  const colorClasses = {
    blue: "text-blue-500",
    green: "text-green-500", 
    purple: "text-purple-500",
    indigo: "text-indigo-500"
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center">
        <svg className={`w-8 h-8 ${colorClasses[color]} mr-3`} fill="currentColor" viewBox="0 0 20 20">
          {icon}
        </svg>
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
};

const StatsGrid = ({ stats, loading }) => {
  if (loading || !stats) {
    return null;
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 KB';
    const mb = bytes / (1024 * 1024);
    return mb > 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <StatCard
        icon={
          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
        }
        title="Всего статей"
        value={stats.total_articles?.toLocaleString() || '0'}
        color="blue"
      />
      
      <StatCard
        icon={
          <>
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
            <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
          </>
        }
        title="Общие просмотры"
        value={stats.total_views?.toLocaleString() || '0'}
        color="green"
      />
      
      <StatCard
        icon={
          <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        }
        title="Средние просмотры"
        value={Math.round(stats.avg_views || 0).toLocaleString()}
        color="purple"
      />
      
      <StatCard
        icon={
          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
        }
        title="Размер индекса"
        value={formatSize(stats.es_index_size)}
        color="indigo"
      />
    </div>
  );
};

export default StatsGrid;
