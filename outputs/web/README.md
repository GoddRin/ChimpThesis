# Interactive defense map (static)

**Open locally:** double-click `index.html` (works from a USB stick, no internet, no server). Chrome, Edge, Firefox and Safari are supported.
**Host online (GitHub Pages):** push this folder, then Settings -> Pages -> deploy from the branch/folder that contains `index.html`.

Contents: `index.html`, `app.js`, `style.css`, `vendor/` (Leaflet 1.9.4, BSD-2), `data/*.js` (the layers; regenerate with `make web`).
The optional OpenStreetMap / Esri backgrounds need internet; everything else works offline.

Layers: rebuilt risk segments (50 m), shorelines 1990/2000/2010/2020/2025, study barangays, other barangays, transects, legacy risk polygons (marked NOT valid; for the "why did the map change?" question).

Known limitations: classification uses erosion rate only (not exposure/vulnerability); positional error and image dates were not supplied (a +-30 m what-if is used for the confidence label); the Cagayan River banks are not classified; the shoreline set is `vector_clean` (provenance of the original lines unknown).
