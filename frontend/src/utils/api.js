// API Configuration
const API_BASE_URL = "https://data-analyst-agent-kw5l.onrender.com";

// Fetch query history from the API
export const fetchHistory = async (limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    const data = await response.json();
    return data.history || [];
  } catch (error) {
    console.error("Error fetching history:", error);
    throw error;
  }
};

// Submit a natural language question to the API
export const submitQuestion = async (
  question,
  storeResults = true,
  requireApproval = true,
  approved = false
) => {
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        store_results: storeResults,
        require_approval: requireApproval,
        approved,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error submitting question:", error);
    throw error;
  }
};

// Submit a direct SQL query to the API
export const submitDirectSql = async (sql, storeResults = false) => {
  try {
    const response = await fetch(`${API_BASE_URL}/direct-sql`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sql,
        store_results: storeResults,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error submitting direct SQL:", error);
    throw error;
  }
};

// Submit a modified SQL query with original question
export const submitModifiedSql = async (question, sql, storeResults = true) => {
  try {
    const response = await fetch(`${API_BASE_URL}/store-question-sql-pair`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        sql,
        store_results: storeResults,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error submitting modified SQL:", error);
    throw error;
  }
};

// Get similar queries for a question
export const getSimilarQueries = async (question, topK = 3) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/similar-queries/${encodeURIComponent(
        question
      )}?top_k=${topK}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const data = await response.json();
    return data.similar_queries || [];
  } catch (error) {
    console.error("Error fetching similar queries:", error);
    throw error;
  }
};

// Generate SQL without executing
export const generateSql = async (question) => {
  try {
    const response = await fetch(`${API_BASE_URL}/generate-sql`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error generating SQL:", error);
    throw error;
  }
};

// Get data analysis from the API
export const analyzeData = async (data) => {
  try {
    console.log("Analyzing data:", data);
    const response = await fetch(`${API_BASE_URL}/analyze-data`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error analyzing data:", error);
    throw error;
  }
};

// Get visualization suggestions from the API
export const getVisualizationSuggestions = async (data) => {
  try {
    const response = await fetch(`${API_BASE_URL}/suggest-visualizations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error getting visualization suggestions:", error);
    throw error;
  }
};
