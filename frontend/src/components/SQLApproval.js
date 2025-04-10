import React from "react";
import { Row, Col, Card, Form, Button } from "react-bootstrap";

const SQLApproval = ({
  pendingQuery,
  editableSql,
  setEditableSql,
  handleSubmit,
  handleModifiedSqlSubmit,
  setShowApproval,
  setPendingQuery,
}) => {
  return (
    <Row className="mb-4">
      <Col>
        <Card className="shadow-sm border-warning">
          <Card.Header className="bg-warning text-dark">
            <h5 className="mb-0">SQL Approval Required</h5>
          </Card.Header>
          <Card.Body>
            <h6>Generated SQL Query:</h6>
            <Form.Group className="mb-3">
              <Form.Control
                as="textarea"
                rows={6}
                value={editableSql}
                onChange={(e) => setEditableSql(e.target.value)}
                className="code-textarea mb-3"
              />
            </Form.Group>
            <p>
              You can modify the SQL query above if needed. What would you like
              to do?
            </p>
            <div className="d-flex gap-2">
              <Button variant="success" onClick={handleModifiedSqlSubmit}>
                Execute Modified SQL
              </Button>
              <Button variant="primary" onClick={() => handleSubmit(true)}>
                Execute Original SQL
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setShowApproval(false);
                  setPendingQuery(null);
                }}>
                Cancel
              </Button>
            </div>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default SQLApproval;
