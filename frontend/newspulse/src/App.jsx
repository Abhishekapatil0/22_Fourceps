import React, { useState, useEffect } from "react";

const HomePage = () => {
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState("all");
  const [domain, setDomain] = useState("all");

  useEffect(() => {
    fetchNews();
  }, [sentiment, domain]);

  const fetchNews = async () => {
    try {
      const response = await fetch(
        `/api/news?sentiment=${sentiment}&domain=${domain}`
      );
      const data = await response.json();
      setNews(data);
    } catch (error) {
      console.error("Error fetching news:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navbar with Filters */}
      <nav className="bg-white shadow-md p-4 flex justify-between">
        <h1 className="text-xl font-bold">NewsPulse</h1>
        <div className="flex gap-4">
          <select
            className="border p-2 rounded"
            value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
          >
            <option value="all">All Sentiments</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="neutral">Neutral</option>
          </select>

          <select
            className="border p-2 rounded"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          >
            <option value="all">All Domains</option>
            <option value="sports">Sports</option>
            <option value="politics">Politics</option>
            <option value="technology">Technology</option>
          </select>
        </div>
      </nav>

      {/* News List */}
      <div className="p-4">
        {news.length > 0 ? (
          news.map((article) => (
            <div key={article.id} className="bg-white shadow-lg p-4 mb-4 rounded">
              <h2 className="text-lg font-bold">{article.title}</h2>
              <p className="text-gray-600">{article.summary}</p>
              <span className="text-sm text-blue-500">{article.domain}</span>
              <span className="ml-2 text-sm text-gray-500">({article.sentiment})</span>
            </div>
          ))
        ) : (
          <p className="text-center text-gray-500">No news available.</p>
        )}
      </div>
    </div>
  );
};

export default HomePage;
