'use client';

import { useState } from 'react';

export default function Home() {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Search query:', query);
  };

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8 text-center">
        AI Research Assistant
      </h1>
      
      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your research query..."
            className="flex-1 p-3 border border-gray-300 rounded-lg"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-blue-500 text-white rounded-lg"
          >
            Search
          </button>
        </div>
      </form>
    </main>
  );
}
