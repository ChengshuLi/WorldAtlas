-- Allow final land partitions expressed through selected lines and witnesses.
ALTER TABLE atlas.decision_policies DROP CONSTRAINT decision_policies_kind_check;
ALTER TABLE atlas.decision_policies ADD CONSTRAINT decision_policies_kind_check
    CHECK (kind IN ('layer_precedence','overlap','coastline_assignment','scoped_land_partition'));
