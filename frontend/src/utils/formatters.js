/**
 * Format time duration in seconds to a readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string
 */
export const formatDuration = (seconds) => {
  if (seconds < 1) return `${(seconds * 1000).toFixed(2)} ms`;
  return `${seconds.toFixed(2)} seconds`;
};

/**
 * Format a date string to a localized date time string
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export const formatDateTime = (dateString) => {
  try {
    return new Date(dateString).toLocaleString();
  } catch (e) {
    return dateString || "";
  }
};

/**
 * Truncate a string if it exceeds the maximum length
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum allowed length
 * @returns {string} Truncated string with ellipsis if needed
 */
export const truncateString = (str, maxLength = 50) => {
  if (!str || str.length <= maxLength) return str;
  return `${str.substring(0, maxLength)}...`;
};
