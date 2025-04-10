import React from "react";
import { Card, Tabs, Tab } from "react-bootstrap";
import NaturalLanguageInput from "./NaturalLanguageInput";
import DirectSqlInput from "./DirectSqlInput";

const QueryInput = ({
  question,
  setQuestion,
  directSql,
  setDirectSql,
  storeResults,
  setStoreResults,
  requireApproval,
  setRequireApproval,
  handleSubmit,
  handleDirectSqlSubmit,
  loading,
  activeInputMode,
  setActiveInputMode,
}) => {
  return (
    <Card className="shadow-sm mb-4">
      <Card.Body>
        <Tabs
          activeKey={activeInputMode}
          onSelect={(k) => setActiveInputMode(k)}
          className="mb-3">
          {/* Natural Language Tab */}
          <Tab eventKey="nl" title="Natural Language">
            <NaturalLanguageInput
              question={question}
              setQuestion={setQuestion}
              storeResults={storeResults}
              setStoreResults={setStoreResults}
              requireApproval={requireApproval}
              setRequireApproval={setRequireApproval}
              handleSubmit={handleSubmit}
              loading={loading}
            />
          </Tab>

          {/* Direct SQL Tab */}
          <Tab eventKey="sql" title="Direct SQL">
            <DirectSqlInput
              directSql={directSql}
              setDirectSql={setDirectSql}
              storeResults={storeResults}
              setStoreResults={setStoreResults}
              handleDirectSqlSubmit={handleDirectSqlSubmit}
              loading={loading}
            />
          </Tab>
        </Tabs>
      </Card.Body>
    </Card>
  );
};

export default QueryInput;
