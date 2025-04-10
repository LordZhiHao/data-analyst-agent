import React, { useState, useEffect } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Alert, Form } from "react-bootstrap";

// Array of colors for different scatter series
const COLORS = [
  "#8884d8",
  "#82ca9d",
  "#ffc658",
  "#ff7300",
  "#0088FE",
  "#00C49F",
];

const ScatterChartComponent = ({ data, config }) => {
  const [chartConfig, setChartConfig] = useState({
    xAxis: "",
    yAxis: "",
    size: null,
    color: null,
  });

  // Initialize with API suggestions or default values
  useEffect(() => {
    if (!data || data.length === 0) return;

    const columns = Object.keys(data[0]);

    // Start with API suggestion if available
    let initialConfig = {
      xAxis: config?.x_axis || "",
      yAxis: config?.y_axis || "",
      size: config?.size || null,
      color: config?.color || null,
    };

    // Default to first column as X axis if not specified
    if (!initialConfig.xAxis && columns.length > 0) {
      initialConfig.xAxis = columns[0];
    }

    // Default to second column as Y axis if not specified
    if (!initialConfig.yAxis && columns.length > 1) {
      initialConfig.yAxis = columns[1];
    }

    setChartConfig(initialConfig);
  }, [data, config]);

  if (!data || data.length === 0) {
    return <Alert variant="info">No data available for visualization</Alert>;
  }

  const columns = Object.keys(data[0]);

  // Format data for the scatter chart
  const formatChartData = () => {
    if (!chartConfig.xAxis || !chartConfig.yAxis) return [];

    // Map the data to the required format for ScatterChart
    return data.map((item) => ({
      x: Number(item[chartConfig.xAxis]) || 0,
      y: Number(item[chartConfig.yAxis]) || 0,
      z: chartConfig.size ? Number(item[chartConfig.size]) || 1 : 100,
      name: chartConfig.xAxis,
      group: chartConfig.color ? String(item[chartConfig.color]) : "default",
    }));
  };

  // Group data by color category if specified
  const groupDataByColor = (formattedData) => {
    if (!chartConfig.color) {
      return { default: formattedData };
    }

    const grouped = {};

    formattedData.forEach((item) => {
      if (!grouped[item.group]) {
        grouped[item.group] = [];
      }

      grouped[item.group].push(item);
    });

    return grouped;
  };

  const formattedData = formatChartData();
  const groupedData = groupDataByColor(formattedData);
  const groups = Object.keys(groupedData);

  // Handle changing the chart configuration
  const handleConfigChange = (field, value) => {
    setChartConfig((prev) => ({
      ...prev,
      [field]: value === "" ? null : value,
    }));
  };

  // Custom tooltip to show point details
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;

      return (
        <div
          className="custom-tooltip"
          style={{
            backgroundColor: "white",
            padding: "10px",
            border: "1px solid #ccc",
            borderRadius: "4px",
          }}>
          <p style={{ margin: 0 }}>
            <strong>
              {chartConfig.color ? `Group: ${data.group}` : "Point"}
            </strong>
          </p>
          <p style={{ margin: 0 }}>{`${chartConfig.xAxis}: ${data.x}`}</p>
          <p style={{ margin: 0 }}>{`${chartConfig.yAxis}: ${data.y}`}</p>
          {chartConfig.size && (
            <p style={{ margin: 0 }}>{`${chartConfig.size}: ${data.z}`}</p>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div className="scatter-chart-container">
      {/* Chart configuration controls */}
      <div className="chart-controls mb-3">
        <div className="row g-2">
          <div className="col-md-3">
            <Form.Group>
              <Form.Label>X-Axis</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.xAxis}
                onChange={(e) => handleConfigChange("xAxis", e.target.value)}>
                <option value="">Select X-Axis</option>
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-md-3">
            <Form.Group>
              <Form.Label>Y-Axis</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.yAxis}
                onChange={(e) => handleConfigChange("yAxis", e.target.value)}>
                <option value="">Select Y-Axis</option>
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-md-3">
            <Form.Group>
              <Form.Label>Size (Optional)</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.size || ""}
                onChange={(e) => handleConfigChange("size", e.target.value)}>
                <option value="">Default Size</option>
                {columns
                  .filter(
                    (col) =>
                      col !== chartConfig.xAxis && col !== chartConfig.yAxis
                  )
                  .map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-md-3">
            <Form.Group>
              <Form.Label>Color By (Optional)</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.color || ""}
                onChange={(e) => handleConfigChange("color", e.target.value)}>
                <option value="">Single Color</option>
                {columns
                  .filter(
                    (col) =>
                      col !== chartConfig.xAxis &&
                      col !== chartConfig.yAxis &&
                      col !== chartConfig.size
                  )
                  .map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
              </Form.Select>
            </Form.Group>
          </div>
        </div>
      </div>

      {/* Scatter Chart */}
      {formattedData.length > 0 ? (
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name={chartConfig.xAxis}
              label={{
                value: chartConfig.xAxis,
                position: "insideBottom",
                offset: -5,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name={chartConfig.yAxis}
              label={{
                value: chartConfig.yAxis,
                angle: -90,
                position: "insideLeft",
              }}
            />
            {chartConfig.size && (
              <ZAxis
                type="number"
                dataKey="z"
                range={[60, 400]}
                name={chartConfig.size}
              />
            )}
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {groups.map((group, index) => (
              <Scatter
                key={group}
                name={group === "default" ? "Points" : group}
                data={groupedData[group]}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      ) : (
        <Alert variant="warning">
          Please select valid X and Y axes to display the chart
        </Alert>
      )}
    </div>
  );
};

export default ScatterChartComponent;
