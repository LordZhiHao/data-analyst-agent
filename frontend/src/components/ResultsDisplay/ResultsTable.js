import React from "react";
import { Badge, Table, Alert } from "react-bootstrap";
import { formatDuration } from "../../utils/formatters";

const ResultsTable = ({ queryResult }) => {
  return (
    <>
      <h5>{queryResult.question}</h5>
      <div className="mb-2">
        {queryResult.was_successful ? (
          <Badge bg="success">Successful</Badge>
        ) : (
          <Badge bg="danger">Failed</Badge>
        )}
        {queryResult.was_successful && (
          <small className="text-muted ms-2">
            Execution time: {formatDuration(queryResult.execution_time)}
          </small>
        )}
      </div>
      <div className="result-container mt-3">
        {queryResult.was_successful ? (
          queryResult.results && queryResult.results.length > 0 ? (
            <Table striped hover responsive>
              <thead>
                <tr>
                  {Object.keys(queryResult.results[0]).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {queryResult.results.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val, j) => (
                      <td key={j}>{val !== null ? String(val) : ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <Alert variant="info">No results returned from query.</Alert>
          )
        ) : (
          <Alert variant="danger">
            {queryResult.error_message ||
              "An error occurred during query execution."}
          </Alert>
        )}
      </div>
    </>
  );
};

export default ResultsTable;
