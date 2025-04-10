import React from "react";
import { ListGroup, Badge, Alert } from "react-bootstrap";
import { formatDuration } from "../../utils/formatters";

const SimilarQueries = ({ similarQueries, reuseQuestion, showSqlModal }) => {
  return (
    <>
      <h5>Similar Queries Used for Reference</h5>
      {similarQueries && similarQueries.length > 0 ? (
        <ListGroup>
          {similarQueries.map((query, i) => (
            <ListGroup.Item
              key={i}
              action
              onClick={() => reuseQuestion(query.question)}
              className="d-flex justify-content-between align-items-start">
              <div className="ms-2 me-auto">
                <div className="fw-bold">{query.question}</div>
                <small className="text-muted">
                  Execution time: {formatDuration(query.execution_time)}
                </small>
                <div>
                  <small
                    className="text-primary cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      showSqlModal(query.sql);
                    }}>
                    View SQL
                  </small>
                </div>
              </div>
              <Badge bg={query.was_successful ? "success" : "danger"} pill>
                {query.was_successful ? "Success" : "Failed"}
              </Badge>
            </ListGroup.Item>
          ))}
        </ListGroup>
      ) : (
        <Alert variant="info">No similar queries found in the database.</Alert>
      )}
    </>
  );
};

export default SimilarQueries;
