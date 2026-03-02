import React from "react";

export const DashboardSkeleton = () => (
  <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6 animate-pulse">
    <div className="max-w-7xl mx-auto">
      <div className="h-12 bg-slate-700 rounded mb-8 w-1/3"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-slate-800 border border-slate-700 rounded-lg p-6 h-32"></div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="bg-slate-800 border border-slate-700 rounded-lg h-80"></div>
        ))}
      </div>
    </div>
  </div>
);

export const BlocksSkeleton = () => (
  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 animate-pulse">
    <div className="h-8 bg-slate-700 rounded mb-4 w-1/4"></div>
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-12 bg-slate-700 rounded"></div>
      ))}
    </div>
  </div>
);

export const TransactionsSkeleton = () => (
  <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 animate-pulse">
    <div className="h-8 bg-slate-700 rounded mb-4 w-1/4"></div>
    <div className="space-y-2">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="h-10 bg-slate-700 rounded"></div>
      ))}
    </div>
  </div>
);
