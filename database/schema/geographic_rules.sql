-- Geographic algorithms reference imported geometry and direct-child targets.
CREATE TABLE atlas.geographic_rules (
    id text PRIMARY KEY CHECK (atlas.nonblank(id)),
    parent_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    operation text NOT NULL CHECK (operation IN (
      'assign_area','divide_area','nearest_land','nearest_coastal_water','nearest_basin_water','nearest_water')),
    physical_class text NOT NULL CHECK (physical_class IN ('land','water','mixed')),
    unit text NOT NULL CHECK (unit IN ('cell','component')),
    unassigned_only boolean NOT NULL DEFAULT false,
    rationale text NOT NULL CHECK (atlas.nonblank(rationale)),
    CHECK (operation <> 'nearest_land' OR (physical_class='land' AND unit='component')),
    CHECK (operation NOT IN ('nearest_coastal_water','nearest_basin_water','nearest_water')
           OR (physical_class='water' AND unit='cell'))
);
CREATE TABLE atlas.geographic_rule_features (
    rule_id text NOT NULL REFERENCES atlas.geographic_rules(id) ON DELETE CASCADE,
    feature_id text NOT NULL REFERENCES atlas.source_features(id),
    role text NOT NULL CHECK (role IN ('boundary_line','scope_area','scope_component','distance_reference','connected_to')),
    PRIMARY KEY (rule_id, feature_id, role)
);
CREATE TABLE atlas.geographic_rule_targets (
    id text PRIMARY KEY CHECK (atlas.nonblank(id)),
    rule_id text NOT NULL REFERENCES atlas.geographic_rules(id) ON DELETE CASCADE,
    entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    label_point_id text REFERENCES atlas.source_features(id),
    CONSTRAINT geographic_rule_targets_unique_label
      UNIQUE (rule_id, label_point_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE atlas.geographic_rule_sources (
    rule_id text NOT NULL REFERENCES atlas.geographic_rules(id) ON DELETE CASCADE,
    source_id text NOT NULL REFERENCES atlas.source_assets(id),
    citation_section text NOT NULL CHECK (atlas.nonblank(citation_section)),
    interpretation text NOT NULL CHECK (atlas.nonblank(interpretation)),
    PRIMARY KEY (rule_id, source_id)
);

CREATE FUNCTION atlas.validate_geographic_rule(ident text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE r atlas.geographic_rules%ROWTYPE; lines integer; areas integer;
        components integer; refs integer; targets integer;
BEGIN
  -- Serialize validation without blocking foreign-key references to this rule.
  SELECT * INTO r FROM atlas.geographic_rules WHERE id=ident FOR NO KEY UPDATE;
  IF NOT FOUND THEN RETURN; END IF;
  IF EXISTS (
    SELECT FROM atlas.geographic_rule_features l JOIN atlas.source_features f ON f.id=l.feature_id
    WHERE l.rule_id=r.id AND NOT CASE l.role
      WHEN 'boundary_line' THEN f.geometry->>'type' IN ('LineString','MultiLineString')
      WHEN 'scope_area' THEN f.geometry->>'type' IN ('Polygon','MultiPolygon')
      ELSE f.geometry->>'type'='Point' END
  ) THEN RAISE EXCEPTION 'invalid feature geometry for rule %', r.id; END IF;
  SELECT count(*) FILTER (WHERE role='boundary_line'), count(*) FILTER (WHERE role='scope_area'),
         count(*) FILTER (WHERE role='scope_component'), count(*) FILTER (WHERE role='distance_reference')
  INTO lines,areas,components,refs FROM atlas.geographic_rule_features WHERE rule_id=r.id;
  IF (r.operation='divide_area' AND lines=0) OR (r.operation<>'divide_area' AND lines<>0)
     OR (r.operation='nearest_land' AND refs=0) OR (r.operation<>'nearest_land' AND refs<>0)
     OR (r.operation='nearest_basin_water' AND (areas<>1 OR components<>0)) THEN
    RAISE EXCEPTION 'invalid feature role counts for rule %', r.id;
  END IF;
  SELECT count(*) INTO targets FROM atlas.geographic_rule_targets WHERE rule_id=r.id;
  IF (r.operation='assign_area' AND targets<>1) OR (r.operation='divide_area' AND targets=0)
     OR (r.operation NOT IN ('assign_area','divide_area') AND targets<>0) THEN
    RAISE EXCEPTION 'invalid target count for rule %', r.id;
  END IF;
  IF EXISTS (
    SELECT FROM atlas.geographic_rule_targets t JOIN atlas.geographic_entities e ON e.id=t.entity_id
    LEFT JOIN atlas.source_features p ON p.id=t.label_point_id
    WHERE t.rule_id=r.id AND (
      e.parent_id IS DISTINCT FROM r.parent_id
      OR (r.physical_class<>'mixed' AND e.physical_class<>'mixed' AND e.physical_class<>r.physical_class)
      OR (r.operation='divide_area' AND (t.label_point_id IS NULL OR p.geometry->>'type'<>'Point'))
      OR (r.operation<>'divide_area' AND t.label_point_id IS NOT NULL))
  ) THEN RAISE EXCEPTION 'invalid child target or label point for rule %', r.id; END IF;
  IF EXISTS (SELECT FROM atlas.geographic_entities p WHERE p.id=r.parent_id
             AND r.physical_class<>'mixed' AND p.physical_class<>'mixed' AND p.physical_class<>r.physical_class) THEN
    RAISE EXCEPTION 'rule % has an incompatible parent physical class', r.id;
  END IF;
END $$;

CREATE FUNCTION atlas.check_geographic_rule_links() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE ident text;
BEGIN
  IF TG_TABLE_NAME='geographic_rules' THEN
    PERFORM atlas.validate_geographic_rule(NEW.id);
  ELSIF TG_TABLE_NAME IN ('geographic_rule_features','geographic_rule_targets') THEN
    PERFORM atlas.validate_geographic_rule(NEW.rule_id);
    IF OLD.rule_id IS DISTINCT FROM NEW.rule_id THEN
      PERFORM atlas.validate_geographic_rule(OLD.rule_id);
    END IF;
  ELSIF TG_TABLE_NAME='source_features' THEN
    FOR ident IN
      SELECT rule_id FROM atlas.geographic_rule_features WHERE feature_id=NEW.id
      UNION SELECT rule_id FROM atlas.geographic_rule_targets WHERE label_point_id=NEW.id
    LOOP PERFORM atlas.validate_geographic_rule(ident); END LOOP;
  ELSE
    FOR ident IN
      SELECT id FROM atlas.geographic_rules WHERE parent_id=NEW.id
      UNION SELECT rule_id FROM atlas.geographic_rule_targets WHERE entity_id=NEW.id
    LOOP PERFORM atlas.validate_geographic_rule(ident); END LOOP;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER geographic_rule_check AFTER INSERT OR UPDATE OF id,parent_id,operation,physical_class
ON atlas.geographic_rules DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_geographic_rule_links();
CREATE CONSTRAINT TRIGGER geographic_rule_feature_check AFTER INSERT OR UPDATE OR DELETE
ON atlas.geographic_rule_features DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_geographic_rule_links();
CREATE CONSTRAINT TRIGGER geographic_rule_target_check AFTER INSERT OR UPDATE OR DELETE
ON atlas.geographic_rule_targets DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_geographic_rule_links();
CREATE CONSTRAINT TRIGGER geographic_rule_geometry_check AFTER UPDATE OF geometry
ON atlas.source_features DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
WHEN ((OLD.geometry->>'type') IS DISTINCT FROM (NEW.geometry->>'type'))
EXECUTE FUNCTION atlas.check_geographic_rule_links();
CREATE CONSTRAINT TRIGGER geographic_rule_entity_check AFTER UPDATE OF parent_id,physical_class
ON atlas.geographic_entities DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_geographic_rule_links();
