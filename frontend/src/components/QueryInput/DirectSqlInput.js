import React from "react";
import { Form, Button, Card } from "react-bootstrap";

const DirectSqlInput = ({
  directSql,
  setDirectSql,
  storeResults,
  setStoreResults,
  handleDirectSqlSubmit,
  loading,
}) => {
  return (
    <>
      <Card.Title>Write SQL Query</Card.Title>
      <Form.Group className="mb-3">
        <Form.Control
          as="textarea"
          rows={5}
          placeholder="SELECT * FROM `your_dataset.your_table` LIMIT 10"
          value={directSql}
          onChange={(e) => setDirectSql(e.target.value)}
          className="code-textarea"
        />
      </Form.Group>
      <div className="d-flex justify-content-between align-items-center">
        <div>
          <Form.Check
            type="checkbox"
            id="store-results-check-sql"
            label="Store for future reference"
            checked={storeResults}
            onChange={(e) => setStoreResults(e.target.checked)}
          />
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={handleDirectSqlSubmit}
          disabled={loading || !directSql.trim()}>
          Execute SQL
        </Button>
      </div>
    </>
  );
};

export default DirectSqlInput;
