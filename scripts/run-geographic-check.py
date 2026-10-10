"""Read-only trusted geography check; proposed commits are data, never code."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import tempfile
import gzip

MAX_BYTES = 32 * 1024 * 1024
TRUSTED_PATHS = ['scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
                 'scripts/check-effective-geographic-regression.mjs', 'src/ownership-codec.js',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
                 'scripts/ellipsoidal_area.py', 'requirements.txt',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs']
PIN_PATHS = ['data/hierarchy.json', 'data/canonical-grid/manifest.json',
             'data/geographic-releases/index.json', 'data/geographic-releases/current-manifest.json']

# One independently reviewed code-only transition. This table is trusted code,
# never a candidate-supplied exemption. The author identity manifest is installed
# by this bootstrap, leaving exactly30 support changes for the subsequent PR.
LINUX_SUPPORT_REFERENCE_BASE = 'c28077da970ae39550e5edea790a266b060d3de5'
LINUX_SUPPORT_REFERENCE_HEAD = '11153922e5e2a0d73b874a29d2300f28a5135bf5'
LINUX_SUPPORT_REFERENCE_SHA256 = 'ae94c33f7923a04648bb7da080c61fffef67cbe7f966127fc9869e3863d468ca'
LINUX_SUPPORT_DELTA_SHA256 = '556a966f64dbaa2a2be1b8cf5ec1d134f5fdd62a20e52633ac84e15077accda7'
LINUX_SUPPORT_VECTOR_SHA256 = '4ba0e3b564611248d428613c33bd60cf68a99233f2db572f3893a7d46dda429a'
LINUX_SUPPORT_MANIFEST = 'coordination/engineering/melanesia363-additive-delivery-20261010/evidence-quality.json'
LINUX_SUPPORT_REFERENCE = [{'after': {'bytes': 3495,
            'git_blob_oid': 'f4c3d65ebb1b9ff8e00b7c29cb866b0714e1e7fb',
            'mode': '100644',
            'sha256': '75eb2ded78e5da3ed8cce99447272823afde9f1c0ab87496597555dde68f77dd'},
  'before': {'bytes': 3415,
             'git_blob_oid': 'f67de8f57a88046dd42c369f44358f240f94d7af',
             'mode': '100644',
             'sha256': '519d329f2d5c3e0ab7aef2f7de208ec3b33c7b1e527aaedf3c483537646390bb'},
  'path': 'coordination/engineering/additive-native-composition-20261009/cold-entry-controls.mjs'},
 {'after': {'bytes': 6212,
            'git_blob_oid': '5a5f4e483d0ef8ea93a91bc17a6e997346bb694f',
            'mode': '100644',
            'sha256': 'cb83513e3afdf502c79ae431e86d1c3879db40ff4089c399634d39d0a0301b48'},
  'before': {'bytes': 3941,
             'git_blob_oid': 'cf0507c510097160d6eb7a43fa7d1132a3ecffe4',
             'mode': '100644',
             'sha256': 'b09c4c48f383d8cf298f882108dab4f75cbe7d168581ed20c81f859379d1e5b5'},
  'path': 'coordination/engineering/additive-native-composition-20261009/external-execution-controls.py'},
 {'after': {'bytes': 23671,
            'git_blob_oid': 'a9c034d4e13fa71be5f3c85247ab56be3ba83f23',
            'mode': '100644',
            'sha256': '37d6e02607204302fc01c5d3d6652c89a937e5e84acaa71fb25f5ddc7bcdf5e8'},
  'before': {'bytes': 4199,
             'git_blob_oid': 'e14112b8c5b15e8a1135cc6021c832d1f43e7dc2',
             'mode': '100644',
             'sha256': '4320d550b8f1dbe333feb6a47608da0d001394cc14d1ae194a66e2054d089536'},
  'path': 'coordination/engineering/additive-native-composition-20261009/issue-current-rebind-execution.py'},
 {'after': {'bytes': 9308,
            'git_blob_oid': '9f8ccb88163e5dc5a77db46d1c0ac27b3fbce29e',
            'mode': '100644',
            'sha256': 'f10f371b186398fa4822987189f7f02b7b4b30dfb50b75213ebe20e8ea255ad4'},
  'before': {'bytes': 1584,
             'git_blob_oid': '3d4cc021c97927f35f77c21f939a817608e79dab',
             'mode': '100644',
             'sha256': '142deb7cde69b752d5269d589b3d7db6f0ad109df9b665f504bd6bb709239f8e'},
  'path': 'coordination/engineering/additive-native-composition-20261009/launch-failure-controls.py'},
 {'after': {'bytes': 7770,
            'git_blob_oid': 'a179d10a9b8af82d05e4fe3270709edeb67e34b8',
            'mode': '100644',
            'sha256': '8e8ba762b57104bd535b278e034e53971d663d8bdebd622c3d06a692d978d936'},
  'before': {'bytes': 3158,
             'git_blob_oid': '1e16062479b2b655825f001677ee38f6d7dc2ab6',
             'mode': '100644',
             'sha256': 'a944fd1a511f693342fcf6b4e355f91408c4efb48d43f0df64f5d6428a0e5b65'},
  'path': 'coordination/engineering/additive-native-composition-20261009/operating-order-controls.py'},
 {'after': {'bytes': 20660,
            'git_blob_oid': 'e1a19f502fe2a975a833c75fe6d50457c0ffc682',
            'mode': '100644',
            'sha256': '5be26c44ef36a097a24c82dab89a91693c94065278f5e15aeb57b0d295755345'},
  'before': {'bytes': 11664,
             'git_blob_oid': '6ae72957b160128072864e7f73d33a8debbf9c71',
             'mode': '100644',
             'sha256': 'eda97761561ed61b5fdb4f1a0bfe3b94a440ff625bf8c1780934a6bbede780ea'},
  'path': 'coordination/engineering/additive-native-composition-20261009/supervise-current-rebind.py'},
 {'after': {'bytes': 10042,
            'git_blob_oid': 'acd1bb9c13981849c59ac1173ab66d9958b0192d',
            'mode': '100644',
            'sha256': '7f8628dbbdb2a84eed0877a461f4cb164d11cfa2770b979cf305647e667e566b'},
  'before': {'bytes': 10036,
             'git_blob_oid': '738ff646346304371249e576e561f19d27ae9947',
             'mode': '100644',
             'sha256': '15c2b405e08435b05e0f12e66c52d7ed263e04f17c792c8e9ead95133c82a83e'},
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-rebind-controls.mjs'},
 {'after': {'bytes': 6959,
            'git_blob_oid': '91d6fbbb4a4e04f38dd9d6decaa6f05ddd0de542',
            'mode': '100644',
            'sha256': 'a10b661c7ae9db0b6c89e400bc257267e1325a52a550fe899a8fb93e0b4eca34'},
  'before': {'bytes': 5247,
             'git_blob_oid': '4757e98fe62680014e1cb8332912bc66e4f70402',
             'mode': '100644',
             'sha256': 'e7154b7b3dc352adcc5196773396c3d5c9563ceefa8a4692fe816ca1040cc816'},
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/execution-custody-controls.mjs'},
 {'after': {'bytes': 3326,
            'git_blob_oid': '8c5ce810230115f48cbe8a8917f5b22cd740a4e9',
            'mode': '100644',
            'sha256': '21bb7cd87e248f7ba11a1f3784f9c3d949e2e8b7b32ff4e1b84d1628551b1301'},
  'before': {'bytes': 3166,
             'git_blob_oid': '4a7614b11b75b2288d8c0b9b8e484de42d4342a2',
             'mode': '100644',
             'sha256': 'b5e34cfb4926f389e35bb4c75f3ad0a7a2e9623a3c6c1e77428dda280abd3e35'},
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/execution-custody-fixture.mjs'},
 {'after': {'bytes': 6568,
            'git_blob_oid': 'dd984491ba4551a3ff1609861c39184cd65b596f',
            'mode': '100644',
            'sha256': '7d400ef0e4d8c1e82e469f5e08731b202d067690ce39bd1ba899b46f6f07b20e'},
  'before': {'bytes': 6572,
             'git_blob_oid': 'aa1f7b4f11bb9f5b1b4657ca1df3d3188c1dcbb1',
             'mode': '100644',
             'sha256': 'd24d8fbe7a5113931bb3d2bd45d4c4f563ff55744f8b4e1b4bb4c862e457e908'},
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/rebind-reader-controls.mjs'},
 {'after': {'bytes': 122375,
            'git_blob_oid': 'abc5f53abb2a6419f8aef268a57b9fdc5721ff7c',
            'mode': '100644',
            'sha256': '6e9f4c5e1756f95950f1b6d7d9cf082fbd2caac3f5be3d5a788ef7d7808ba299'},
  'before': {'bytes': 122375,
             'git_blob_oid': '4b51b6d6e62c49cb7036d3c96d630f5789e66e2b',
             'mode': '100644',
             'sha256': 'f827929d6cca4b6360949a9a3f15596f5bee42a0c44276df9955ad8f0df445a0'},
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/evidence-quality.json'},
 {'after': {'bytes': 5620,
            'git_blob_oid': '2fc6ce092018a4bda934921c5f7289c7d4623d01',
            'mode': '100644',
            'sha256': 'f31ef60b5dd653db5d835f00d82a7e6c9e8b68c48f95b6fabb93b4d08261c1c5'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/README.md'},
 {'after': {'bytes': 5340,
            'git_blob_oid': 'bb7c7f6992f3a4eb3d1e8ced21d301ab006b2673',
            'mode': '100644',
            'sha256': '30c9edf68c3f1853dcce78c13e6ecd2a11ca94edccb06f15e208e5c3248977a5'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/capture.jsonl'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/capture.stderr'},
 {'after': {'bytes': 311,
            'git_blob_oid': 'c41593e9cc1d55157a6c9e32cb8c6b47398cfd69',
            'mode': '100644',
            'sha256': 'a854b6951920e4edd62438e2b89c7283bfb783ca223721e21471a342c8e4b6da'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/cold-entry.json'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/cold-entry.stderr'},
 {'after': {'bytes': 14998,
            'git_blob_oid': 'dc1d118df20dc051190dc3403ff5fa9c772f1c03',
            'mode': '100644',
            'sha256': 'd12e8232139c62a8d84ae1e3438d5ea12610ba67619be5d315aaaa2b5122ad1a'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/external-runtime.json'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/external-runtime.stderr'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/focused-additive.stderr'},
 {'after': {'bytes': 1599,
            'git_blob_oid': '19e2cea5573907a1ca216d5eecdf7ebfc3f7f28f',
            'mode': '100644',
            'sha256': '819777a15cba06a91f6fecfe74cf43b2824d1fd2cd3d2c569c7f858eb30ebca5'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/focused-additive.tap'},
 {'after': {'bytes': 10697,
            'git_blob_oid': '4270ed41ca36cc41259feb2ecea0edd62a5369c9',
            'mode': '100644',
            'sha256': 'cc432d7ce123e3da12a1eb5c427cf117a92e482432888da948b30941a84a38bc'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/gnu-custody.jsonl'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/gnu-custody.stderr'},
 {'after': {'bytes': 27426,
            'git_blob_oid': 'd02c682483f6fd540062d3ca4a6834206663f942',
            'mode': '100644',
            'sha256': '31f50a5481830b369f2fa3e23267db8be0858a05af53be0c078aab38c3cc840d'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/immutable-reader.jsonl'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/immutable-reader.stderr'},
 {'after': {'bytes': 620,
            'git_blob_oid': '5b2b36788ba6f8e9bf3160b4695b2da7540658e6',
            'mode': '100644',
            'sha256': 'd9f26aab0d4f4249d40b4a07ab3f81d08931ccfa2072b84b79e0b2c52bb1bd68'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/launch-cleanup.json'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/launch-cleanup.stderr'},
 {'after': {'bytes': 472,
            'git_blob_oid': 'd0c569ad9793b127c107e8208ab3c163e3a57cc9',
            'mode': '100644',
            'sha256': 'fb5f428b21ff501fc622054f9b5c1ebfba215ec60a2d8664c4d5cbe0ac958679'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/operating-order.json'},
 {'after': {'bytes': 0,
            'git_blob_oid': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'mode': '100644',
            'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/controls-20261010T2153Z/operating-order.stderr'},
 {'after': {'bytes': 40034,
            'git_blob_oid': '99d2676e7aa5230bcb4ece6bf8fd2fef48d6ca6f',
            'mode': '100644',
            'sha256': 'fcdef8074e30f7981d6089c59768e118a00ce0c419568e06685b313a4e31388b'},
  'before': None,
  'path': 'coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/historical-code-vectors.json'},
 {'after': {'bytes': 180040,
            'git_blob_oid': 'e271775ffc9d1862ecc77d0c8f9882dec34a06a9',
            'mode': '100644',
            'sha256': '7135f0e2b72419c40542169d9806335eb1b1bd86149894fb6eacda531b41e4b4'},
  'before': {'bytes': 175564,
             'git_blob_oid': '72eb0503a740155e326c99fdfde7f7e77e37357b',
             'mode': '100644',
             'sha256': 'e32bde2be56b5c8002248eac7eedb5fd7c83b8ced46015778c6eb2145dcda44a'},
  'path': 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'},
 {'after': {'bytes': 22077,
            'git_blob_oid': '8acc140c046d7186442718c84ba227b456d1b234',
            'mode': '100644',
            'sha256': '1b2485775d8a48e2092004ccee058ea7e3462e48fb6dd39b5bad277936d663b2'},
  'before': {'bytes': 17984,
             'git_blob_oid': '52767ad65dbf5fdcb2c7be2a5ed6125eff747f5d',
             'mode': '100644',
             'sha256': '259f38dc95c810fe2ed629ce06f23fd56d56ba29f940bf517e8455f0f5f8ec6e'},
  'path': 'test/additive-gap-repair.test.mjs'}]
LINUX_SUPPORT_OLD_VECTOR = [{'bytes': 2279,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
  'sha256': 'f4d5480d23ba6ae097a559d066b2a244ce388ba81aa6c486331e731be23e1813'},
 {'bytes': 242,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-geometry.mjs',
  'sha256': '704b8a224f09943b4290d0c39514c480d041de946683253f36ef86dcf4f92f7c'},
 {'bytes': 317,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-rebind.mjs',
  'sha256': 'a0aecb8720ff295df16e5bef6bb5f527ed002380c6cb64a514242f79614c8cb0'},
 {'bytes': 175564,
  'path': 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
  'sha256': 'e32bde2be56b5c8002248eac7eedb5fd7c83b8ced46015778c6eb2145dcda44a'},
 {'bytes': 45330,
  'path': 'src/effective-footprint.js',
  'sha256': '28edb52a2befd80b73e0ce62fa3f7de51cada4f9894aab32e5ff2761f1fe0745'},
 {'bytes': 75074,
  'path': 'scripts/check-effective-geographic-regression.mjs',
  'sha256': '801ad9f05a8d7f34ae591ee78a09b71c87090acd4d20c92c9831152528a9c039'},
 {'bytes': 2948,
  'path': 'src/ownership-codec.js',
  'sha256': '64630f340a2815d5c86706cc4456718054990083d1026e0b420dd8f9f02f593d'},
 {'bytes': 1417, 'path': 'package.json', 'sha256': '2af9169f046047a5cbc14592bdd776740d1b6e2871ec8216fa4a0b5e52b739a3'},
 {'bytes': 3497,
  'path': 'src/native-runtime.js',
  'sha256': '988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600'},
 {'bytes': 4472,
  'path': 'scripts/native-ownership/compile-native-ownership.mjs',
  'sha256': '2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378'},
 {'bytes': 6408,
  'path': 'src/native-grid.js',
  'sha256': 'b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663'},
 {'bytes': 2799,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/package.json',
  'sha256': 'ceb30ba96a14786c419db53f2b8d3d59ece7ac5221c198ac03def462cf96ef23'},
 {'bytes': 16773,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/sha2.js',
  'sha256': '3ddc587c588283cbceed4dd9929cefcce06a0c231b54d4c6f0f99c478c686c00'},
 {'bytes': 5615,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/_md.js',
  'sha256': 'a112f0fe1b15db00f2638618c436a17be1c5e13baf19d02fcc29016ae1db2233'},
 {'bytes': 3081,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/_u64.js',
  'sha256': 'e48c0cfc10810439a4807b46db136ce603a3fa09b62584f513ef2f3ca496af54'},
 {'bytes': 9356,
  'path': 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/utils.js',
  'sha256': '11319ec0a8132a0c2ced8c98af33ae9274c001d6baf4f4709c4a6115e031a3c5'},
 {'bytes': 6777,
  'path': 'scripts/audit-grid-intervals.mjs',
  'sha256': '084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9'},
 {'bytes': 15017,
  'path': 'coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs',
  'sha256': '63f50c081b5439a8030a1d431ec9feb10bc36e58efc56f45315c87fa58765b8e'},
 {'bytes': 7729,
  'path': 'coordination/engineering/additive-native-composition-20261009/run-current-rebind.mjs',
  'sha256': '7132d5f16c779586a5475ddc2a3205a5fdd537a93feec6c3beeab1dffc984f8f'},
 {'bytes': 4199,
  'path': 'coordination/engineering/additive-native-composition-20261009/issue-current-rebind-execution.py',
  'sha256': '4320d550b8f1dbe333feb6a47608da0d001394cc14d1ae194a66e2054d089536'},
 {'bytes': 11664,
  'path': 'coordination/engineering/additive-native-composition-20261009/supervise-current-rebind.py',
  'sha256': 'eda97761561ed61b5fdb4f1a0bfe3b94a440ff625bf8c1780934a6bbede780ea'},
 {'bytes': 3169,
  'path': 'coordination/engineering/additive-native-composition-20261009/execution-contract.py',
  'sha256': '8bdc08d55830a7a3d95bce5ad20044f0ce5de08bcd5e514b51570bd19e8b114a'},
 {'bytes': 2201,
  'path': 'coordination/engineering/additive-native-composition-20261009/owned-group-original.py',
  'sha256': '9ac8aeca9c721968bf33e69e219dbfb103875263b994dff1bd2e94402d0750ce'},
 {'bytes': 2596,
  'path': 'coordination/engineering/additive-native-composition-20261009/owned-child-termination-original.py',
  'sha256': '00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61'},
 {'bytes': 22001,
  'path': 'coordination/engineering/additive-native-composition-20261009/mac-execution-runtime-original.json',
  'sha256': '3b4c62732d123b00c436f724387f3fec67390b205223561b70787b0e2d44d4f5'},
 {'bytes': 2197,
  'path': 'coordination/engineering/additive-native-composition-20261009/execution-code-paths.json',
  'sha256': '9173f3eb7a6c9dfe6c6aaf4524229db6c7caec296a09ed41347b0c43c6145708'},
 {'bytes': 13365,
  'path': 'scripts/local-workspace.mjs',
  'sha256': '74c390efa3360b4431d047f89ab99986da697e58716000f44a4b284760e2a373'},
 {'bytes': 548,
  'path': 'scripts/worker-identity.mjs',
  'sha256': 'e31ef3d286c3250f7f69e23f455edd896cfa96b8eb6438026aa4374da57128bd'}]


def immutable_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{40}', value):
        raise ValueError('Require exact immutable baseline and candidate commits')
    return value


def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value or any(p in ['', '.', '..'] for p in value.split('/')):
        raise ValueError('Unsafe geography input path')
    return value


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args], stderr=subprocess.PIPE)


def entry(repo, commit, name):
    name = safe_path(name)
    row = git(repo, 'ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
    if not row.startswith(('100644 ', '100755 ')) or row[row.find('\t'):] != '\t' + name:
        raise ValueError('Geography input must be an ordinary Git file: ' + name)
    blob = row.split()[2]
    return {'path': name, 'mode': row.split()[0], 'git_blob_oid': blob}


def read(repo, commit, name):
    blob = entry(repo, commit, name)['git_blob_oid']
    if int(git(repo, 'cat-file', '-s', blob)) > MAX_BYTES:
        raise ValueError('Geography input exceeds bounded file size: ' + name)
    return git(repo, 'cat-file', 'blob', blob)


def inventory(repo, commit):
    index = json.loads(read(repo, commit, 'data/world-index.json'))
    parts = index.get('parts')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 512 or len(set(parts)) != len(parts):
        raise ValueError('Invalid or incomplete live geography part inventory')
    names = ['data/world-index.json', *PIN_PATHS, *['data/' + safe_path(p) for p in parts]]
    pointer = json.loads(read(repo, commit, PIN_PATHS[-1]))
    if not isinstance(pointer, dict) or not re.fullmatch('[a-f0-9]{64}', pointer.get('sha256', '')):
        raise ValueError('Invalid geographic release pointer')
    pointed = safe_path(pointer.get('path'))
    if not pointed.startswith('data/'):
        pointed = 'data/geographic-releases/' + pointed
    if hashlib.sha256(read(repo, commit, pointed)).hexdigest() != pointer['sha256']:
        raise ValueError('Geographic release pointer hash mismatch')
    names.append(pointed)
    return [entry(repo, commit, name) for name in sorted(set(names))]


def verify_trusted_checkout(repo, baseline):
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != baseline:
        raise ValueError('Checker checkout must be the exact trusted baseline commit')
    # Verify the complete local scripts namespace, including package absence.
    # A byte-correct geometry.py is insufficient if an untracked evidence.py,
    # package initializer, extension module or cached bytecode can shadow it.
    expected = {}
    for row in git(repo, 'ls-tree', '-r', '-z', baseline, '--', 'scripts', 'src').decode().split('\0'):
        if not row:
            continue
        fields, name = row.split('\t', 1)
        if fields.split()[0] not in ['100644', '100755']:
            raise ValueError('Trusted scripts must be ordinary committed files')
        expected[name] = fields.split()[2]
    actual = {}
    for namespace in ['scripts', 'src']:
        if (repo / namespace).is_symlink():
            raise ValueError('Trusted scripts namespace cannot contain symlinks')
        for target in (repo / namespace).rglob('*'):
            if target.is_symlink():
                raise ValueError('Trusted scripts namespace cannot contain symlinks')
            if target.is_file():
                actual[str(target.relative_to(repo))] = target
    if set(actual) != set(expected):
        raise ValueError('Untracked or missing file in trusted scripts namespace')
    for name, target in actual.items():
        if target.read_bytes() != git(repo, 'cat-file', 'blob', expected[name]):
            raise ValueError('Checker differs from immutable trusted baseline: ' + name)
    for name in ['requirements.txt', 'package.json', '.github/evidence-policy.json', *[p for p in TRUSTED_PATHS if p.startswith('coordination/')]]:
        target = repo / name
        if any(path.is_symlink() for path in [target, *target.parents]) or not target.is_file() or target.read_bytes() != read(repo, baseline, name):
            raise ValueError('Trusted dependency metadata or evidence policy differs from baseline')
        expected[name] = entry(repo, baseline, name)['git_blob_oid']
    return hashlib.sha256((json.dumps(expected, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()


def compare_effective_primitives(detector, before, after, additions, base_hashes=None):
    """Literal BASE OR complete ADDITION sets; never persist a dissolved polygon.

    Original prepare/compare operates on each unchanged complete primitive.
    Multiple primitives with one stable owner are one ownership set, so their
    internal intersections are not competing-location overlap. Coverage-loss
    findings are never filtered. The original geometry routines stay literal.
    """
    if not any(additions.values()):
        return detector.compare(before, after)
    owners, primitives = {}, {}
    for vintage, features in [('baseline', before), ('candidate', after)]:
        values = {}
        for identity, feature in features.items():
            key = json.dumps([identity, 'base'], ensure_ascii=False, separators=(',', ':'))
            owners[key] = identity
            values[key] = {**feature, 'id': key}
        seen = set()
        for row in additions[vintage]:
            identity, component = row['target_id'], row['component_id']
            if identity not in features:
                continue  # Whole additions outside the certified affected set.
            if component in seen or row['base_geometry_sha256'] != (base_hashes[vintage][identity] if base_hashes is not None else detector.geometry_hash(features[identity])):
                raise ValueError('Foreign/duplicate/stale complete effective primitive')
            seen.add(component)
            key = json.dumps([identity, component], ensure_ascii=False, separators=(',', ':'))
            if key in values:
                raise ValueError('Effective primitive identity collision')
            owners[key] = identity
            values[key] = {'type': 'Feature', 'id': key, 'properties': {'id': key}, 'geometry': row['geometry']}
        primitives[vintage] = values
    result = detector.compare(primitives['baseline'], primitives['candidate'])
    changed = sorted({owners[key] for key in result['changed_location_ids']})
    findings = []
    for feature in result['findings']['features']:
        props = feature['properties']
        identities = sorted({owners[key] for key in props['location_ids']})
        if props['kind'] == 'new-pair-overlap' and len(identities) == 1:
            continue
        props['location_ids'] = identities
        props['changed_location_ids'] = sorted(set(identities) & set(changed))
        for vintage in ['before', 'after']:
            for row in props[vintage]:
                row['primitive_id'] = row['location_id']
                row['location_id'] = owners[row['location_id']]
        findings.append(feature)
    for feature in result['coverage_gained']['features']:
        props = feature['properties']
        props['location_ids'] = sorted({owners[key] for key in props['location_ids']})
        props['changed_location_ids'] = sorted(set(props['location_ids']) & set(changed))
        for vintage in ['before', 'after']:
            for row in props[vintage]:
                row['primitive_id'] = row['location_id']
                row['location_id'] = owners[row['location_id']]
    for error in result['geometry_errors']:
        error['primitive_id'] = error['location_id']
        error['location_id'] = owners[error['location_id']]
    result['changed_primitive_ids'] = result['changed_location_ids']
    result['changed_location_ids'] = changed
    result['affected_neighbor_ids'] = sorted({owners[key] for key in result['affected_neighbor_ids']} - set(changed))
    result['findings']['features'] = findings
    if result['regressions'] is not None:
        result['regressions'] = len(findings)
        result['status'] = 'regressions-found' if findings else 'no-new-regression'
    result['effective_set_domain'] = 'literal-base-or-complete-additions:v2'
    return result


def selected_continuous(repo, baseline, candidate, detector):
    import sys
    env = dict(os.environ)
    for name in ['NODE_OPTIONS', 'NODE_PATH']:
        env.pop(name, None)
    executable = os.environ.get('NODE', 'node')
    entrypoint = repo / 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'
    with tempfile.TemporaryDirectory(prefix='trusted-selected-footprints-') as temporary:
        destination = pathlib.Path(temporary).resolve() / 'complete'
        raw = subprocess.check_output([executable, str(entrypoint), 'continuous', str(repo), baseline,
                                      baseline, candidate, str(destination), sys.executable], env=env, stderr=subprocess.PIPE)
        if len(raw) > MAX_BYTES:
            raise ValueError('Cold selected acknowledgement exceeds output cap')
        issued = json.loads(raw)
        if issued.get('candidate_code_executed') is not False or issued.get('kind') != 'trusted-selected-continuous-comparison-v1':
            raise ValueError('Unsupported selected continuous acknowledgement')
        if issued.get('status') == 'selected-sources-unchanged':
            return issued
        publication = issued.get('publication')
        if not isinstance(publication, dict) or publication.get('complete') is not True:
            raise ValueError('Selected continuous source operands lack complete issued publication')
        names = ['publication.json', publication['facts']['path'], publication['operands']['path']]
        pins = [None, publication['facts'], publication['operands']]
        total = 0
        for name, pin in zip(names, pins):
            if safe_path(name) != pathlib.Path(name).name:
                raise ValueError('Foreign selected output path')
            target = destination / name
            stat = target.lstat()
            if target.is_symlink() or not target.is_file() or stat.st_mode & 0o777 != 0o644 or stat.st_size > MAX_BYTES:
                raise ValueError('Nonordinary whole selected output')
            if pin is not None and (stat.st_size != pin['bytes'] or pin.get('decoded_bytes', 0) > MAX_BYTES):
                raise ValueError('Whole selected output size exceeds original bound')
            total += stat.st_size + (pin.get('decoded_bytes', 0) if pin else 0)
        # Node has terminated. This is the actual Python consumer phase, with
        # complete encoded+decoded operands and retained output/code allowance.
        runtime_bytes = pathlib.Path(sys.executable).resolve().stat().st_size
        code_bytes = sum((repo / name).stat().st_size for name in TRUSTED_PATHS)
        if total + runtime_bytes + code_bytes + 2 * MAX_BYTES > 256 * 1024 * 1024:
            raise ValueError('Complete selected polygon consumer phase exceeds prospective cap')
        bodies = []
        for name, pin in zip(names, pins):
            body = (destination / name).read_bytes()
            if pin is not None and (len(body) != pin['bytes'] or hashlib.sha256(body).hexdigest() != pin['sha256']):
                raise ValueError('Whole selected output differs from issued trusted child')
            bodies.append(body)
        if json.loads(bodies[0]) != publication:
            raise ValueError('Cold selected publication differs from live issued acknowledgement')
        facts = json.loads(bodies[1])
        if facts.get('executing_commit') != baseline or facts.get('baseline_commit') != baseline or facts.get('candidate_commit') != candidate or facts.get('candidate_code_executed') is not False:
            raise ValueError('Foreign selected execution/input vintage')
        pin = publication['operands']
        decoded = gzip.decompress(bodies[2])
        if len(decoded) != pin['decoded_bytes'] or hashlib.sha256(decoded).hexdigest() != pin['decoded_sha256']:
            raise ValueError('Whole selected operand decoded inverse differs')
        operands = json.loads(decoded)
        plan = operands.get('plan')
        if operands.get('kind') != 'complete-selected-continuous-operands-v1' or not isinstance(plan, dict):
            raise ValueError('Unsupported complete selected operand domain')
        ids = plan['required_ids']
        if ids != sorted(set(ids)) or sorted(operands['baseline']) != ids or sorted(operands['candidate']) != ids or plan['changed_ids'] != issued['changed_ids']:
            raise ValueError('Selected affected operand closure omitted/reordered owners')
        additions = operands.get('effective_additions', {'baseline': [], 'candidate': []})
        if sorted(additions) != ['baseline', 'candidate'] or any(not isinstance(v, list) for v in additions.values()):
            raise ValueError('Incomplete effective primitive operand domain')
        base_hashes = {'baseline': {}, 'candidate': {}}
        for row in facts['inverse']:
            vintage, identity = row['vintage'], row['id']
            if vintage not in base_hashes or identity in base_hashes[vintage] or not re.fullmatch('[a-f0-9]{64}', row['geometry_sha256']):
                raise ValueError('Foreign/duplicate complete source geometry inverse')
            base_hashes[vintage][identity] = row['geometry_sha256']
        if any(sorted(v) != ids for v in base_hashes.values()):
            raise ValueError('Complete source geometry inverse scope differs')
        result = compare_effective_primitives(detector, operands['baseline'], operands['candidate'], additions, base_hashes)
        if result['changed_location_ids'] != plan['changed_ids']:
            raise ValueError('Original polygon operator changed-ID closure differs from complete certificate')
        return {'version': 1, 'kind': 'trusted-selected-continuous-comparison-v1',
                'candidate_code_executed': False, 'issued_publication': publication,
                'source_binding': plan['source_bindings'], 'complete_owners': issued['complete_owners'],
                'required_ids': ids, 'original_strict_polygon_result': result,
                'status': result['status'], 'regressions': result['regressions'],
                'limits': ['Complete coordinate-derived exclusion and full affected source pointsets; original coverage/overlap predicates are unchanged.',
                           'No physical water/admin/history approval, repair assignment, release activation or deployment.']}



def transition_digest(value, newline=False):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw + (b'\n' if newline else b'')).hexdigest()


def transition_pin_matches(repo, commit, name, expected):
    """Stat first, then authenticate the exact ordinary whole body; no imports."""
    raw = git(repo, 'ls-tree', '-z', commit, '--', safe_path(name))
    if expected is None:
        return raw == b''
    if not isinstance(expected, dict) or set(expected) != {'mode', 'git_blob_oid', 'bytes', 'sha256'}:
        raise ValueError('Malformed trusted transition descriptor')
    size = expected['bytes']
    if (expected['mode'] != '100644' or type(size) is not int or not 0 <= size <= MAX_BYTES
            or not re.fullmatch('[a-f0-9]{40}', expected['git_blob_oid'])
            or not re.fullmatch('[a-f0-9]{64}', expected['sha256'])):
        raise ValueError('Invalid trusted transition mode/size/hash')
    literal = f"100644 blob {expected['git_blob_oid']}\t{name}\0".encode()
    if raw != literal:
        return False
    # Candidate bodies cannot choose their own byte allowance or parser.
    if git(repo, 'cat-file', '-s', expected['git_blob_oid']).strip() != str(size).encode():
        return False
    body = git(repo, 'cat-file', 'blob', expected['git_blob_oid'])
    return len(body) == size and hashlib.sha256(body).hexdigest() == expected['sha256']


def linux_support_transition(repo, baseline, candidate):
    """Authenticate only the finite reviewed transition; unknowns use old checks."""
    if baseline == candidate:
        return None
    reference, vector = LINUX_SUPPORT_REFERENCE, LINUX_SUPPORT_OLD_VECTOR
    paths = [row['path'] for row in reference]
    if (len(reference) != 31 or paths != sorted(set(paths))
            or transition_digest(reference) != LINUX_SUPPORT_REFERENCE_SHA256
            or len(vector) != 28 or len({row['path'] for row in vector}) != 28
            or transition_digest(vector, newline=True) != LINUX_SUPPORT_VECTOR_SHA256):
        raise ValueError('Incomplete or reordered trusted transition inventory')
    delta = [row for row in reference if row['path'] != LINUX_SUPPORT_MANIFEST]
    identities = [row for row in reference if row['path'] == LINUX_SUPPORT_MANIFEST]
    if (len(delta) != 30 or len(identities) != 1
            or transition_digest(delta) != LINUX_SUPPORT_DELTA_SHA256):
        raise ValueError('Incomplete exact30 support delta')
    # Complete prospective body union, including repeated old-vector reads.
    pins = [pin for row in reference for pin in [row['before'], row['after']] if pin is not None]
    sizes = [pin['bytes'] for pin in pins] + [row['bytes'] for row in vector]
    if any(type(n) is not int or not 0 <= n <= MAX_BYTES for n in sizes) or sum(sizes) > 256 * 1024 * 1024:
        raise ValueError('Trusted transition body union exceeds original bounds')
    for row in delta:
        if not transition_pin_matches(repo, baseline, row['path'], row['before']):
            return None
        if not transition_pin_matches(repo, candidate, row['path'], row['after']):
            return None
    for version in [baseline, candidate]:
        if not transition_pin_matches(repo, version, LINUX_SUPPORT_MANIFEST, identities[0]['after']):
            return None
    current_vector = []
    for pin in vector:
        # The path order and whole body hashes match original valueSha semantics.
        actual = entry(repo, baseline, pin['path'])
        if git(repo, 'cat-file', '-s', actual['git_blob_oid']).strip() != str(pin['bytes']).encode():
            return None
        body = read(repo, baseline, pin['path'])
        if actual['mode'] != '100644' or len(body) != pin['bytes'] or hashlib.sha256(body).hexdigest() != pin['sha256']:
            return None
        current_vector.append({'path': pin['path'], 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    if transition_digest(current_vector, newline=True) != LINUX_SUPPORT_VECTOR_SHA256:
        raise ValueError('Actual baseline complete28 vector differs')
    # Exact ordinary-file checks above prevent exclusions from hiding a same-name
    # directory. Literal exclusions have no wildcard meaning. Quiet tree comparison
    # emits no unbounded diff, invokes no hooks/textconv/external diff, and requires
    # all other tree entries (data, methods, modes, names and evidence) identical.
    command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=',
               '-C', str(repo), 'diff-tree', '--quiet', '-r', '--no-ext-diff',
               '--no-textconv', '--no-renames', baseline, candidate, '--', '.',
               *[':(exclude,literal)' + row['path'] for row in delta]]
    environment = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    compared = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=30, env=environment)
    if compared.returncode == 1:
        return None
    if compared.returncode != 0:
        raise ValueError('Complete candidate tree equivalence unavailable')
    if not git(repo, 'ls-tree', '-z', baseline, '--', 'data/ownership-selection.json'):
        raise ValueError('Finite transition needs actual selected baseline')
    trees = [git(repo, 'rev-parse', version + '^{tree}').decode().strip() for version in [baseline, candidate]]
    for tree in trees:
        immutable_sha(tree)
    return {'kind': 'exact-reviewed-linux-support-input-equivalence-v1',
            'reference_base': LINUX_SUPPORT_REFERENCE_BASE, 'reference_support_head': LINUX_SUPPORT_REFERENCE_HEAD,
            'reference_paths': 31, 'reference_sha256': LINUX_SUPPORT_REFERENCE_SHA256,
            'changed_paths': 30, 'exact_delta_sha256': LINUX_SUPPORT_DELTA_SHA256,
            'old_vector_sha256': LINUX_SUPPORT_VECTOR_SHA256,
            'baseline_commit': baseline, 'candidate_commit': candidate,
            'baseline_tree': trees[0], 'candidate_tree': trees[1],
            'manifest_identity': identities[0]['after'], 'whole_tree_outside_exact_delta_equal': True,
            'candidate_code_executed': False, 'candidate_scientific_qualification': False}


def inspect(repo, baseline, candidate):
    immutable_sha(baseline)
    immutable_sha(candidate)
    trusted_inventory = verify_trusted_checkout(repo, baseline)
    before, after = inventory(repo, baseline), inventory(repo, candidate)
    report = {'version': 1, 'method_id': 'worldatlas-trusted-geography-check-v1',
              'baseline_commit': baseline, 'candidate_commit': candidate,
              'trusted_code_commit': baseline, 'trusted_code_inventory_sha256': trusted_inventory,
              'candidate_code_executed': False,
              'baseline_input_inventory': before, 'candidate_input_inventory': after,
              'published': False, 'source_approval': False}
    transition = linux_support_transition(repo, baseline, candidate)
    if transition is not None:
        if before != after:
            raise ValueError('Finite transition changed geographic inputs')
        # Genuine original trusted checks run, including native/continuous paths.
        # Keep their actual baseline/baseline identities rather than relabelling
        # them as candidate qualification. Any exception/failure remains a failure.
        proof = inspect(repo, baseline, baseline)
        if proof['status'] not in ['not-applicable', 'no-footprint-change', 'no-new-regression']:
            raise ValueError('Original trusted baseline proof did not pass')
        return {**report, 'status': 'not-applicable', 'regressions': None,
                'reviewed_code_transition': transition, 'reused_baseline_proof': proof,
                'limits': ['Exact reviewed Linux boundary transition only; all other tree inputs and methods are unchanged.',
                           'Genuine baseline proof is reused under separately authenticated candidate-input equivalence.',
                           'Candidate code was not executed; no new qualification, gap clearance, source approval or publication.']}
    selected = any(git(repo, 'ls-tree', '-z', version, '--', 'data/ownership-selection.json')
                   for version in [baseline, candidate])
    if selected:
        import sys
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        native_raw = subprocess.check_output([
            os.environ.get('NODE', 'node'), str(repo / 'scripts/check-effective-geographic-regression.mjs'),
            str(repo), baseline, candidate, sys.executable], stderr=subprocess.PIPE, env=env)
        if len(native_raw) > MAX_BYTES:
            raise ValueError('Selected native report exceeds bounded output')
        native = json.loads(native_raw)
        report['selected_native_report'] = native
        if native['status'] == 'native-regressions-found':
            return {**report, 'status': 'native-regressions-found',
                    'regressions': len(native['intervals']),
                    'limits': ['Existing owner loss/reassignment has no automatic water or political exception. The raw polygon gate is preserved.']}
    import sys
    sys.path.insert(0, str(repo / 'scripts'))
    spec = importlib.util.spec_from_file_location('trusted_geographic_detector', repo / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    if selected:
        continuous = selected_continuous(repo, baseline, candidate, detector)
        report['selected_continuous_report'] = continuous
        if continuous.get('regressions') not in [None, 0] or str(continuous.get('status', '')).startswith('blocked-'):
            return {**report, 'status': continuous['status'], 'regressions': continuous['regressions'],
                    'differential_report': continuous['original_strict_polygon_result'],
                    'limits': ['Selected complete footprint loss/overlap is enforced with original predicates; no automatic source exception.']}
    if before == after:
        return {**report, 'status': 'not-applicable', 'regressions': None,
                'limits': ['Live geography input blobs are unchanged; this is applicability evidence, not fresh polygon validation or a global gap clearance.']}
    # Import only after verifying the checked-out implementation against trusted
    # baseline bytes. Candidate scripts, hooks and reproduction commands never run.
    result = detector.inspect(repo, baseline, candidate)
    return {**report, 'status': result['status'], 'regressions': result['regressions'],
            'differential_report': result,
            'limits': ['No automatic repair. Water-loss acceptance requires retained original physical sources, full-shape support and separate exact-head independent review.',
                       'Existing release, identity, regional certificate and historical import checks remain required.']}


def apply_adjudications(repo, candidate, report):
    # No proposed local envelope is accepted. Only baseline Node code can read
    # actual GitHub authority, using a read-only workflow token and exact head.
    if report['status'] != 'regressions-found':
        return report
    report['adjudication'] = {'status': 'blocked'}
    try:
        number, head = os.environ.get('GEOGRAPHY_PR_NUMBER'), os.environ.get('GEOGRAPHY_REVIEWED_HEAD')
        if not isinstance(number, str) or not re.fullmatch('[1-9][0-9]*', number):
            raise ValueError('Missing trusted PR context for source-backed adjudication')
        immutable_sha(head)
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        # stdout contains bounded base64 original dossier bytes, never executable
        # candidate code. The child enforces 48 MiB transport; timeout is finite.
        result = subprocess.run(['node', str(repo / 'scripts/check-geographic-adjudications.mjs'),
                                 '--pr', number, '--head', head], cwd=repo, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode or len(result.stdout) > 48 * 1024 * 1024:
            raise ValueError('Trusted GitHub source-decision validation failed; rerun after exact-head independent review')
        envelope = json.loads(result.stdout)
        from geographic_adjudication import adjudicate
        report['adjudication'] = adjudicate(report, envelope, lambda name: read(repo, candidate, name))
    except Exception as error:  # Preserve raw findings on every failed adjudication.
        report['adjudication'] = {'status': 'blocked', 'reason': str(error)[:1024]}
        if getattr(error, 'unsupported_geometry', None) is not None:
            report['adjudication']['unsupported_geometry'] = error.unsupported_geometry
    return report


def fetch_candidate(repo, candidate):
    immutable_sha(candidate)
    # Read token stays in process environment, not arguments, logs or Git config.
    token = os.environ.get('GH_TOKEN')
    if token:
        for key in list(os.environ):
            if key.startswith('GIT_CONFIG_KEY_') or key.startswith('GIT_CONFIG_VALUE_'):
                del os.environ[key]
        os.environ['GIT_CONFIG_COUNT'] = '1'
        os.environ['GIT_CONFIG_KEY_0'] = 'http.https://github.com/.extraheader'
        os.environ['GIT_CONFIG_VALUE_0'] = 'AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode()
    git(repo, 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head', '--filter=blob:none', 'origin', candidate)


def main():
    import sys
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('Invoke the trusted checker with python -I -B')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline', default=os.environ.get('GEOGRAPHY_BASELINE'))
    parser.add_argument('--candidate', default=os.environ.get('GEOGRAPHY_CANDIDATE'))
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    immutable_sha(args.baseline)
    immutable_sha(args.candidate)
    # Refuse collisions and symlink/dangling ancestors before any code or data
    # reads; the final exclusive open still handles a later destination race.
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    if args.out.exists():
        raise ValueError('Report destination already exists')
    if not args.out.absolute().parent.is_dir():
        raise ValueError('Report parent must be an existing ordinary directory')
    repo = args.repo.resolve()
    verify_trusted_checkout(repo, args.baseline)
    if args.fetch:
        fetch_candidate(repo, args.candidate)
    result = apply_adjudications(repo, args.candidate, inspect(repo, args.baseline, args.candidate))
    passed = result['status'] in ['not-applicable', 'no-footprint-change', 'no-new-regression'] or (
        result.get('adjudication', {}).get('status') == 'all-findings-supported-and-reviewed')
    result['gate_status'] = 'passed' if passed else 'blocked'
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('Geography check output exceeds bounded report size')
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    with args.out.open('xb') as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('report_sha256=' + digest + '\n')
    print(json.dumps({'status': result['status'], 'regressions': result['regressions'],
                      'report_bytes': len(raw), 'report_sha256': hashlib.sha256(raw).hexdigest()}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
