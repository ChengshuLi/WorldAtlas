-- Upgrade the existing working database; source imports populate the values.
ALTER TABLE atlas.decision_features ADD COLUMN IF NOT EXISTS geometry jsonb;
ALTER TABLE atlas.decision_features ADD COLUMN IF NOT EXISTS coordinate_reference text;
ALTER TABLE atlas.decision_features DROP CONSTRAINT IF EXISTS decision_features_geometry;
ALTER TABLE atlas.decision_features ADD CONSTRAINT decision_features_geometry CHECK (
  (geometry IS NULL AND coordinate_reference IS NULL) OR
  (geometry IS NOT NULL AND jsonb_typeof(geometry)='object'
   AND geometry ? 'type' AND geometry ? 'coordinates'
   AND coordinate_reference IS NOT NULL AND length(trim(coordinate_reference))>0)
);
