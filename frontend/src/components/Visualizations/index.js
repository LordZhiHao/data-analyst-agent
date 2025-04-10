import React, { useState, useEffect } from "react";
import { Alert, Spinner, Button, Card } from "react-bootstrap";

import LineChartComponent from "./LineChart";
import BarChartComponent from "./BarChart";
import PieChartComponent from "./PieChart";
import ScatterChartComponent from "./ScatterChart";
import DataSummary from "./DataSummary";
import { getVisualizationSuggestions } from "../../utils/api";

const VisualizationSelector = ({ data }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [selectedChart, setSelectedChart] = useState(null);

  useEffect(() => {
    if (!data || data.length === 0) {
      setLoading(false);
      return;
    }

    const fetchSuggestions = async () => {
      try {
        setLoading(true);
        const result = await getVisualizationSuggestions(data);
        setSuggestions(result);
        setSelectedChart(result.recommended_chart || "table");
        setLoading(false);
      } catch (err) {
        console.error("Error getting visualization suggestions:", err);
        setError("Failed to get visualization suggestions");
        setLoading(false);
      }
    };

    fetchSuggestions();
  }, [data]);

  const renderVisualization = () => {
    if (!suggestions || !selectedChart) return null;

    // Find the configuration for the selected chart type
    const chartConfig = suggestions.possible_charts.find(
      (chart) => chart.type === selectedChart
    );

    switch (selectedChart) {
      case "line":
        return (
          <LineChartComponent
            data={data}
            config={chartConfig?.suggested_config}
          />
        );
      case "bar":
        return (
          <BarChartComponent
            data={data}
            config={chartConfig?.suggested_config}
          />
        );
      case "pie":
        return (
          <PieChartComponent
            data={data}
            config={chartConfig?.suggested_config}
          />
        );
      case "scatter":
        return (
          <ScatterChartComponent
            data={data}
            config={chartConfig?.suggested_config}
          />
        );
      case "table":
      default:
        return (
          <Alert variant="info">
            This data is best viewed in table format. No suitable visualization
            available.
          </Alert>
        );
    }
  };

  // Chart type selector buttons
  const renderChartTypeSelector = () => {
    if (
      !suggestions ||
      !suggestions.possible_charts ||
      suggestions.possible_charts.length === 0
    ) {
      return null;
    }

    return (
      <div className="chart-type-selector mb-3">
        <div className="d-flex flex-wrap gap-2">
          {suggestions.possible_charts.map((chart) => (
            <Button
              key={chart.type}
              variant={
                selectedChart === chart.type ? "primary" : "outline-primary"
              }
              size="sm"
              onClick={() => setSelectedChart(chart.type)}>
              {chart.type.charAt(0).toUpperCase() + chart.type.slice(1)}
            </Button>
          ))}
        </div>
        {selectedChart && renderChartReason()}
      </div>
    );
  };

  // Shows reason for chart suggestion
  const renderChartReason = () => {
    const chartConfig = suggestions.possible_charts.find(
      (chart) => chart.type === selectedChart
    );
    if (!chartConfig || !chartConfig.reason) return null;

    return (
      <small className="text-muted d-block mt-2">{chartConfig.reason}</small>
    );
  };

  if (loading) {
    return (
      <div className="text-center my-4">
        <Spinner animation="border" variant="primary" size="sm" />
        <p className="mt-2">Analyzing data for visualization...</p>
      </div>
    );
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  if (!data || data.length === 0) {
    return <Alert variant="info">No data available for visualization</Alert>;
  }

  return (
    <Card className="mb-4">
      <Card.Body>
        <h5>Data Visualization</h5>

        {renderChartTypeSelector()}

        <div className="visualization-container">{renderVisualization()}</div>

        <DataSummary data={data} />
      </Card.Body>
    </Card>
  );
};

export default VisualizationSelector;
