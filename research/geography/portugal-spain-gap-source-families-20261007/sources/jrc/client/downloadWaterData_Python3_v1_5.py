#!python
# Copyright (c) 2025, European Union
#
# This script is produced by the European Commission to download the Global Surface
# Water Explorer (GSWE) dataset.
#
# It is released WITHOUT ANY WARRANTY of any kind, express or implied, including but
# not limited to the warranties of merchantability and fitness for a particular
# purpose. Use it AT YOUR OWN RISK.

import urllib.request, sys, getopt, os
def main(argv):
   DESTINATION_FOLDER = argv[0]
   if (DESTINATION_FOLDER[-1:]!="/"):
      DESTINATION_FOLDER = DESTINATION_FOLDER + "/"
   if not os.path.exists(DESTINATION_FOLDER):
      print("Creating folder " + DESTINATION_FOLDER)
      os.makedirs(DESTINATION_FOLDER)
   DATASET_NAME = argv[1]
   print(DATASET_NAME)
   longs = [str(w) + "W" for w in range(180,0,-10)]
   longs.extend([str(e) + "E" for e in range(0,180,10)])
   lats = [str(s) + "S" for s in range(50,0,-10)]
   lats.extend([str(n) + "N" for n in range(0,90,10)])

   # ---------------------------------------------------------------------------------
   # monthlyhistory: time series tiled by year and month under
   #   download2024/monthlyhistory/<YYYY>/<YYYY>_<MM>/
   #   monthlyhistory_<lng>_<lat>_v1_5_<YYYY>_<MM>.tif
   # The user passes 'monthlyhistory' as the second parameter.
   # Optional 3rd parameter: comma-separated years   (e.g. "2023" or "2022,2024").
   #                         Omitted -> all years 2022,2023,2024.
   # Optional 4th parameter: comma-separated tile IDs (e.g. "100W_80N" or "0E_0N,10E_0N").
   #                         Omitted -> all tiles.
   # ---------------------------------------------------------------------------------
   if DATASET_NAME == "monthlyhistory":
      ALL_YEARS = ["2022", "2023", "2024"]
      MONTHS = ["%.2d" % m for m in range(1, 13)]

      # 3rd param: years subset
      if len(argv) >= 3 and argv[2].strip() != "":
         YEARS = [y.strip() for y in argv[2].split(",") if y.strip() != ""]
      else:
         YEARS = ALL_YEARS

      # 4th param: tile ID subset (tile id = "<lng>_<lat>", e.g. 100W_80N)
      if len(argv) >= 4 and argv[3].strip() != "":
         TILELIST = [t.strip() for t in argv[3].split(",") if t.strip() != ""]
      else:
         TILELIST = []   # empty = all tiles

      print("Years:", YEARS)
      print("Tiles:", TILELIST if TILELIST else "ALL")

      # build the (lng, lat) tile list, honoring the optional TILELIST
      tiles = []
      for lng in longs:
         for lat in lats:
            tileID = str(lng) + "_" + str(lat)
            if len(TILELIST) > 0 and tileID not in TILELIST:
               continue
            tiles.append((lng, lat))

      fileCount = len(tiles)*len(YEARS)*len(MONTHS)
      counter = 1
      for YYYY in YEARS:
         for MM in MONTHS:
            for lng, lat in tiles:
                  filename = DATASET_NAME + "_" + str(lng) + "_" + str(lat) + "_v1_5_" + YYYY + "_" + MM + ".tif"
                  if os.path.exists(DESTINATION_FOLDER + filename):
                     print(DESTINATION_FOLDER + filename + " already exists - skipping")
                  else:
                     url = ("https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/"
                            + DATASET_NAME + "/VER1-5/" + YYYY + "/" + YYYY + "_" + MM + "/" + filename)
                     try:
                        code = urllib.request.urlopen(url).getcode()
                     except urllib.error.HTTPError as e:
                        code = e.code
                     if (code != 404):
                        print("Downloading " + url + " (" + str(counter) + "/" + str(fileCount) + ")")
                        urllib.request.urlretrieve(url, DESTINATION_FOLDER + filename)
                     else:
                        print(url + " not found")
                  counter += 1
      return

   fileCount = len(longs)*len(lats)
   counter = 1
   for lng in longs:
      for lat in lats:
        filename = DATASET_NAME+ "_" + str(lng) + "_" + str(lat) + "_v1_5_2024.tif"
        print(filename)
        if os.path.exists(DESTINATION_FOLDER + filename):
           print(DESTINATION_FOLDER + filename + " already exists - skipping")
        else:
           url = "https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/Aggregated/VER1-5/" + DATASET_NAME + "/" + filename
           
           code = urllib.request.urlopen(url).getcode()
           if (code != 404):
              print("Downloading " + url + " (" + str(counter) + "/" + str(fileCount) + ")")
              urllib.request.urlretrieve(url, DESTINATION_FOLDER + filename)
           else:
              print(url + " not found")
        counter += 1
if __name__ == "__main__":
   main(sys.argv[1:])
