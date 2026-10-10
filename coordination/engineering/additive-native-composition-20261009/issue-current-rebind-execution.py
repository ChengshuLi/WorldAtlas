"""Fresh whole local platform pre-use issuer; original Python lineage preserved."""
import pathlib,sys,json,os,importlib.util
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rebind_execution_contract',HERE/'execution-contract.py');contract=importlib.util.module_from_spec(spec);exec(compile((HERE/'execution-contract.py').read_bytes(),str(HERE/'execution-contract.py'),'exec'),contract.__dict__)

# Reviewed finite Debian 13 / CPython 3.13.5 / Node 24.19.0 closure.
# This is a literal byte roster, never discovery from the executing machine.
# GNU time is Debian's signed-metadata-verified time 1.9-0.2 package.
# Source and consumed Python cache/extension bodies are pinned independently;
# OS/kernel provenance is context, not a claim of a hermetic operating system.
LINUX_RUNTIME = [
 {'role': 'git', 'path': '/usr/bin/git', 'bytes': 4082768, 'mode': 493, 'sha256': '356db14e102d68a1a37d8a1ac577dfd678d45d46e92f468bef8b7154e7bfdc60'},
 {'role': 'node', 'path': '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/bin/node', 'bytes': 125989464, 'mode': 493, 'sha256': 'bc17c508ffeed0ec622934f9b7fa72f8e78da65350e63c3eceb56fa688aa5e12'},
 {'role': 'process-inspector', 'path': '/usr/bin/ps', 'bytes': 154552, 'mode': 493, 'sha256': '43b8d2d049183e9ebc409c86b89150b5a4a68fa19fe1815b16bed5561921a9c3'},
 {'role': 'supervisor-python', 'path': '/usr/bin/python3.13', 'bytes': 6832784, 'mode': 493, 'sha256': '889c603f0d17cb54060951bcf4c4f9b8c9ebd9e52b392c70209bbb9755d797d9'},
 {'role': 'supervisor-stdlib', 'path': '/etc/python3.13/sitecustomize.py', 'bytes': 155, 'mode': 420, 'sha256': '43d81125d92376b1a69d53a71126a041cc9a18d8080e92dea0a2ae23be138b1e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/_weakrefset.cpython-313.pyc', 'bytes': 12049, 'mode': 420, 'sha256': 'eba778b88fd8ddfce2d6ecbbbaa898b641ada82b021e65e84287b77ba6581581'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/contextlib.cpython-313.pyc', 'bytes': 30494, 'mode': 420, 'sha256': '8a4a9c4b467a2750668e64c49405b25b8c02c47fd3f8dd8bd4170ee1f200817b'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/copyreg.cpython-313.pyc', 'bytes': 7536, 'mode': 420, 'sha256': '955c6f626fca8bddc85878ab9daae4ec8e891394f71f49e7837e6d591399e1ad'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/enum.cpython-313.pyc', 'bytes': 85851, 'mode': 420, 'sha256': '811e87236348e28cedb1c684be15f0971c276139a6b1b4a95b5a3afa9d22479e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/fnmatch.cpython-313.pyc', 'bytes': 6804, 'mode': 420, 'sha256': '88559d1003cec0b23f37d0038a207406045601444f99904d0e8255bc62981860'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/functools.cpython-313.pyc', 'bytes': 42253, 'mode': 420, 'sha256': '8f0eb819e5894dc93fd9f34e87a23b39c0efd340b7ec4ecf88d4dc9db7ceba69'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/glob.cpython-313.pyc', 'bytes': 23666, 'mode': 420, 'sha256': '2c05e62a47e7859f61e7c04cfcce25b53b6391086736cbc17e5a6a9b82686564'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/hashlib.cpython-313.pyc', 'bytes': 8276, 'mode': 420, 'sha256': '3f1f0d9f919fa18f466abb0c15b660d2273ab2673193d18913b2fa32b573dcba'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/keyword.cpython-313.pyc', 'bytes': 1041, 'mode': 420, 'sha256': '32d3ea422d4028a0731b1e8f9548be486cf4ec53034a8bd434916893d9c28ccc'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/locale.cpython-313.pyc', 'bytes': 58999, 'mode': 420, 'sha256': 'ee69fdcf54689d4aff938a4c54abaf860ef02b6de12f99a07e063c9f97b8e104'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/operator.cpython-313.pyc', 'bytes': 17365, 'mode': 420, 'sha256': '17c5bacd98bb69c58097210481e70c0bdb0530e1bc935b77bb6f9948ca75675d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/reprlib.cpython-313.pyc', 'bytes': 10423, 'mode': 420, 'sha256': '6c71e07bb6f81ac39455614ad3b90d0c89d12e719f9e89da1ce5380fb0642cb0'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/selectors.cpython-313.pyc', 'bytes': 26355, 'mode': 420, 'sha256': '3ddeb63a670b7f7c04d951e6fabd34428f5d04f55146b2d56f18da7816723b91'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/signal.cpython-313.pyc', 'bytes': 4544, 'mode': 420, 'sha256': '2cd081c945d2a0986fcab4e4a3f32f53011eaa2d53c85efc731616904e5d5411'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/sitecustomize.cpython-313.pyc', 'bytes': 299, 'mode': 420, 'sha256': 'b46749b3c2c4afbb1ed50d6e9dd59d35da242b252501ef5983d5afa2489739e1'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/subprocess.cpython-313.pyc', 'bytes': 81954, 'mode': 420, 'sha256': '54ba02e1ac4fd65cd352e4d6a9673ff46ebb5b5f730d70ef2ba5027c2d387f43'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/threading.cpython-313.pyc', 'bytes': 63292, 'mode': 420, 'sha256': '666c865767b8514e8b2f78f7fc23f9a11b8d000c54e739955359fcb8b9205a4b'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/types.cpython-313.pyc', 'bytes': 15545, 'mode': 420, 'sha256': '7be64f77ca682bb16d53420f5a6b6b52f10f147c74e1d3a842e341e3e56ecdf6'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/__pycache__/warnings.cpython-313.pyc', 'bytes': 29538, 'mode': 420, 'sha256': '99760d472c02d0ab26d8d015e6b8f625f265d6667572fd7f5a2dcb32e1f62e05'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/_collections_abc.py', 'bytes': 32264, 'mode': 420, 'sha256': '2cfe340c4cf54077f054cd366a2c7a515e9ee8da7d8b3fa071251f280034756d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/_sitebuiltins.py', 'bytes': 3128, 'mode': 420, 'sha256': 'b9388bc1d6d12ed6be12da420ab1feca40f99c0e33ec315d92b1e01cb69b25bc'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/_weakrefset.py', 'bytes': 5893, 'mode': 420, 'sha256': '91895a451d06e9f521a1171b31b9b19bc9740f35af00d4fa106338ab7167c9ac'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/abc.py', 'bytes': 6538, 'mode': 420, 'sha256': 'e558702a95cdce3febd289da021715d2b92bc43995b8a1bc58dfa1c3d8010287'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/codecs.py', 'bytes': 36928, 'mode': 420, 'sha256': '514b00fe93120b4face4508351aa9f1246ecc808c4da3e599dfee7430fe459f9'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/collections/__init__.py', 'bytes': 52500, 'mode': 420, 'sha256': '2347f647577b6c11b82fc48fa4a1744f7af1af87f15942f92b7cc4410f0a817b'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/collections/__pycache__/__init__.cpython-313.pyc', 'bytes': 73200, 'mode': 420, 'sha256': 'b876040c2bf3f850d6b3da0171bf30cab69fdf73aadcc2deb496b7bb825cc2d5'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/contextlib.py', 'bytes': 27801, 'mode': 420, 'sha256': 'c1e0d67b2007de11ae93cd36cf6faf38d9ab32656a832d592a49325eec579f96'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/copyreg.py', 'bytes': 7614, 'mode': 420, 'sha256': 'c8eda41f05c6bf95a4da4726a530409d2485ae060b8d019b3a8034389a15d3e9'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/__init__.py', 'bytes': 5884, 'mode': 420, 'sha256': '78c4744d407690f321565488710b5aaf6486b5afa8d185637aa1e7633ab59cd8'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/__pycache__/__init__.cpython-313.pyc', 'bytes': 6017, 'mode': 420, 'sha256': 'cdce7c86c054dd720b9a7a3bb547a8c7f72af844e2959fa8fd463ad02a89eb91'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/__pycache__/aliases.cpython-313.pyc', 'bytes': 12385, 'mode': 420, 'sha256': '5017e171dd74174cb2941c5d7b4e54e60b35a5782230d82f24e418d691e75254'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/__pycache__/utf_8.cpython-313.pyc', 'bytes': 2284, 'mode': 420, 'sha256': 'c972f5f12284ed012121e0142fafecf0e80a1020e8688f1aebd34f38810aac5f'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/__pycache__/utf_8_sig.cpython-313.pyc', 'bytes': 6913, 'mode': 420, 'sha256': '69824d24d14ad453167e187b1fa34d2aea4fa07c77c86eb39302208c53349d66'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/aliases.py', 'bytes': 15713, 'mode': 420, 'sha256': 'cac92d68c7ea5bc0f05b448b9144e3bdf236d0b7d27ab66112e96d43aad15b3f'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/utf_8.py', 'bytes': 1005, 'mode': 420, 'sha256': 'ba0cac060269583523ca9506473a755203037c57d466a11aa89a30a5f6756f3d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/encodings/utf_8_sig.py', 'bytes': 4133, 'mode': 420, 'sha256': '1ef3da8d8aa08149e7f274dc64dbfce2155da812e5258ca8e8f832428d3b5c2d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/enum.py', 'bytes': 85578, 'mode': 420, 'sha256': '419c011ac6db4efd60e737db7cbba83eb67110ed20d91781f7c60cdeed61e0b6'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/fnmatch.py', 'bytes': 6180, 'mode': 420, 'sha256': '95391dac2ce9f60084d65eba2f4b9d9735e28136d55b684e1fde7d6342555963'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/functools.py', 'bytes': 39123, 'mode': 420, 'sha256': '7aa8725afbe9b9fc47a825b4e7c0330fa374432f481d7be8202b96f56eeac9a0'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/genericpath.py', 'bytes': 6247, 'mode': 420, 'sha256': 'cdac5a68dd738051e0d66fc81d5947d6a1776248fc6fe862253477608d870ec4'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/glob.py', 'bytes': 19720, 'mode': 420, 'sha256': '3399f242a9bfb4e0b2b8bbbcdc0231487e453a861f4a4ca109c2a560e05698e8'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/hashlib.py', 'bytes': 9446, 'mode': 420, 'sha256': 'f129b330e6ab878a96085843b3606acd7d157b8fe6edfa15e37fa13988cef19c'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/__init__.py', 'bytes': 4767, 'mode': 420, 'sha256': '72b07de4133a7e39b2f6a7920465669aa04626f217e800779587bc0713fe002e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/__pycache__/__init__.cpython-313.pyc', 'bytes': 4544, 'mode': 420, 'sha256': 'cabd89b8800057fc6267daa96b4a8b6efb45a2704a9e82ef3bb63959b091380e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/__pycache__/_abc.cpython-313.pyc', 'bytes': 1618, 'mode': 420, 'sha256': 'a19e07906305fbc6889af5bb1d6c75169a320ee097c42625a0642806f467c838'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/_abc.py', 'bytes': 1354, 'mode': 420, 'sha256': '80aab7931dc999dee581c8b8b56fcd973fe156335a96ceeaf6acfc03cebf10e8'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/_bootstrap.py', 'bytes': 57082, 'mode': 420, 'sha256': 'b84488f731914f6da30607e10f6f8d4c5c2ff7f4b0e913060aa66999c04f6252'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/_bootstrap_external.py', 'bytes': 73169, 'mode': 420, 'sha256': '6cfeeeb243d340a6fa551e73f1752e9d45155dfc529631ce485b9948def20e8e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/importlib/util.py', 'bytes': 11199, 'mode': 420, 'sha256': '47eed68cfc84cdb4950edc092fc1a81abf37b47cadd6ff68d3460b1c9f536e9b'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/io.py', 'bytes': 3582, 'mode': 420, 'sha256': '7cec3cb8ac004058dd0a5af246e6d950fb59c7ddd0058fda48bcb3fcb98d8822'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/__init__.py', 'bytes': 14020, 'mode': 420, 'sha256': 'd5d41e2c29049515d295d81a6d40b4890fbec8d8482cfb401630f8ef2f77e4d5'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/__pycache__/__init__.cpython-313.pyc', 'bytes': 13510, 'mode': 420, 'sha256': '2d542f9389f445777b8bdf53f45024801026fe38f52ab9cd08b2e12f2d84fe8e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/__pycache__/decoder.cpython-313.pyc', 'bytes': 13822, 'mode': 420, 'sha256': '64fa2550dbcfbca1513339044f4e6bdb938498349403acee4735c93a877397db'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/__pycache__/encoder.cpython-313.pyc', 'bytes': 15164, 'mode': 420, 'sha256': 'edfb56c0bf2f6d8b807ba9c813cca24f63dd707de51881ff8dde03089bef92ea'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/__pycache__/scanner.cpython-313.pyc', 'bytes': 3363, 'mode': 420, 'sha256': '57b426beafba71a0876367e4a7e3b7b35110e6f7d25520747ca1407aaae01e17'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/decoder.py', 'bytes': 12872, 'mode': 420, 'sha256': '6d95679fccf178f2af9e9eead42f8efb084c58735951dc47fce89aec11d44955'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/encoder.py', 'bytes': 16148, 'mode': 420, 'sha256': '4b24ae9c0efbe73272f6a891054b2f40cc6e07c3c9957b33a2ebc8da130e671e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/json/scanner.py', 'bytes': 2434, 'mode': 420, 'sha256': '572958017eae8842eeddd0e3d18d3c56cc0a197348224915e1d87ce937841764'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/keyword.py', 'bytes': 1073, 'mode': 420, 'sha256': '18c2be738c04ad20ad375f6a71db34b3823c7f40b0340f5294d0e89f3c9b093b'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/lib-dynload/_hashlib.cpython-313-x86_64-linux-gnu.so', 'bytes': 68272, 'mode': 420, 'sha256': 'fe5ccb577d81444ca5f592e7484cd43088dcc7c555736a26c9aa9f95f8e052ed'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/locale.py', 'bytes': 79033, 'mode': 420, 'sha256': 'ccffa53357828663c7a9d3f6817aab92dab378eaa950b460a72401d842f74365'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/ntpath.py', 'bytes': 30886, 'mode': 420, 'sha256': '7c5c992b1b52f97d7dc73ad09ea8b97917475e7e4474563379e71b03015f04ca'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/operator.py', 'bytes': 10980, 'mode': 420, 'sha256': 'c048f8a6852832d5fa750d6ae772d7658c52c3511d261cb902f7edfd262e9127'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/os.py', 'bytes': 41635, 'mode': 420, 'sha256': 'b6b68783d438ff044c096fd0c3d1dfc9479a9b632e0a450a376be6c01655aafe'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/__init__.py', 'bytes': 296, 'mode': 420, 'sha256': '07921047886282e3d324acf95f7d9f840faa806664ee7007e7333a7df4cdcaf6'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/__pycache__/__init__.cpython-313.pyc', 'bytes': 477, 'mode': 420, 'sha256': '4a662caeb2676fa954799e33e4b46c2299d85bd2b28c2c09d4ab0eb98acf0159'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/__pycache__/_abc.cpython-313.pyc', 'bytes': 39998, 'mode': 420, 'sha256': 'a70f7a0d2158a7845f04feef0d0e766cccc3fc47e43700dd28ddd84940f581e5'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/__pycache__/_local.cpython-313.pyc', 'bytes': 40913, 'mode': 420, 'sha256': '4bf9b2987232d8881f82f5c34a2882ae08cc29473ff07a468e82eb8e21954678'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/_abc.py', 'bytes': 33565, 'mode': 420, 'sha256': '75e6bc728013d11446126d535f92b8907fb6dae7404df3d0268ac7b6865a2090'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/pathlib/_local.py', 'bytes': 31460, 'mode': 420, 'sha256': 'd147f1b179b684138519b31cddebec8fe1d6e9e576d37bd672e9c1519591aeec'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/posixpath.py', 'bytes': 18233, 'mode': 420, 'sha256': '69acb9e294987cd6056a2237048373cf8d6201faf1e43a49c38889b47d2fb28e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__init__.py', 'bytes': 17876, 'mode': 420, 'sha256': 'dbe158a677c6aaacf717ea2abc23c56233453d38024aef75b7c3d93612cabb93'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__pycache__/__init__.cpython-313.pyc', 'bytes': 19368, 'mode': 420, 'sha256': 'ceb70f5819b3d218ed1e42b6bc18155fdac1d9b99741b4f7c6e1af396be85d16'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__pycache__/_casefix.cpython-313.pyc', 'bytes': 1816, 'mode': 420, 'sha256': 'f86fb7eade52471f3a51d2989df19c04964b4ef18682fe470693f5f30f4b4a1e'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__pycache__/_compiler.cpython-313.pyc', 'bytes': 26866, 'mode': 420, 'sha256': 'a261428d269e1dc3268dab78e07c60373abe887193073d6d605bcc84c6f5e149'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__pycache__/_constants.cpython-313.pyc', 'bytes': 5379, 'mode': 420, 'sha256': '96eb0588eb07988cd149285cb5ca41b3d76e6f3fac60367c4e266adf9fb89a5d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/__pycache__/_parser.cpython-313.pyc', 'bytes': 43564, 'mode': 420, 'sha256': '6f94266d816b4e7bff2448e48aef1a56566f0151eb9c34421ed897c463cca4d3'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/_casefix.py', 'bytes': 5444, 'mode': 420, 'sha256': '1b12d9136f23db6c3f6f26053fefc15ca964b886838c7b9c1fabf8d2efc1e5c8'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/_compiler.py', 'bytes': 26290, 'mode': 420, 'sha256': '83537237a82294d084d40abaa42e86149be33eef338a5ef028a7fd2fad0dafd5'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/_constants.py', 'bytes': 5939, 'mode': 420, 'sha256': '1dbe236d34fa934e3e7172ba9d6b0dcfab338ecf7717f370f1fd4a9d24b2ecdb'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/re/_parser.py', 'bytes': 41237, 'mode': 420, 'sha256': 'c7a6c80b3b448f50684c320265a7b5efb5d0b1daf0a36fb5dee8dd83628359d7'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/reprlib.py', 'bytes': 7192, 'mode': 420, 'sha256': 'af33116cdd0d8baf2d5d41d9e6eafa9f5a0b7fb5af7e7343218877a04965f2f3'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/selectors.py', 'bytes': 19457, 'mode': 420, 'sha256': '4b8a60cfbb619d080f87dffe1578372e56e8c0ac826f043224a154cf7b77606d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/signal.py', 'bytes': 2495, 'mode': 420, 'sha256': '0363c964c90ac0b3e515de5749205e6e6454051a1211058375d84d91eab6071a'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/site.py', 'bytes': 26648, 'mode': 420, 'sha256': 'f2dc75d58f273ef34c5e552ed3a429ad4bb00c9490ba2d205e06dc20640a59ea'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/stat.py', 'bytes': 6147, 'mode': 420, 'sha256': 'f76eaa7f02d6ef4a8c3c3e82cae34ed72870b643b8c94937a34c697d1e9d6ca2'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/subprocess.py', 'bytes': 89486, 'mode': 420, 'sha256': '21ecc4c8f4fcf641974fc0d9cc28e97b07670ed1cef7e9d96769b31bb8345586'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/threading.py', 'bytes': 55244, 'mode': 420, 'sha256': '61e1cd79adb93cfacf69dc3900ea99fbc8042d65f3742233c07c5707e39add84'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/types.py', 'bytes': 11207, 'mode': 420, 'sha256': '74516af714d270b59d67e5ae5e60a02cb4ff32ecdd373e165ad1d780fbfd2c5d'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/warnings.py', 'bytes': 26948, 'mode': 420, 'sha256': '1fc53fd4ecec5e32214116b1fe02c3ef1509ab0e57661f79d98ef3a598ec87bd'},
 {'role': 'supervisor-stdlib', 'path': '/usr/lib/python3.13/zipimport.py', 'bytes': 32890, 'mode': 420, 'sha256': 'ec9f157ff6d4ebd26a6fd1715247578068b5af2799d07ecf06f2b531a5605e13'},
 {'role': 'time', 'path': '/workspace/scratch/127991fc8b8e/cloud-tools/gnu-time/time-1.9-0.2-amd64/usr/bin/time', 'bytes': 27384, 'mode': 493, 'sha256': 'efc0d1112e36ec76c14bf7508e287935cf1631d9d0d91fb532802d07aef51cea'},
]

