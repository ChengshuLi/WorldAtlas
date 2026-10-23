"""Controls for whole encoded/decoded physical-source custody."""
import hashlib
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import descriptor, deterministic_gzip
from physical_gap_successor import decode_gzip_layers, verify_decoded_relation


class DecodedSourceControls(unittest.TestCase):
    def test_nested_gzip_retains_both_exact_whole_byte_layers(self):
        decoded = b'{ "original": [1.000, true, null] }\n'
        encoded = deterministic_gzip(deterministic_gzip(decoded))
        record = verify_decoded_relation(descriptor('source.gz.gz', encoded), encoded,
                                         descriptor('source.json', decoded), decoded, 2)
        self.assertEqual(record['decoded_sha256'], hashlib.sha256(decoded).hexdigest())
        self.assertEqual(decode_gzip_layers(encoded, 2), decoded)

    def test_truncation_trailing_data_wrong_layer_count_and_changed_decoded_bytes_fail(self):
        decoded = b'complete source bytes\n'
        encoded = deterministic_gzip(decoded)
        with self.assertRaisesRegex(ValueError, 'not a valid gzip|truncated'):
            decode_gzip_layers(encoded[:-2], 1)
        with self.assertRaisesRegex(ValueError, 'trailing bytes'):
            decode_gzip_layers(encoded + b'unclaimed tail', 1)
        with self.assertRaisesRegex(ValueError, 'not a valid gzip'):
            decode_gzip_layers(encoded, 2)
        changed = b'changed source bytes\n'
        with self.assertRaisesRegex(ValueError, 'do not equal'):
            verify_decoded_relation(descriptor('source.gz', encoded), encoded,
                                    descriptor('source.json', changed), changed, 1)

    def test_invalid_gzip_layer_counts_fail_closed(self):
        for layers in [0, -1, 4, True, 1.0]:
            with self.subTest(layers=layers), self.assertRaisesRegex(ValueError, 'layer count'):
                decode_gzip_layers(b'irrelevant', layers)


if __name__ == '__main__':
    unittest.main()
