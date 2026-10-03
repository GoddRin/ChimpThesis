/*
 * gee_v2.js  -  Landsat water-index composites for a DEFENSIBLE shoreline (Phase 3C)
 * ===========================================================================
 * STATUS: written, NOT executed by the analyst (no Earth Engine login in the analysis sandbox).
 *         Run it yourself in the Earth Engine Code Editor with your own account, check the printed
 *         image counts, then start the Tasks. Keep the legacy script (Code.docx) untouched.
 *
 * What is different from the legacy script (see docs/01b_gee_audit.md):
 *   1. SEASONAL composite: only the months in MONTHS, every year - not a whole-year median.
 *   2. The water INDEX IMAGES are exported (the legacy script exported only an edge mask), so the
 *      shoreline can be a sub-pixel contour at a PER-YEAR Otsu threshold (done in Python, make landsat).
 *   3. Scene list exported (year, id, date, sensor, cloud cover) -> image counts / dates are on record.
 *   4. Exported in EPSG:32651 (metres) over an AOI that covers ALL EIGHT barangays
 *      (the legacy box missed Bulala Sur and Paddaya).
 *
 * Files to download from Drive into data/raw/landsat_v2/ :
 *   MNDWI_<year>.tif (and NDWI_/AWEIsh_ if you change INDEX), scenes.csv
 *
 * [PROPOSAL] values below must be confirmed by the students/adviser: MONTHS, WINDOW_YEARS, INDEX.
 */

// ---------------------------------------------------------------- parameters
var AOI = ee.Geometry.Rectangle([121.55, 18.28, 121.78, 18.41]);   // lon/lat: Bulala Sur ... Paddaya
var YEARS = [1990, 2000, 2010, 2020, 2025];
var MONTHS = [3, 4, 5];       // [PROPOSAL] Mar-May: low rainfall, calmer sea than the NE-monsoon/typhoon months
var WINDOW_YEARS = 1;         // [PROPOSAL] +/- years around each target year to get enough scenes (record it in the thesis!)
var MAX_CLOUD = 60;           // scene-level cloud cover filter (%)
var INDEX = 'MNDWI';          // 'NDWI' | 'MNDWI' | 'AWEIsh'
var FOLDER = 'Aparri_Landsat_v2';

// ---------------------------------------------------------------- collections (Collection 2, Level 2)
var SENSORS = {
  'LANDSAT/LT04/C02/T1_L2': {name: 'L4', bands: ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']},
  'LANDSAT/LT05/C02/T1_L2': {name: 'L5', bands: ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']},
  'LANDSAT/LE07/C02/T1_L2': {name: 'L7', bands: ['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']},
  'LANDSAT/LC08/C02/T1_L2': {name: 'L8', bands: ['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']},
  'LANDSAT/LC09/C02/T1_L2': {name: 'L9', bands: ['SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']}
};
var NAMES = ['BLUE','GREEN','RED','NIR','SWIR1','SWIR2'];

function prep(id) {
  var cfg = SENSORS[id];
  return function (img) {
    var qa = img.select('QA_PIXEL');
    // bits: 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 5 snow
    var ok = qa.bitwiseAnd(1 << 1).eq(0).and(qa.bitwiseAnd(1 << 2).eq(0))
               .and(qa.bitwiseAnd(1 << 3).eq(0)).and(qa.bitwiseAnd(1 << 4).eq(0));
    return img.select(cfg.bands, NAMES).multiply(0.0000275).add(-0.2).updateMask(ok)
              .set('sensor', cfg.name).copyProperties(img, ['system:time_start', 'CLOUD_COVER']);
  };
}

function scenesFor(year) {
  var y0 = year - WINDOW_YEARS, y1 = year + WINDOW_YEARS;
  var start = ee.Date.fromYMD(y0, 1, 1), end = ee.Date.fromYMD(y1 + 1, 1, 1);
  var cols = Object.keys(SENSORS).map(function (id) {
    return ee.ImageCollection(id).filterBounds(AOI).filterDate(start, end)
      .filter(ee.Filter.calendarRange(MONTHS[0], MONTHS[MONTHS.length - 1], 'month'))
      .filter(ee.Filter.lt('CLOUD_COVER', MAX_CLOUD)).map(prep(id));
  });
  var all = cols[0];
  for (var i = 1; i < cols.length; i++) all = all.merge(cols[i]);
  return all;
}

function indexImage(img) {
  var idx;
  if (INDEX === 'NDWI')   idx = img.normalizedDifference(['GREEN', 'NIR']);
  if (INDEX === 'MNDWI')  idx = img.normalizedDifference(['GREEN', 'SWIR1']);
  if (INDEX === 'AWEIsh') idx = img.expression('B + 2.5*G - 1.5*(N + S1) - 0.25*S2',
      {B: img.select('BLUE'), G: img.select('GREEN'), N: img.select('NIR'), S1: img.select('SWIR1'), S2: img.select('SWIR2')});
  return idx.rename(INDEX);
}

// ---------------------------------------------------------------- per-year composites + bookkeeping
var sceneRows = [];
YEARS.forEach(function (year) {
  var col = scenesFor(year);
  print('IMAGES ' + year + ' (window +/-' + WINDOW_YEARS + ' y, months ' + MONTHS + ')', col.size());
  var comp = col.median();                       // median of the SEASONAL stack
  var idx = indexImage(comp).clip(AOI);
  Map.addLayer(idx, {min: -0.5, max: 0.5, palette: ['8B4513', 'FFFFFF', '0000FF']}, INDEX + ' ' + year, year === 2025);
  Export.image.toDrive({
    image: idx.toFloat(), description: INDEX + '_' + year, folder: FOLDER, fileNamePrefix: INDEX + '_' + year,
    region: AOI, scale: 30, crs: 'EPSG:32651', maxPixels: 1e9
  });
  var feats = col.map(function (im) {
    return ee.Feature(null, {year: year, scene_id: im.get('system:index'),
      date: ee.Date(im.get('system:time_start')).format('YYYY-MM-dd'),
      sensor: im.get('sensor'), cloud_cover: im.get('CLOUD_COVER')});
  });
  sceneRows.push(feats);
});
var scenes = ee.FeatureCollection(sceneRows).flatten();
Export.table.toDrive({collection: scenes, description: 'scenes', folder: FOLDER, fileNamePrefix: 'scenes', fileFormat: 'CSV'});
Map.centerObject(AOI, 12);
print('Done. Check the image count per year (need >= 3), then run the export Tasks.');
