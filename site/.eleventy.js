module.exports = function(eleventyConfig) {
  // Copy CSS to output
  eleventyConfig.addPassthroughCopy("css");

  // Load opportunities data
  eleventyConfig.addGlobalData("opportunities", () => {
    const fs = require("fs");
    const path = require("path");
    const dataPath = path.join(__dirname, "..", "data", "opportunities.json");

    if (fs.existsSync(dataPath)) {
      const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
      return data;
    }
    return [];
  });

  // Date formatting filter
  eleventyConfig.addFilter("formatDate", (dateStr) => {
    if (!dateStr) return "No deadline";
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    } catch {
      return dateStr;
    }
  });

  // Check if deadline is soon (within 14 days)
  eleventyConfig.addFilter("isClosingSoon", (dateStr) => {
    if (!dateStr) return false;
    try {
      const deadline = new Date(dateStr);
      if (isNaN(deadline.getTime())) return false;
      const now = new Date();
      const diffDays = (deadline - now) / (1000 * 60 * 60 * 24);
      return diffDays > 0 && diffDays <= 14;
    } catch {
      return false;
    }
  });

  // Check if deadline has passed
  eleventyConfig.addFilter("isExpired", (dateStr) => {
    if (!dateStr) return false;
    try {
      const deadline = new Date(dateStr);
      if (isNaN(deadline.getTime())) return false;
      return deadline < new Date();
    } catch {
      return false;
    }
  });

  // Truncate text
  eleventyConfig.addFilter("truncate", (str, length = 200) => {
    if (!str) return "";
    if (str.length <= length) return str;
    return str.substring(0, length) + "...";
  });

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes"
    },
    templateFormats: ["njk", "html", "md"],
    htmlTemplateEngine: "njk"
  };
};
