#!/bin/bash
NATIVE_TOOLS_TOTAL_BYTES=10791003
NATIVE_TOOLS_LOCK_SHA256=ea0d817773a2a56609e06384f72213ace1651f083d907f059e24960836321d19
NATIVE_SYSTEM=Darwin
NATIVE_RELEASE=24.6.0
NATIVE_MACHINE=x86_64
NATIVE_BASH=/bin/bash
bash() { "$NATIVE_BASH" "$@"; }
NATIVE_GIT=/Library/Developer/CommandLineTools/usr/bin/git
git() { "$NATIVE_GIT" "$@"; }
NATIVE_TAR=/usr/bin/bsdtar
tar() { "$NATIVE_TAR" "$@"; }
NATIVE_TEE=/usr/bin/tee
tee() { "$NATIVE_TEE" "$@"; }
NATIVE_SHA256SUM=/sbin/sha256sum
sha256sum() { "$NATIVE_SHA256SUM" "$@"; }
NATIVE_CMP=/usr/bin/cmp
cmp() { "$NATIVE_CMP" "$@"; }
NATIVE_MKTEMP=/usr/bin/mktemp
mktemp() { "$NATIVE_MKTEMP" "$@"; }
NATIVE_UNLINK=/bin/unlink
unlink() { "$NATIVE_UNLINK" "$@"; }
NATIVE_RMDIR=/bin/rmdir
rmdir() { "$NATIVE_RMDIR" "$@"; }
NATIVE_MKDIR=/bin/mkdir
mkdir() { "$NATIVE_MKDIR" "$@"; }
NATIVE_OTOOL=/Library/Developer/CommandLineTools/usr/bin/llvm-otool
otool() { "$NATIVE_OTOOL" "$@"; }
NATIVE_GREP=/usr/bin/grep
grep() { "$NATIVE_GREP" "$@"; }
NATIVE_WC=/usr/bin/wc
wc() { "$NATIVE_WC" "$@"; }
NATIVE_SYNC=/bin/sync
sync() { "$NATIVE_SYNC" "$@"; }
NATIVE_UNAME=/usr/bin/uname
uname() { "$NATIVE_UNAME" "$@"; }
NATIVE_TR=/usr/bin/tr
tr() { "$NATIVE_TR" "$@"; }
NATIVE_LN=/bin/ln
ln() { "$NATIVE_LN" "$@"; }
NATIVE_AWK=/usr/bin/awk
awk() { "$NATIVE_AWK" "$@"; }
NATIVE_SHASUM=/usr/bin/shasum
shasum() { "$NATIVE_SHASUM" "$@"; }
verify_native_tools() {
  test "$("$NATIVE_UNAME" -s)" = "$NATIVE_SYSTEM"
  test "$("$NATIVE_UNAME" -r)" = "$NATIVE_RELEASE"
  test "$("$NATIVE_UNAME" -m)" = "$NATIVE_MACHINE"
  actual_0=$("$NATIVE_SHA256SUM" /Library/Developer/CommandLineTools/usr/bin/git)
  test "${actual_0%% *}" = 4c5ca299b5311572b4f948d11efd7c66dcadf30950fbf260688ee32f4a63f6a4
  actual_1=$("$NATIVE_SHA256SUM" /Library/Developer/CommandLineTools/usr/bin/llvm-otool)
  test "${actual_1%% *}" = 1cb32a54070f97a9a33bad5f16bbd6b5d5cb69fb4164d46a419197f405853a24
  actual_2=$("$NATIVE_SHA256SUM" /bin/bash)
  test "${actual_2%% *}" = b46e8d4eac541d79f77000550b4254b47599df8dd8c52cc5b0f37cca1c3b02d4
  actual_3=$("$NATIVE_SHA256SUM" /bin/ln)
  test "${actual_3%% *}" = 5142155e176cc38a1e46153723f6a01eae3153c7fbe109090adf7c26997ac858
  actual_4=$("$NATIVE_SHA256SUM" /bin/mkdir)
  test "${actual_4%% *}" = e0ebb9a221e2a70c43c887ee04c5e710faac4ec3bb8f43deb608074695364ccf
  actual_5=$("$NATIVE_SHA256SUM" /bin/rmdir)
  test "${actual_5%% *}" = 88c68b4542a6a6712b3c54e4143bd2db775fe3a136277be3e7f54bdd93559be5
  actual_6=$("$NATIVE_SHA256SUM" /bin/sync)
  test "${actual_6%% *}" = f71dbca841122263b9410ceb4ab888034071c1aa4932dd9345c189ab813e931f
  actual_7=$("$NATIVE_SHA256SUM" /bin/unlink)
  test "${actual_7%% *}" = 52664e60b8518927d414ae48d4ffd229d45d8845656f1d975f14181109a28ab6
  actual_8=$("$NATIVE_SHA256SUM" /sbin/sha256sum)
  test "${actual_8%% *}" = 911cfe6fc220c41ee02d18ea71c89f8ff788bdf8a6d4f0d6f94dc965aa18521f
  actual_9=$("$NATIVE_SHA256SUM" /usr/bin/awk)
  test "${actual_9%% *}" = eff2fc0af6a429ec469f5b62cdb781339c571e0540b7f4e2a846d165095e8580
  actual_10=$("$NATIVE_SHA256SUM" /usr/bin/bsdtar)
  test "${actual_10%% *}" = aa870c0534e2317cc62d228127e7af58582827f8380e16cb89c9454c1bc870d6
  actual_11=$("$NATIVE_SHA256SUM" /usr/bin/cmp)
  test "${actual_11%% *}" = 9db3988a2c1e1bba78256987a6d9bedc08816f290fb4d9655c985efa7f7605b8
  actual_12=$("$NATIVE_SHA256SUM" /usr/bin/git)
  test "${actual_12%% *}" = 7588ceab299393618d6f8861502ac0588d1594025f301d9a61a898215b5571d3
  actual_13=$("$NATIVE_SHA256SUM" /usr/bin/grep)
  test "${actual_13%% *}" = dd0998a8203835aec5d4dd61823f7b98b9e7b085c7f2728560feb94b9444bb9e
  actual_14=$("$NATIVE_SHA256SUM" /usr/bin/mktemp)
  test "${actual_14%% *}" = e9533f44792b1db75c36f3673eaec04467eb95b5d7121d5b40a0623f7229fe3a
  actual_15=$("$NATIVE_SHA256SUM" /usr/bin/otool)
  test "${actual_15%% *}" = 7588ceab299393618d6f8861502ac0588d1594025f301d9a61a898215b5571d3
  actual_16=$("$NATIVE_SHA256SUM" /usr/bin/shasum)
  test "${actual_16%% *}" = 0812595f981a26f813d98dc380af14d4af427626c9339eda29eb849ae13de1e3
  actual_17=$("$NATIVE_SHA256SUM" /usr/bin/tee)
  test "${actual_17%% *}" = 9f24a14c6c8c64463250337738fe748635157903e9176ba7d87625cfdd47149e
  actual_18=$("$NATIVE_SHA256SUM" /usr/bin/tr)
  test "${actual_18%% *}" = 46b6d01dfb4208edf512ade7cee49a34e50644b667ed1394e599cce71800926e
  actual_19=$("$NATIVE_SHA256SUM" /usr/bin/uname)
  test "${actual_19%% *}" = 8fc60d9639661172997e2036559c0e635fa127f9b84895115c36797cb23b52bf
  actual_20=$("$NATIVE_SHA256SUM" /usr/bin/wc)
  test "${actual_20%% *}" = 6dd1ce80825c439ef6dc4812cdb0711bf191446728b8a13ed655f22ce210aeee
}
