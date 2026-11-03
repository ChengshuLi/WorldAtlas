-- Preserve single-continent named basins; shared-nearest basins need at least two participants.
CREATE OR REPLACE FUNCTION atlas.guard_decision_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP = 'INSERT' THEN
   IF NEW.status <> 'draft' THEN RAISE EXCEPTION 'decision revision must start as draft'; END IF;
   RETURN NEW;
 END IF;
 IF OLD.status <> 'draft' THEN RAISE EXCEPTION 'closed decision revisions are immutable'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 IF NEW.status = 'accepted' THEN
   IF NOT EXISTS (SELECT 1 FROM atlas.entity_registry_revisions WHERE revision = NEW.entity_revision AND status = 'accepted') THEN
     RAISE EXCEPTION 'accepted decisions require an accepted entity registry';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_basins b WHERE b.revision = NEW.revision AND
     (SELECT count(*) FROM atlas.decision_basin_participants p WHERE p.revision=b.revision AND p.basin_id=b.basin_id) < CASE WHEN b.method = 'shared_nearest_assigned_shore' THEN 2 ELSE 1 END) THEN
     RAISE EXCEPTION 'basin has too few participants for its method';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_basin_participants p WHERE p.revision=NEW.revision AND
     (SELECT count(*) FROM atlas.review_category_bindings b WHERE b.revision=p.entity_revision AND b.entity_id=p.entity_id AND b.physical_class='water') <> 1) THEN
     RAISE EXCEPTION 'basin participant requires one water binding';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_routes r WHERE r.revision = NEW.revision AND
     ((SELECT count(*) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) < 2 OR
      (SELECT min(ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) <> 0 OR
      (SELECT max(ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) <>
      (SELECT count(*) - 1 FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id))) THEN
     RAISE EXCEPTION 'each route requires contiguous points starting at zero';
   END IF;
 END IF;
 RETURN NEW;
END $$;
