import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
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

const LineChartComponent = ({ data, config }) => {
  const [chartConfig, setChartConfig] = useState({
    xAxis: "",
    yAxis: "",
    series: null,
  });

  // Initialize with API suggestions or default values
  useEffect(() => {
    if (!data || data.length === 0) return;

    const columns = Object.keys(data[0]);

    // Start with API suggestion if available
    let initialConfig = {
      xAxis: config?.x_axis || "",
      yAxis: config?.y_axis || "",
      series: config?.series || null,
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

    // If no series specified, just use the data as is
    if (!chartConfig.series) {
      return data.map((item) => ({
        [chartConfig.xAxis]: item[chartConfig.xAxis],
        [chartConfig.yAxis]: Number(item[chartConfig.yAxis]) || 0,
      }));
    }

    // With series, we need to transform the data
    // Group by x-axis values
    const groupedData = {};

    data.forEach((item) => {
      const xValue = item[chartConfig.xAxis];
      const seriesValue = String(item[chartConfig.series]);
      const yValue = Number(item[chartConfig.yAxis]) || 0;

      if (!groupedData[xValue]) {
        groupedData[xValue] = { [chartConfig.xAxis]: xValue };
      }

      groupedData[xValue][seriesValue] = yValue;
    });

    return Object.values(groupedData);
  };

  const chartData = formatChartData();

  // Get unique series values if using series
  const getSeriesValues = () => {
    if (!chartConfig.series) return [chartConfig.yAxis];

    const seriesSet = new Set();
    data.forEach((item) => {
      seriesSet.add(String(item[chartConfig.series]));
    });

    return Array.from(seriesSet);
  };

  const seriesValues = getSeriesValues();

  // Handle changing the chart configuration
  const handleConfigChange = (field, value) => {
    setChartConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <div className="line-chart-container">
      {/* Chart configuration controls */}
      <div className="chart-controls mb-3">
        <div className="row g-2">
          <div className="col-md-4">
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
          <div className="col-md-4">
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
          <div className="col-md-4">
            <Form.Group>
              <Form.Label>Series (Optional)</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.series || ""}
                onChange={(e) =>
                  handleConfigChange("series", e.target.value || null)
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

      {/* Line Chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
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
                value: chartConfig.yAxis,
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip />
            <Legend />
            {seriesValues.map((series, index) => (
              <Line
                key={series}
                type="monotone"
                dataKey={series}
                stroke={COLORS[index % COLORS.length]}
                activeDot={{ r: 8 }}
                name={series}
              />
            ))}
            {chartData.length > 10 && (
              <Brush dataKey={chartConfig.xAxis} height={30} stroke="#8884d8" />
            )}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <Alert variant="warning">
          Please select valid X and Y axes to display the chart
        </Alert>
      )}
    </div>
  );
};

export default LineChartComponent;
