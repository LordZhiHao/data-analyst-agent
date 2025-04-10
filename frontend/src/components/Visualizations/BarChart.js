import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Alert, Form } from "react-bootstrap";

// Array of colors for multiple series
const COLORS = [
  "#8884d8",
  "#82ca9d",
  "#ffc658",
  "#ff7300",
  "#0088FE",
  "#00C49F",
];

const BarChartComponent = ({ data, config }) => {
  const [chartConfig, setChartConfig] = useState({
    xAxis: "",
    yAxis: "",
    groupBy: null,
  });

  // Initialize with API suggestions or default values
  useEffect(() => {
    if (!data || data.length === 0) return;

    const columns = Object.keys(data[0]);

    // Start with API suggestion if available
    let initialConfig = {
      xAxis: config?.x_axis || "",
      yAxis: config?.y_axis || "",
      groupBy: config?.group_by || null,
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

  // Format data for the chart if we have valid x and y axes
  const formatChartData = () => {
    if (!chartConfig.xAxis || !chartConfig.yAxis) return [];

    // If no groupBy specified, just aggregate the data by xAxis
    if (!chartConfig.groupBy) {
      // Group by x-axis value and sum y-axis values
      const grouped = {};

      data.forEach((item) => {
        const xValue = String(item[chartConfig.xAxis]);
        const yValue = Number(item[chartConfig.yAxis]) || 0;

        if (!grouped[xValue]) {
          grouped[xValue] = {
            [chartConfig.xAxis]: xValue,
            [chartConfig.yAxis]: 0,
          };
        }

        grouped[xValue][chartConfig.yAxis] += yValue;
      });

      return Object.values(grouped);
    }

    // With groupBy, we need to transform the data
    // Group by x-axis values and create series per group
    const groupedData = {};

    data.forEach((item) => {
      const xValue = String(item[chartConfig.xAxis]);
      const groupValue = String(item[chartConfig.groupBy]);
      const yValue = Number(item[chartConfig.yAxis]) || 0;

      if (!groupedData[xValue]) {
        groupedData[xValue] = { [chartConfig.xAxis]: xValue };
      }

      if (!groupedData[xValue][groupValue]) {
        groupedData[xValue][groupValue] = 0;
      }

      groupedData[xValue][groupValue] += yValue;
    });

    return Object.values(groupedData);
  };

  const chartData = formatChartData();

  // Get unique group values if using groupBy
  const getGroupValues = () => {
    if (!chartConfig.groupBy) return [chartConfig.yAxis];

    const groupSet = new Set();
    data.forEach((item) => {
      groupSet.add(String(item[chartConfig.groupBy]));
    });

    return Array.from(groupSet);
  };

  const groupValues = getGroupValues();

  // Handle changing the chart configuration
  const handleConfigChange = (field, value) => {
    setChartConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <div className="bar-chart-container">
      {/* Chart configuration controls */}
      <div className="chart-controls mb-3">
        <div className="row g-2">
          <div className="col-md-4">
            <Form.Group>
              <Form.Label>X-Axis (Categories)</Form.Label>
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
          <div className="col-md-4">
            <Form.Group>
              <Form.Label>Y-Axis (Values)</Form.Label>
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
          <div className="col-md-4">
            <Form.Group>
              <Form.Label>Group By (Optional)</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.groupBy || ""}
                onChange={(e) =>
                  handleConfigChange("groupBy", e.target.value || null)
                }>
                <option value="">None</option>
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
        </div>
      </div>

      {/* Bar Chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={chartConfig.xAxis}
              label={{
                value: chartConfig.xAxis,
                position: "insideBottom",
                offset: -5,
              }}
            />
            <YAxis
              label={{
                value: chartConfig.groupBy ? "Value" : chartConfig.yAxis,
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip />
            <Legend />
            {groupValues.map((group, index) => (
              <Bar
                key={group}
                dataKey={group}
                fill={COLORS[index % COLORS.length]}
                name={group}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <Alert variant="warning">
          Please select valid X and Y axes to display the chart
        </Alert>
      )}
    </div>
  );
};

export default BarChartComponent;
