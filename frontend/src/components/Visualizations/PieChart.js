import React, { useState, useEffect } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import { Alert, Form } from "react-bootstrap";

// Array of colors for pie slices
const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#8884d8",
  "#82ca9d",
];

const PieChartComponent = ({ data, config }) => {
  const [chartConfig, setChartConfig] = useState({
    nameKey: "", // Category name
    valueKey: "", // Value to measure
  });

  // Initialize with API suggestions or default values
  useEffect(() => {
    if (!data || data.length === 0) return;

    const columns = Object.keys(data[0]);

    // Start with API suggestion if available
    let initialConfig = {
      nameKey: config?.name || "",
      valueKey: config?.value || "",
    };

    // Default to first column as name if not specified
    if (!initialConfig.nameKey && columns.length > 0) {
      initialConfig.nameKey = columns[0];
    }

    // Default to second column as value if not specified
    if (!initialConfig.valueKey && columns.length > 1) {
      initialConfig.valueKey = columns[1];
    }

    setChartConfig(initialConfig);
  }, [data, config]);

  if (!data || data.length === 0) {
    return <Alert variant="info">No data available for visualization</Alert>;
  }

  const columns = Object.keys(data[0]);

  // Format data for the pie chart
  const formatChartData = () => {
    if (!chartConfig.nameKey || !chartConfig.valueKey) return [];

    // Group by name and sum values
    const grouped = {};

    data.forEach((item) => {
      const name = String(item[chartConfig.nameKey]);
      const value = Number(item[chartConfig.valueKey]) || 0;

      if (!grouped[name]) {
        grouped[name] = {
          name,
          value: 0,
        };
      }

      grouped[name].value += value;
    });

    // Convert to array and sort by value (descending)
    return Object.values(grouped)
      .sort((a, b) => b.value - a.value)
      .slice(0, 10); // Limit to top 10 for readability
  };

  const chartData = formatChartData();

  // Handle changing the chart configuration
  const handleConfigChange = (field, value) => {
    setChartConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  // Custom tooltip to show percentage
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const totalValue = chartData.reduce((sum, item) => sum + item.value, 0);
      const percentage = ((payload[0].value / totalValue) * 100).toFixed(1);

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
            <strong>{payload[0].name}</strong>
          </p>
          <p style={{ margin: 0 }}>{`${payload[0].value} (${percentage}%)`}</p>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="pie-chart-container">
      {/* Chart configuration controls */}
      <div className="chart-controls mb-3">
        <div className="row g-2">
          <div className="col-md-6">
            <Form.Group>
              <Form.Label>Category (Name)</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.nameKey}
                onChange={(e) => handleConfigChange("nameKey", e.target.value)}>
                <option value="">Select Category</option>
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-md-6">
            <Form.Group>
              <Form.Label>Value</Form.Label>
              <Form.Select
                size="sm"
                value={chartConfig.valueKey}
                onChange={(e) =>
                  handleConfigChange("valueKey", e.target.value)
                }>
                <option value="">Select Value</option>
                {columns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
        </div>
      </div>

      {/* Pie Chart */}
      {chartData.length > 0 ? (
        <>
          {chartData.length > 10 && (
            <Alert variant="info" className="mb-3">
              Showing top 10 categories by value for better readability
            </Alert>
          )}

          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name}: ${(percent * 100).toFixed(1)}%`
                }
                outerRadius={150}
                fill="#8884d8"
                dataKey="value">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </>
      ) : (
        <Alert variant="warning">
          Please select valid category and value fields to display the chart
        </Alert>
      )}
    </div>
  );
};

export default PieChartComponent;
