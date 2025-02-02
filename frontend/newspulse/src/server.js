import express from "express";
import mysql from "mysql2";
import cors from "cors";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

const db = mysql.createConnection({
  host: process.env.DB_HOST || "localhost",
  user: process.env.DB_USER || "root",
  password: process.env.DB_PASSWORD || "adhesh",
  database: process.env.DB_NAME || "news_db",
});

db.connect((err) => {
  if (err) {
    console.error("Database connection failed:", err);
  } else {
    console.log("Connected to MySQL database!");
  }
});

app.get("/api/news", (req, res) => {
  const { sentiment, domain, search } = req.query;
  
  let query = "SELECT * FROM news_analytics_results WHERE 1=1";
  const values = [];

  if (sentiment && sentiment !== "all") {
    query += " AND sentiment = ?";
    values.push(sentiment);
  }
  if (domain && domain !== "all") {
    query += " AND classification = ?";
    values.push(domain);
  }
  if (search) {
    query += " AND (title LIKE ? OR summary LIKE ?)";
    values.push(`%${search}%`, `%${search}%`);
  }

  console.log("Executing query:", query);
  console.log("With values:", values);

  db.query(query, values, (err, results) => {
    if (err) {
      console.error("Error fetching news:", err);
      return res.status(500).json({ error: "Database error" });
    }
    res.json(results);
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});