import React from "react";
import { Row, Col, Card, Button, Table, Badge, Alert } from "react-bootstrap";
import { formatDuration, formatDateTime } from "../utils/formatters";

const QueryHistory = ({
  history,
  loadQueryHistory,
  reuseQuestion,
  reuseSql,
  showSqlModal,
}) => {
  return (
    <Row>
      <Col>
        <Card className="shadow-sm">
          <Card.Header>
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Query History</h5>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={loadQueryHistory}>
                Refresh
              </Button>
            </div>
          </Card.Header>
          <Card.Body>
            {history.length > 0 ? (
              <Table hover responsive>
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Status</th>
                    <th>Time</th>
                    <th>Timestamp</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item, index) => (
                    <tr key={index}>
                      <td>{item.question}</td>
                      <td>
                        <Badge bg={item.was_successful ? "success" : "danger"}>
                          {item.was_successful ? "Success" : "Failed"}
                        </Badge>
                      </td>
                      <td>{formatDuration(item.execution_time)}</td>
                      <td>{formatDateTime(item.timestamp)}</td>
                      <td>
                        <Button
                          variant="outline-primary"
                          size="sm"
                          className="me-2"
                          onClick={() => reuseQuestion(item.question)}>
                          Reuse Question
                        </Button>
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          className="me-2"
                          onClick={() => reuseSql(item.sql)}>
                          Reuse SQL
                        </Button>
                        <Button
                          variant="outline-info"
                          size="sm"
                          onClick={() => showSqlModal(item.sql)}>
                          View SQL
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <Alert variant="info">No query history available.</Alert>
            )}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default QueryHistory;