def platform_runtime():
 if sys.platform=='darwin':
  return json.loads((HERE/'mac-execution-runtime-original.json').read_text())['runtime'],'-l'
 assert sys.platform=='linux','Unreviewed execution platform'
 return [dict(p) for p in LINUX_RUNTIME],'-v'

def issue(root,head,plan_path,destination,output):
 assert root.is_absolute() and len(head)==40 and all(c in '0123456789abcdef' for c in head)
 assert destination.is_relative_to(root/'.cache') and output.is_relative_to(root/'.cache')
 for p in [plan_path,destination,output]:
  assert p.is_absolute() and '..' not in p.parts
  for a in p.parents:assert not a.is_symlink() and a.is_dir()
 assert not os.path.lexists(destination) and not os.path.lexists(output),'Fresh output custody/destination required'
 stat=plan_path.stat();assert stat.st_size<=131072 and stat.st_mode&0o777==0o644
 raw=plan_path.read_bytes();plan=json.loads(raw);assert plan['execution_commit']==head and 0<plan['limits']['complete_phase_bytes']<=contract.PHASE
 for name in ['mac-execution-runtime-original.json','run-current-rebind.mjs','supervise-current-rebind.py']:
  assert (HERE/name).stat().st_size<=131072 and not (HERE/name).is_symlink()
 assert [p['path'] for p in plan['executed_code']]==json.loads((HERE/'execution-code-paths.json').read_bytes())
 runtime,time_option=platform_runtime()
 assert pathlib.Path(sys.executable).resolve()==pathlib.Path(next(p['path'] for p in runtime if p['role']=='supervisor-python')).resolve(),'Actual Python executable differs from bound runtime'
 for name in ['package.json','sha2.js','_md.js','_u64.js','utils.js']:
  source=next(p for p in plan['executed_code'] if p['path'].endswith('/module-bodies/'+name));p=root/'node_modules'/'@noble'/'hashes'/name
  runtime.append({'role':'installed-dependency','path':str(p),'bytes':source['bytes'],'sha256':source['sha256'],'mode':0o644})
 # Declare actual source/stat descriptors before any runtime/code body opens.
 def ordinary(p):s=p.stat();assert s.st_size<=contract.FILE and s.st_mode&0o777==0o644;return {'path':str(p),'bytes':s.st_size,'sha256':contract.digest(p.read_bytes()),'mode':0o644}
 # Small entry/supervisor metadata bodies have their own fixed1MiB metadata
 # admission. Full installed runtime is only opened by capture after union stats.
 pre={'runtime':runtime,'code':plan['executed_code'],'entry':ordinary(HERE/'run-current-rebind.mjs'),'supervisor':ordinary(HERE/'supervise-current-rebind.py'),'plan':{'path':str(plan_path),'bytes':len(raw),'sha256':contract.digest(raw),'mode':0o644}}
 python_extra=sum(p['bytes'] for p in runtime if p['role'] not in ('node','git','installed-dependency'))
 operating=plan['limits']['complete_phase_bytes']+python_extra+contract.OUTPUT+contract.META
 assert operating<=contract.PHASE,'Whole child carried union plus actual external runtime/output reserve exceeds operating phase'
 contract.capture(root,head,pre)
 command=[next(p['path'] for p in runtime if p['role']=='time'),time_option,next(p['path'] for p in runtime if p['role']=='node'),'--expose-gc',pre['entry']['path'],str(plan_path),str(destination)]
 result={'version':1,'kind':'issued-current-rebind-execution-pre-use-v1','execution_commit':head,'root':str(root),'command':command,'pre_use':pre,'operating_phase_bytes':operating,'output_log_reserve_bytes':contract.OUTPUT}
 body=contract.canonical(result);assert len(body)<=131072
 fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 try:os.write(fd,body)
 finally:os.close(fd)
 return result
if __name__=='__main__':
 assert sys.flags.isolated and sys.dont_write_bytecode,'Use exact isolated Python -I -B entry'
 assert len(sys.argv)==7
 result=issue(pathlib.Path(sys.argv[1]),sys.argv[2],pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[4]),pathlib.Path(sys.argv[5]));assert sys.argv[6]=='issue-only';print(json.dumps({'bytes':len(contract.canonical(result)),'sha256':contract.digest(contract.canonical(result)),'operating_phase_bytes':result['operating_phase_bytes']}))
