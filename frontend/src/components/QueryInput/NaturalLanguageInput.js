import React from "react";
import { Form, Button, Card } from "react-bootstrap";

const NaturalLanguageInput = ({
  question,
  setQuestion,
  storeResults,
  setStoreResults,
  requireApproval,
  setRequireApproval,
  handleSubmit,
  loading,
}) => {
  return (
    <>
      <Card.Title>Ask a Question</Card.Title>
      <Form.Group className="mb-3">
        <Form.Control
          size="lg"
          type="text"
          placeholder="e.g., Show me total sales by region for the last quarter"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === "Enter") handleSubmit(false);
          }}
        />
      </Form.Group>
      <div className="d-flex justify-content-between align-items-center">
        <div>
          <Form.Check
            type="checkbox"
            id="store-results-check-nl"
            label="Store for future learning"
            checked={storeResults}
            onChange={(e) => setStoreResults(e.target.checked)}
            className="mb-2"
          />
          <Form.Check
            type="checkbox"
            id="require-approval-check"
            label="Require approval before executing"
            checked={requireApproval}
            onChange={(e) => setRequireApproval(e.target.checked)}
          />
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={() => handleSubmit(false)}
          disabled={loading || !question.trim()}>
          Ask
        </Button>
      </div>
    </>
  );
};

export default NaturalLanguageInput;
