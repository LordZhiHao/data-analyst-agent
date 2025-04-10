import React, { useState, useEffect } from "react";
import {
  Card,
  Accordion,
  Badge,
  Alert,
  Spinner,
  ListGroup,
} from "react-bootstrap";
import { analyzeData } from "../../utils/api";

const DataSummary = ({ data }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    if (!data || data.length === 0) {
      setLoading(false);
      return;
    }

    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        const result = await analyzeData(data);
        setAnalysis(result);
        setLoading(false);
      } catch (err) {
        console.error("Error analyzing data:", err);
        setError("Failed to analyze data");
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [data]);

  if (loading) {
    return (
      <div className="text-center my-4">
        <Spinner animation="border" variant="primary" size="sm" />
        <p className="mt-2">Analyzing data...</p>
      </div>
    );
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  if (!analysis) {
    return <Alert variant="info">No analysis available</Alert>;
  }

  // Handle error response from the API
  if (analysis.error) {
    return <Alert variant="warning">{analysis.error}</Alert>;
  }

  // Check if Gemini insights are available
  const hasGeminiInsights =
    analysis.ai_analysis &&
    !analysis.ai_analysis.error &&
    (analysis.ai_analysis.executive_summary ||
      analysis.ai_analysis.key_insights ||
      analysis.ai_analysis.gemini_analysis);

  return (
    <div className="data-summary mt-4">
      <h6>Data Insights</h6>

      {/* Gemini AI Analysis (if available) */}
      {hasGeminiInsights && (
        <Alert variant="info" className="mb-3">
          <h6 className="alert-heading">AI Analysis</h6>

          {analysis.ai_analysis.executive_summary && (
            <div className="mb-2">
              <strong>Summary:</strong> {analysis.ai_analysis.executive_summary}
            </div>
          )}

          {analysis.ai_analysis.key_insights &&
            analysis.ai_analysis.key_insights.length > 0 && (
              <div className="mb-2">
                <strong>Key Insights:</strong>
                <ListGroup variant="flush" className="mt-1">
                  {analysis.ai_analysis.key_insights.map((insight, index) => (
                    <ListGroup.Item key={index} className="py-1 ps-2 border-0">
                      • {insight}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </div>
            )}

          {analysis.ai_analysis.recommended_steps &&
            analysis.ai_analysis.recommended_steps.length > 0 && (
              <div className="mb-2">
                <strong>Recommended Steps:</strong>
                <ListGroup variant="flush" className="mt-1">
                  {analysis.ai_analysis.recommended_steps.map((step, index) => (
                    <ListGroup.Item key={index} className="py-1 ps-2 border-0">
                      • {step}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </div>
            )}

          {analysis.ai_analysis.data_limitations &&
            analysis.ai_analysis.data_limitations.length > 0 && (
              <div>
                <strong>Data Limitations:</strong>
                <ListGroup variant="flush" className="mt-1">
                  {analysis.ai_analysis.data_limitations.map(
                    (limitation, index) => (
                      <ListGroup.Item
                        key={index}
                        className="py-1 ps-2 border-0">
                        • {limitation}
                      </ListGroup.Item>
                    )
                  )}
                </ListGroup>
              </div>
            )}

          {/* For unstructured Gemini analysis */}
          {analysis.ai_analysis.gemini_analysis && (
            <div className="mt-2">
              <p>{analysis.ai_analysis.gemini_analysis}</p>
            </div>
          )}
        </Alert>
      )}

      {/* Basic insights */}
      {analysis.insights && analysis.insights.length > 0 && (
        <Alert variant="secondary" className="mb-3">
          <h6 className="alert-heading">Basic Statistical Insights</h6>
          <ul className="mb-0">
            {analysis.insights.map((insight, index) => (
              <li key={index}>{insight}</li>
            ))}
          </ul>
        </Alert>
      )}

      {/* Dataset summary */}
      <div className="mb-3">
        <small>
          <Badge bg="secondary" className="me-2">
            Rows: {analysis.row_count}
          </Badge>
          <Badge bg="secondary" className="me-2">
            Columns: {analysis.column_count}
          </Badge>
        </small>
      </div>

      {/* Column details */}
      <Accordion>
        <Accordion.Item eventKey="0">
          <Accordion.Header>Column Details</Accordion.Header>
          <Accordion.Body>
            <div className="column-details">
              {Object.entries(analysis.columns || {}).map(
                ([colName, colData]) => (
                  <Card key={colName} className="mb-2">
                    <Card.Header className="py-2">
                      <strong>{colName}</strong>
                      <Badge
                        bg={
                          colData.type === "numeric"
                            ? "primary"
                            : colData.type === "datetime"
                            ? "success"
                            : "info"
                        }
                        className="ms-2">
                        {colData.type}
                      </Badge>
                    </Card.Header>
                    <Card.Body className="py-2">
                      <small>
                        {colData.null_count > 0 && (
                          <div className="text-warning mb-1">
                            Missing values: {colData.null_count} (
                            {colData.null_percentage}%)
                          </div>
                        )}

                        {/* Numeric column stats */}
                        {colData.type === "numeric" && (
                          <div>
                            <div>
                              Range: {colData.min} to {colData.max}
                            </div>
                            <div>
                              Average: {colData.mean?.toFixed(2)} / Median:{" "}
                              {colData.median?.toFixed(2)}
                            </div>
                            <div>Std Dev: {colData.std_dev?.toFixed(2)}</div>

                            {colData.potential_outliers && (
                              <div className="text-warning mt-1">
                                Outliers detected: {colData.outlier_count}{" "}
                                values
                              </div>
                            )}
                          </div>
                        )}

                        {/* Categorical column stats */}
                        {colData.type === "categorical" && (
                          <div>
                            <div>Unique values: {colData.unique_count}</div>
                            {colData.top_values &&
                              Object.keys(colData.top_values).length > 0 && (
                                <div>
                                  Top values:
                                  <ul className="mb-0 mt-1">
                                    {Object.entries(colData.top_values).map(
                                      ([value, count]) => (
                                        <li key={value}>
                                          {value}: {count} items
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </div>
                              )}
                          </div>
                        )}

                        {/* Datetime column stats */}
                        {colData.type === "datetime" && (
                          <div>
                            <div>
                              Range: {colData.min_date} to {colData.max_date}
                            </div>
                            {colData.date_range_days && (
                              <div>Span: {colData.date_range_days} days</div>
                            )}
                          </div>
                        )}
                      </small>
                    </Card.Body>
                  </Card>
                )
              )}
            </div>
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
    </div>
  );
};

export default DataSummary;
