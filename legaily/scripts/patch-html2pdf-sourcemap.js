/**
 * html2pdf.js bundles es6-promise with //# sourceMappingURL=es6-promise.map
 * but does not ship that file. CRA's source-map-loader warns on every build.
 */
const fs = require("fs");
const path = require("path");

const mapPath = path.join(
  __dirname,
  "..",
  "node_modules",
  "html2pdf.js",
  "dist",
  "es6-promise.map"
);

const stub = JSON.stringify({
  version: 3,
  file: "es6-promise.js",
  sources: [],
  names: [],
  mappings: "",
});

if (!fs.existsSync(path.dirname(mapPath))) {
  process.exit(0);
}

if (!fs.existsSync(mapPath)) {
  fs.writeFileSync(mapPath, stub);
  console.log("patched: html2pdf.js/dist/es6-promise.map");
}
