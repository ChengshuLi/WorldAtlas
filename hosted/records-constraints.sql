-- Append this file to the generated Drizzle base migration.
-- Triggers retain source identity and enforce cross-table evidence contracts.
CREATE TRIGGER atlas_sources_collision BEFORE INSERT ON atlas_sources BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_sources') WHERE EXISTS(SELECT 1 FROM atlas_sources x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.name IS NEW.name AND x.url IS NEW.url AND x.license IS NEW.license AND x.vintage IS NEW.vintage AND x.supported_from IS NEW.supported_from AND x.supported_to IS NEW.supported_to AND x.status IS NEW.status AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_sources_required_text BEFORE INSERT ON atlas_sources BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.license,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.vintage,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_sources_immutable BEFORE UPDATE ON atlas_sources BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_sources_retain BEFORE DELETE ON atlas_sources BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_entity_types_collision BEFORE INSERT ON atlas_entity_types BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_entity_types') WHERE EXISTS(SELECT 1 FROM atlas_entity_types x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.name IS NEW.name AND x.geographic_level IS NEW.geographic_level AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_entity_types_required_text BEFORE INSERT ON atlas_entity_types BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_entity_types_immutable BEFORE UPDATE ON atlas_entity_types BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_entity_types_retain BEFORE DELETE ON atlas_entity_types BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_entities_collision BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_entities') WHERE EXISTS(SELECT 1 FROM atlas_entities x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.kind IS NEW.kind AND x.name IS NEW.name AND x.parent_id IS NEW.parent_id AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.reference_owner IS NEW.reference_owner AND x.is_example IS NEW.is_example AND x.active IS NEW.active AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_entities_required_text BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_entities_retain BEFORE DELETE ON atlas_entities BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_categories_collision BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_categories') WHERE EXISTS(SELECT 1 FROM atlas_categories x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.kind IS NEW.kind AND x.name IS NEW.name AND x.source_id IS NEW.source_id AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_categories_required_text BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_categories_immutable BEFORE UPDATE ON atlas_categories BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_categories_retain BEFORE DELETE ON atlas_categories BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_attribute_records_collision BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_attribute_records') WHERE EXISTS(SELECT 1 FROM atlas_attribute_records x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.location_id IS NEW.location_id AND x.attribute IS NEW.attribute AND x.value IS NEW.value AND x.category_id IS NEW.category_id AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.method IS NEW.method AND x.status IS NEW.status AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_attribute_records_immutable BEFORE UPDATE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_attribute_records_retain BEFORE DELETE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_names_collision BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_names') WHERE EXISTS(SELECT 1 FROM atlas_names x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.entity_id IS NEW.entity_id AND x.name IS NEW.name AND x.language IS NEW.language AND x.role IS NEW.role AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_names_required_text BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.language,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.role,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_names_immutable BEFORE UPDATE ON atlas_names BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_names_retain BEFORE DELETE ON atlas_names BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_relationships_collision BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_relationships') WHERE EXISTS(SELECT 1 FROM atlas_relationships x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.source_entity_id IS NEW.source_entity_id AND x.target_entity_id IS NEW.target_entity_id AND x.relationship_type IS NEW.relationship_type AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_relationships_required_text BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.relationship_type,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_relationships_immutable BEFORE UPDATE ON atlas_relationships BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_relationships_retain BEFORE DELETE ON atlas_relationships BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_media_collision BEFORE INSERT ON atlas_media BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_media') WHERE EXISTS(SELECT 1 FROM atlas_media x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.object_key IS NEW.object_key AND x.sha256 IS NEW.sha256 AND x.bytes IS NEW.bytes AND x.mime IS NEW.mime AND x.name IS NEW.name AND x.license IS NEW.license AND x.attribution IS NEW.attribution AND x.source_id IS NEW.source_id AND x.status IS NEW.status AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_media_required_text BEFORE INSERT ON atlas_media BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.license,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.attribution,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.mime,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_media_retain BEFORE DELETE ON atlas_media BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_media_links_collision BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_media_links') WHERE EXISTS(SELECT 1 FROM atlas_media_links x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.media_id IS NEW.media_id AND x.entity_id IS NEW.entity_id AND x.role IS NEW.role AND x.caption IS NEW.caption AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_media_links_required_text BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.role,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_media_links_immutable BEFORE UPDATE ON atlas_media_links BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_media_links_retain BEFORE DELETE ON atlas_media_links BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_ingestions_collision BEFORE INSERT ON atlas_ingestions BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_ingestions') WHERE EXISTS(SELECT 1 FROM atlas_ingestions x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.fingerprint IS NEW.fingerprint AND x.counts IS NEW.counts));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_ingestions_immutable BEFORE UPDATE ON atlas_ingestions BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
CREATE TRIGGER atlas_ingestions_retain BEFORE DELETE ON atlas_ingestions BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
CREATE TRIGGER atlas_entities_parent BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Invalid adjacent geographic parent') WHERE
 (NEW.kind='continent' AND NEW.parent_id IS NOT NULL) OR
 (NEW.kind IN ('location','province','area','region','subcontinent') AND NOT EXISTS(SELECT 1 FROM atlas_entities p WHERE p.id=NEW.parent_id AND p.kind=CASE NEW.kind WHEN 'location' THEN 'province' WHEN 'province' THEN 'area' WHEN 'area' THEN 'region' WHEN 'region' THEN 'subcontinent' WHEN 'subcontinent' THEN 'continent' END)) OR
 (NEW.kind='settlement' AND NEW.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_entities p WHERE p.id=NEW.parent_id AND p.kind='location')) OR
 (NEW.kind NOT IN ('location','province','area','region','subcontinent','continent','settlement') AND NEW.parent_id IS NOT NULL);
 SELECT RAISE(ABORT,'Entity lifetime exceeds source coverage') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND ((NEW.valid_from IS NOT NULL AND NEW.valid_from<s.supported_from) OR (NEW.valid_to IS NOT NULL AND NEW.valid_to>s.supported_to)));
