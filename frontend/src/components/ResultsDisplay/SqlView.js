import React from "react";
import { Button } from "react-bootstrap";
import Highlight from "react-highlight";

const SqlView = ({ sql, reuseSql }) => {
  return (
    <>
      <h5>SQL Query</h5>
      <div className="bg-light p-3 rounded">
        <Highlight className="sql">{sql}</Highlight>
      </div>
      <div className="mt-3">
        <Button
          variant="outline-primary"
          size="sm"
          onClick={() => reuseSql(sql)}>
          Reuse as Direct SQL
        </Button>
      </div>
    </>
  );
};

export default SqlView;
