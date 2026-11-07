import unittest
from region_worker import normalized_sources


class UralSourceContract(unittest.TestCase):
 def test_raw_part_manifest_survives_worker_normalization(self):
  source={'source_id':'tile','version':'1','kind':'raw','sha256':'a'*64,'bucket':'b','key':'tile/manifest.json','representation':'manifest_of_raw_parts','full_tile_sha256':'b'*64}
  result=normalized_sources([source])[('tile','1')]
  self.assertEqual(result['representation'],'manifest_of_raw_parts')
  self.assertEqual(result['full_tile_sha256'],'b'*64)
  self.assertEqual(result['sha256'],'a'*64)
 def test_incomplete_or_forged_manifest_rejected(self):
  source={'source_id':'tile','version':'1','kind':'raw','sha256':'a'*64,'bucket':'b','key':'tile/manifest.json','representation':'manifest_of_raw_parts'}
  with self.assertRaisesRegex(ValueError,'manifest identity'):normalized_sources([source])
  source['full_tile_sha256']='not-a-hash'
  with self.assertRaisesRegex(ValueError,'manifest identity'):normalized_sources([source])
  source['full_tile_sha256']='b'*64;source['representation']='provider_original'
  with self.assertRaisesRegex(ValueError,'manifest identity'):normalized_sources([source])


if __name__=='__main__':unittest.main()
