import React, { useState, useEffect } from "react";

const HomePage = () => {
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState("all");
  const [domain, setDomain] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchNews();
  }, [sentiment, domain, search]);

  const fetchNews = async () => {
    try {
      const response = await fetch(
        `http://localhost:5000/api/news?sentiment=${sentiment}&domain=${domain}&search=${search}`
      );
      const data = await response.json();
      console.log("Fetched news:", data);
      setNews(data);
    } catch (error) {
      console.error("Error fetching news:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-green-600 shadow-lg p-4">
        <div className="container mx-auto flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          {/* Logo */}
          <h1 className="text-2xl font-bold text-white">NewsPulse</h1>

          {/* Search Bar */}
          <input
            type="text"
            placeholder="Search news..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full md:w-64 px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
          />

          {/* Filters */}
          <div className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-4">
            {/* Sentiment Filter */}
            <select
              value={sentiment}
              onChange={(e) => setSentiment(e.target.value)}
              className="px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="all">All Sentiments</option>
              <option value="positive">Positive</option>
              <option value="negative">Negative</option>
              <option value="neutral">Neutral</option>
            </select>

            {/* Domain Filter */}
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="all">All Domains</option>
              <option value="sports">Sports</option>
              <option value="politics">Politics</option>
              <option value="technology">Technology</option>
            </select>
          </div>
        </div>
      </nav>

      {/* News Grid */}
      <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4 grid-flow-dense auto-rows-[minmax(200px,auto)]">
        {news.length > 0 ? (
          news.map((article, index) => {
            // Determine grid spans based on index
            let colSpan = "md:col-span-1";
            let rowSpan = "md:row-span-1";

            if (index % 6 === 0) {
              colSpan = "md:col-span-2";
              rowSpan = "md:row-span-2";
            } else if (index % 3 === 0) {
              colSpan = "md:col-span-2";
            } else if (index % 2 === 0) {
              rowSpan = "md:row-span-2";
            }

            return (
              <div
                key={article.id}
                className={`bg-white shadow-lg p-6 rounded-lg border-l-4 border-green-600 transition-transform duration-200 hover:scale-[1.01] h-full overflow-hidden ${colSpan} ${rowSpan}`}
              >
                <h2 className="text-xl font-bold text-green-800 line-clamp-2 mb-3">
                  {article.title}
                </h2>
                <p className="text-gray-700 line-clamp-5 mb-4">
                  {article.summary}
                </p>
                <div className="mt-auto">
                  <span className="inline-block bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-medium">
                    {article.domain}
                  </span>
                  <span
                    className={`ml-2 text-sm font-semibold ${
                      article.sentiment === "positive"
                        ? "text-green-600"
                        : article.sentiment === "negative"
                        ? "text-red-600"
                        : "text-gray-600"
                    }`}
                  >
                    ({article.sentiment})
                  </span>
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-center text-gray-600 col-span-3 py-8">
            No news articles found. Try adjusting your filters.
          </p>
        )}
      </div>
    </div>
  );
};

export default HomePage;