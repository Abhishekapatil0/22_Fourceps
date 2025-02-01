import express from "express";
import mysql from "mysql";
import cors from "cors";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// ✅ MySQL Database Connection
const db = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "Aadi@157",
  database: "newpulse",
});

db.connect((err) => {
  if (err) {
    console.error("Database connection failed:", err);
  } else {
    console.log("Connected to MySQL database!");
  }
});

// ✅ API Route to Fetch News with Filters
app.get("/api/news", (req, res) => {
  const { sentiment, domain, search } = req.query;
  console.log(sentiment, domain, search);
  let query = "SELECT * FROM news WHERE 1=1";
  const values = [];

  if (sentiment && sentiment !== "all") {
    query += " AND sentiment = ?";
    values.push(sentiment);
  }
  if (domain && domain !== "all") {
    query += " AND domain = ?";
    values.push(domain);
  }
  if (search) {
    query += " AND (title LIKE ? OR content LIKE ?)";
    values.push(`%${search}%`, `%${search}%`);
  }

  db.query(query, values, (err, results) => {
    if (err) {
      console.error("Error fetching news:", err);
      return res.status(500).json({ error: "Database error" });
    }
    res.json(results);
  });
});

// ✅ Start the Server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
