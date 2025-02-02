import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const categories = [
  "POLITICS",
  "WELLNESS",
  "ENTERTAINMENT",
  "TRAVEL",
  "BUSINESS",
  "SPORTS",
  "THE WORLDPOST",
  "CRIME",
  "IMPACT",
  "WORLD NEWS",
  "MEDIA",
  "RELIGION",
  "SCIENCE",
  "TECH"
];

const sentiments = ["positive", "negative"];

const HomePage = () => {
  const [allNews, setAllNews] = useState([]);
  const [filteredNews, setFilteredNews] = useState([]);
  const [sentiment, setSentiment] = useState("all");
  const [domain, setDomain] = useState("all");
  const [search, setSearch] = useState("");

  const formatDomain = (domain) => {
    return domain
      .toLowerCase()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const response = await fetch("http://localhost:5000/api/news");
        const data = await response.json();
        setAllNews(data);
      } catch (error) {
        console.error("Error fetching news:", error);
      }
    };
    fetchNews();
  }, []);

  useEffect(() => {
    const applyFilters = () => {
      let filtered = allNews.filter(article => {
        const matchesSearch = article.title.toLowerCase().includes(search.toLowerCase()) || 
                             article.summary.toLowerCase().includes(search.toLowerCase());
        const matchesSentiment = sentiment === "all" || article.sentiment === sentiment;
        const matchesDomain = domain === "all" || article.classification === domain;
        
        return matchesSearch && matchesSentiment && matchesDomain;
      });

      filtered = filtered
        .map(article => ({
          ...article,
          score: (article.priority * 0.8) + (Math.random() * 0.2)
        }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 50);

      setFilteredNews(filtered);
    };

    applyFilters();
  }, [allNews, search, sentiment, domain]);

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <div className="min-h-screen bg-gray-50 font-['Helvetica_Neue',_sans-serif] min-w-[100vw]">
      <nav className="bg-[#3a252a] shadow-lg p-4">
        <div className="container mx-auto flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          <img
            src="/logo.jpeg"
            alt="NewsPulse Logo"
            className="h-12"
          />

          <input
            type="text"
            placeholder="Search news..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full md:w-64 px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
          />

          <div className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-4">
            <select
              value={sentiment}
              onChange={(e) => setSentiment(e.target.value)}
              className="px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="all">All Sentiments</option>
              {sentiments.map((sent) => (
                <option key={sent} value={sent}>
                  {sent.charAt(0).toUpperCase() + sent.slice(1)}
                </option>
              ))}
            </select>

            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="px-4 py-2 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-400"
            >
              <option value="all">All Categories</option>
              {categories.map((domain) => (
                <option key={domain} value={domain}>
                  {formatDomain(domain)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </nav>

      <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4 grid-flow-dense auto-rows-[minmax(200px,auto)]">
        <AnimatePresence>
          {filteredNews.length > 0 ? (
            filteredNews.map((article, index) => {
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
                <motion.div
                  key={article.id}
                  initial="hidden"
                  animate="visible"
                  variants={itemVariants}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className={`bg-white shadow-lg p-6 rounded-lg border-l-4 border-[#3a252a] transition-transform duration-200 h-full overflow-hidden ${colSpan} ${rowSpan} cursor-pointer`}
                  whileHover={{ 
                    scale: 1.02,
                    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
                    transition: { duration: 0.2 }
                  }}
                  onClick={() => window.open(article.url, '_blank')}
                >
                  <h2 className="text-xl font-bold text-gray-800 line-clamp-2 mb-3">
                    {article.title}
                  </h2>
                  <p className="text-gray-700 line-clamp-5 mb-4">
                    {article.summary}
                  </p>
                  <div className="mt-auto">
                    <span className="inline-block bg-[#d2b8be] text-gray-700 px-3 py-1 rounded-full text-sm font-medium">
                      {formatDomain(article.classification)}
                    </span>
                    <span
                      className={`ml-2 text-sm font-semibold ${
                        article.sentiment === "positive"
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      ({article.sentiment})
                    </span>
                  </div>
                </motion.div>
              );
            })
          ) : (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="text-center text-gray-600 col-span-3 py-8"
            >
              No news articles found. Try adjusting your filters.
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default HomePage;