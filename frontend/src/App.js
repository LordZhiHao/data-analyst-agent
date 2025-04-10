import React, { useState, useEffect } from "react";
import { Container, Spinner } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "highlight.js/styles/github.css";
import "./App.css";

// Import components
import Header from "./components/Header";
import QueryInput from "./components/QueryInput";
import SQLApproval from "./components/SQLApproval";
import ResultsDisplay from "./components/ResultsDisplay";
import QueryHistory from "./components/QueryHistory";
import SqlModal from "./components/SqlModal";

// Import API functions
import {
  fetchHistory,
  submitQuestion,
  submitDirectSql,
  submitModifiedSql,
} from "./utils/api";

function App() {
  // State variables
  const [question, setQuestion] = useState("");
  const [directSql, setDirectSql] = useState("");
  const [storeResults, setStoreResults] = useState(true);
  const [requireApproval, setRequireApproval] = useState(true);
  const [loading, setLoading] = useState(false);
  const [pendingQuery, setPendingQuery] = useState(null);
  const [editableSql, setEditableSql] = useState("");
  const [showApproval, setShowApproval] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [activeInputMode, setActiveInputMode] = useState("nl");
  const [history, setHistory] = useState([]);
  const [sqlModalShow, setSqlModalShow] = useState(false);
  const [sqlModalContent, setSqlModalContent] = useState("");

  // Fetch query history on component mount
  useEffect(() => {
    loadQueryHistory();
  }, []);

  // Load query history
  const loadQueryHistory = async () => {
    try {
      const historyData = await fetchHistory();
      setHistory(historyData);
    } catch (error) {
      console.error("Error loading history:", error);
    }
  };

  // Handle natural language question submission
  const handleSubmit = async (approved = false) => {
    const currentQuestion = approved && pendingQuery ? pendingQuery : question;
    if (!currentQuestion.trim()) return;

    setLoading(true);
    setShowResults(false);
    setShowApproval(false);

    try {
      const data = await submitQuestion(
        currentQuestion,
        storeResults,
        requireApproval && !approved,
        approved
      );

      // Check if approval is required
      if (data.requires_approval && data.awaiting_approval) {
        setPendingQuery(data.question);
        setEditableSql(data.sql);
        setShowApproval(true);
        setLoading(false);
        return;
      }

      // Process results
      setQueryResult(data);
      setShowResults(true);
      setLoading(false);

      // Refresh history if successful
      if (data.was_successful !== false) {
        loadQueryHistory();
      }

      // Clear pending query
      setPendingQuery(null);
    } catch (error) {
      console.error("Error submitting query:", error);
      setLoading(false);
      setPendingQuery(null);
      alert(`Error: ${error.message}`);
    }
  };

  // Handle direct SQL query submission
  const handleDirectSqlSubmit = async () => {
    if (!directSql.trim()) return;

    setLoading(true);
    setShowResults(false);

    try {
      const data = await submitDirectSql(directSql, storeResults);

      // Add the question field to match the structure expected by the results display
      data.question = "Direct SQL Query";

      setQueryResult(data);
      setShowResults(true);
      setLoading(false);

      // Refresh history if store_results was true
      if (storeResults && data.was_successful !== false) {
        loadQueryHistory();
      }
    } catch (error) {
      console.error("Error submitting direct SQL:", error);
      setLoading(false);
      alert(`Error: ${error.message}`);
    }
  };

  // Handle submission of modified SQL during approval
  const handleModifiedSqlSubmit = async () => {
    if (!editableSql.trim() || !pendingQuery) return;

    setLoading(true);
    setShowApproval(false);

    try {
      const data = await submitModifiedSql(
        pendingQuery,
        editableSql,
        storeResults
      );

      setQueryResult(data);
      setShowResults(true);
      setLoading(false);

      // Refresh history if successful and store_results was true
      if (data.was_successful !== false && storeResults) {
        loadQueryHistory();
      }

      // Clear pending query
      setPendingQuery(null);
    } catch (error) {
      console.error("Error submitting modified SQL:", error);
      setLoading(false);
      setPendingQuery(null);
      alert(`Error: ${error.message}`);
    }
  };

  // Handle SQL modal
  const showSqlModal = (sql) => {
    setSqlModalContent(sql);
    setSqlModalShow(true);
  };

  // Handle question reuse from history
  const reuseQuestion = (questionText) => {
    setQuestion(questionText);
    setActiveInputMode("nl");
  };

  // Handle SQL reuse from history
  const reuseSql = (sql) => {
    setDirectSql(sql);
    setActiveInputMode("sql");
  };

  return (
    <Container className="py-4">
      <Header />

      <QueryInput
        question={question}
        setQuestion={setQuestion}
        directSql={directSql}
        setDirectSql={setDirectSql}
        storeResults={storeResults}
        setStoreResults={setStoreResults}
        requireApproval={requireApproval}
        setRequireApproval={setRequireApproval}
        handleSubmit={handleSubmit}
        handleDirectSqlSubmit={handleDirectSqlSubmit}
        loading={loading}
        activeInputMode={activeInputMode}
        setActiveInputMode={setActiveInputMode}
      />

      {/* Loading Indicator */}
      {loading && (
        <div className="text-center my-4">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Generating SQL and fetching results...</p>
        </div>
      )}

      {/* SQL Approval Component */}
      {showApproval && (
        <SQLApproval
          pendingQuery={pendingQuery}
          editableSql={editableSql}
          setEditableSql={setEditableSql}
          handleSubmit={handleSubmit}
          handleModifiedSqlSubmit={handleModifiedSqlSubmit}
          setShowApproval={setShowApproval}
          setPendingQuery={setPendingQuery}
        />
      )}

      {/* Results Display Component */}
      {showResults && queryResult && (
        <ResultsDisplay
          queryResult={queryResult}
          reuseSql={reuseSql}
          reuseQuestion={reuseQuestion}
          showSqlModal={showSqlModal}
        />
      )}

      {/* Query History Component */}
      <QueryHistory
        history={history}
        loadQueryHistory={loadQueryHistory}
        reuseQuestion={reuseQuestion}
        reuseSql={reuseSql}
        showSqlModal={showSqlModal}
      />

      {/* SQL Modal Component */}
      <SqlModal
        show={sqlModalShow}
        onHide={() => setSqlModalShow(false)}
        sqlContent={sqlModalContent}
      />
    </Container>
  );
}

export default App;
