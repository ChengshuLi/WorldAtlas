-- psql: pass --set=points='[...]' with the 15 inserted points from the
-- verified local reviewed geometry. No credentials or geographic data here.
-- A pre-existing target revision, a stale source boundary, or a wrong point
-- count aborts the transaction. Full coordinate readback must be compared with
-- the locally generated file after execution.
\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
 IF (SELECT count(*) FROM atlas.decision_mainland_boundaries
     WHERE revision='ural-kara-intersection-20261105'
       AND boundary_id='ural_kara_coast_to_caspian'
       AND geometry_sha256='f4943e118ebc42c746d52444e131818dc02828c15c04697294877914d895f9bb') <> 1
 OR (SELECT count(*) FROM atlas.decision_mainland_boundary_sources
     WHERE revision='ural-kara-intersection-20261105'
       AND boundary_id='ural_kara_coast_to_caspian') <> 11
 THEN RAISE EXCEPTION 'stale Ural source geometry or source links'; END IF;
END $$;
CREATE TEMP TABLE ural_join_points ON COMMIT DROP AS
 SELECT p, i, md5(:'points') AS input_md5 FROM jsonb_array_elements(:'points'::jsonb) WITH ORDINALITY e(p,i);
DO $$ BEGIN
 IF (SELECT count(*) FROM ural_join_points) <> 15 OR
    EXISTS (SELECT 1 FROM ural_join_points WHERE input_md5 <> 'b8e5813b4403e84fff3a4decf3e282f1') THEN
  RAISE EXCEPTION 'geodesic points do not match the verified compact input'; END IF;
END $$;
INSERT INTO atlas.decision_revisions(revision,entity_revision,status,evidence)
 SELECT 'ural-spring-geodesic-20261106',entity_revision,'draft',
 jsonb_build_object('status','User-selected Ural research boundary with WGS84 geodesic spring join; not a complete global revision',
 'previous_revision','ural-kara-intersection-20261105',
 'limitations',jsonb_build_array('Earlier terminal proofs bind the earlier geometry and require rebinding before pipeline use','Coordinate-linear chords approximate the WGS84 geodesic at under 1m station spacing'))
 FROM atlas.decision_revisions WHERE revision='ural-kara-intersection-20261105';
INSERT INTO atlas.decision_mainland_boundaries(revision,boundary_id,method,execution_status,geometry,geometry_sha256,geometry_hash_method,coordinate_reference,provenance)
 SELECT 'ural-spring-geodesic-20261106',b.boundary_id,b.method,b.execution_status,
 jsonb_set(b.geometry,'{coordinates}',g.coords),
 '746e6a85b05e40994e451e49e7df6333b8816dfe1d6624d9c20f9c669e953b32',
 b.geometry_hash_method,b.coordinate_reference,
 (b.provenance - 'candidate_bound_closure_checks' - 'physical_closures' - 'current_construction_status') ||
 jsonb_build_object('selection','user-selected-spring-geodesic-research-boundary',
 'physical_closures','Earlier proofs bind the prior geometry hash and must be revalidated for this revision',
 'spring_geodesic',jsonb_build_object('previous_revision','ural-kara-intersection-20261105',
 'previous_geometry_sha256',b.geometry_sha256,'code_commit','f267f3dde8d6a16737c33e3e4b730bacb2158c68',
 'method','WGS84 geodesic represented by coordinate-linear chords with max 1m station spacing',
 'length_wgs84_m',15.35970455972955,'inserted_vertices',15,'spring_node_id','1385867869'))
 FROM atlas.decision_mainland_boundaries b CROSS JOIN LATERAL
 (SELECT jsonb_agg(v.p ORDER BY v.idx,v.subidx) coords FROM
   (SELECT e.p,e.i AS idx,0 AS subidx FROM jsonb_array_elements(b.geometry->'coordinates') WITH ORDINALITY e(p,i)
    UNION ALL
    SELECT q.p,4746 AS idx,q.i-100 AS subidx FROM ural_join_points q) v) g
 WHERE b.revision='ural-kara-intersection-20261105' AND b.boundary_id='ural_kara_coast_to_caspian'
 AND b.geometry_sha256='f4943e118ebc42c746d52444e131818dc02828c15c04697294877914d895f9bb';
INSERT INTO atlas.decision_mainland_boundary_sources(revision,boundary_id,source_id,source_version,relationship)
 SELECT 'ural-spring-geodesic-20261106',boundary_id,source_id,source_version,relationship
 FROM atlas.decision_mainland_boundary_sources WHERE revision='ural-kara-intersection-20261105'
 AND boundary_id='ural_kara_coast_to_caspian';
DO $$ BEGIN
 IF (SELECT count(*) FROM atlas.decision_mainland_boundaries WHERE revision='ural-spring-geodesic-20261106'
 AND boundary_id='ural_kara_coast_to_caspian' AND jsonb_array_length(geometry->'coordinates')=46430) <> 1
 OR (SELECT count(*) FROM atlas.decision_mainland_boundary_sources WHERE revision='ural-spring-geodesic-20261106'
 AND boundary_id='ural_kara_coast_to_caspian') <> 11 THEN
 RAISE EXCEPTION 'Ural output or source links missing'; END IF;
END $$;
COMMIT;
