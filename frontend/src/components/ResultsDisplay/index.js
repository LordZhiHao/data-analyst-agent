import React, { useState } from "react";
import { Row, Col, Card, Nav, Tab } from "react-bootstrap";
import ResultsTable from "./ResultsTable";
import SqlView from "./SqlView";
import SimilarQueries from "./SimilarQueries";
import VisualizationSelector from "../Visualizations"; // Import our visualization component

const ResultsDisplay = ({
  queryResult,
  reuseSql,
  reuseQuestion,
  showSqlModal,
}) => {
  const [activeTab, setActiveTab] = useState("results");

  return (
    <Row className="mb-4">
      <Col>
        <Card className="shadow-sm">
          <Card.Body>
            <Tab.Container
              activeKey={activeTab}
              onSelect={(k) => setActiveTab(k)}>
              <Nav variant="tabs" className="mb-3">
                <Nav.Item>
                  <Nav.Link eventKey="results">Results</Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="visualization">Visualization</Nav.Link>
                </Nav.Item>
                <Nav.Item>
                  <Nav.Link eventKey="sql">SQL Query</Nav.Link>
                </Nav.Item>
                {queryResult.similar_queries && (
                  <Nav.Item>
                    <Nav.Link eventKey="similar">Similar Queries</Nav.Link>
                  </Nav.Item>
                )}
              </Nav>
              <Tab.Content>
                <Tab.Pane eventKey="results">
                  <ResultsTable queryResult={queryResult} />
                </Tab.Pane>

                <Tab.Pane eventKey="visualization">
                  {queryResult.was_successful &&
                  queryResult.results &&
                  queryResult.results.length > 0 ? (
                    <VisualizationSelector data={queryResult.results} />
                  ) : (
                    <div className="alert alert-warning">
                      Visualization is only available for successful queries
                      with results
                    </div>
                  )}
                </Tab.Pane>

                <Tab.Pane eventKey="sql">
                  <SqlView sql={queryResult.sql} reuseSql={reuseSql} />
                </Tab.Pane>

                {queryResult.similar_queries && (
                  <Tab.Pane eventKey="similar">
                    <SimilarQueries
                      similarQueries={queryResult.similar_queries}
                      reuseQuestion={reuseQuestion}
                      showSqlModal={showSqlModal}
                    />
                  </Tab.Pane>
                )}
              </Tab.Content>
            </Tab.Container>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default ResultsDisplay;