END;
CREATE TRIGGER atlas_entities_immutable BEFORE UPDATE ON atlas_entities BEGIN SELECT RAISE(ABORT,'Entity changes require an explicit sourced migration; identity is retained'); END;
CREATE TRIGGER atlas_attribute_contract BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute requires a location territory') WHERE NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND e.kind='location');
 SELECT RAISE(ABORT,'Category kind mismatch') WHERE NEW.category_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_categories c WHERE c.id=NEW.category_id AND c.kind=NEW.attribute);
 SELECT RAISE(ABORT,'Overlapping attribute evidence') WHERE EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND r.location_id=NEW.location_id AND r.attribute=NEW.attribute AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Attribute exceeds location lifetime') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
 SELECT RAISE(ABORT,'Uninhabited / unsettled conflicts with settlement attributes') WHERE NEW.method='direct' AND EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND r.location_id=NEW.location_id AND r.method='direct' AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND ((((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='uninhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$')='unsettled') OR (NEW.attribute='population' AND NEW.method='direct' AND NEW.status='sourced' AND EXISTS(SELECT 1 FROM atlas_sources zero_source WHERE zero_source.id=NEW.source_id AND zero_source.status NOT IN ('estimate','example')) AND json_extract(NEW.value,'$')=0 AND coalesce(json_extract(NEW.metadata,'$.estimate'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_attributes'),0)=0 AND (json_type(NEW.metadata,'$.rounding') IS NULL OR json_type(NEW.metadata,'$.rounding')='null') AND (json_type(NEW.metadata,'$.model') IS NULL OR json_type(NEW.metadata,'$.model')='null') AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%approx%')) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='inhabited') OR (r.attribute='rank' AND json_extract(r.value,'$') IN ('rural settlement','town','city','metropolis')) OR (r.attribute='population' AND json_extract(r.value,'$')>0))) OR (((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='inhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$') IN ('rural settlement','town','city','metropolis')) OR (NEW.attribute='population' AND json_extract(NEW.value,'$')>0)) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='uninhabited') OR (r.attribute='rank' AND json_extract(r.value,'$')='unsettled') OR (r.attribute='population' AND r.method='direct' AND r.status='sourced' AND EXISTS(SELECT 1 FROM atlas_sources zero_source WHERE zero_source.id=r.source_id AND zero_source.status NOT IN ('estimate','example')) AND json_extract(r.value,'$')=0 AND coalesce(json_extract(r.metadata,'$.estimate'),0)=0 AND coalesce(json_extract(r.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(r.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(r.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(r.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(r.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_attributes'),0)=0 AND (json_type(r.metadata,'$.rounding') IS NULL OR json_type(r.metadata,'$.rounding')='null') AND (json_type(r.metadata,'$.model') IS NULL OR json_type(r.metadata,'$.model')='null') AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%approx%')))));
END;
CREATE TRIGGER atlas_names_contract BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Overlapping preferred names') WHERE NEW.role='preferred' AND EXISTS(SELECT 1 FROM atlas_names n WHERE n.id!=NEW.id AND n.entity_id=NEW.entity_id AND n.language=NEW.language AND n.role='preferred' AND n.is_example=NEW.is_example AND n.valid_from<NEW.valid_to AND n.valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Name exceeds entity lifetime') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
CREATE TRIGGER atlas_media_immutable BEFORE UPDATE ON atlas_media BEGIN SELECT RAISE(ABORT,'Registered media is immutable; new content needs a new digest and identity'); END;
CREATE TRIGGER atlas_attribute_records_source_interval BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
CREATE TRIGGER atlas_names_source_interval BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
CREATE TRIGGER atlas_relationships_source_interval BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
CREATE TRIGGER atlas_media_links_source_interval BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
CREATE TRIGGER atlas_attribute_records_example_source BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
CREATE TRIGGER atlas_names_example_source BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
CREATE TRIGGER atlas_relationships_example_source BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
CREATE TRIGGER atlas_attribute_nonempty BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute scalar must not be blank') WHERE json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$'),char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER atlas_relationships_entity_lifetime BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Relationship exceeds known entity lifetime') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.source_entity_id,NEW.target_entity_id) AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
CREATE TRIGGER atlas_media_links_entity_lifetime BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Media link exceeds known entity lifetime') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
CREATE TRIGGER atlas_categories_entity_kind BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Category must share a matching graph identity') WHERE NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.id AND e.kind=CASE NEW.kind WHEN 'owner' THEN 'polity' ELSE NEW.kind END);
END;
CREATE TRIGGER atlas_entities_example_source BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Example entity source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
CREATE TRIGGER atlas_attribute_example_identity BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.is_example=1 AND (e.id=NEW.location_id OR e.id=NEW.category_id));
END;
CREATE TRIGGER atlas_names_example_identity BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND e.is_example=1);
END;
CREATE TRIGGER atlas_relationships_example_identity BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.source_entity_id,NEW.target_entity_id) AND e.is_example=1);
END;
CREATE TRIGGER atlas_media_links_example BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Example media must stay opt-in') WHERE NEW.is_example=0 AND (EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example') OR EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND e.is_example=1) OR EXISTS(SELECT 1 FROM atlas_media m JOIN atlas_sources s ON s.id=m.source_id WHERE m.id=NEW.media_id AND s.status='example'));
END;
CREATE TRIGGER atlas_attribute_source_class BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Source class must match evidence method') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND ((s.status='reference' AND NEW.method!='reference') OR (s.status='estimate' AND NEW.method!='estimate')));
END;
