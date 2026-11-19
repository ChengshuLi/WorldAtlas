DO $$
DECLARE failed_case text;
BEGIN
 SELECT name INTO failed_case
 FROM (VALUES
  ('empty text', '', false),
  ('whitespace only', E' \t\r\n\f' || chr(11), false),
  ('Unicode whitespace only', U&'\0085\00A0\1680\2001\2028\2029\202F\205F\3000', false),
  ('ordinary text', 'Title', true),
  ('Unicode text with Unicode spaces', U&'\00A0\6771\4EAC\3000', true),
  ('text surrounded by whitespace', E'\tÉvidence\n', true),
  ('null', NULL, NULL::boolean)
 ) AS cases(name, value, expected)
 WHERE atlas.nonblank(value) IS DISTINCT FROM expected
 LIMIT 1;
 IF FOUND THEN RAISE EXCEPTION 'nonblank check failed for %', failed_case; END IF;
END $$;
