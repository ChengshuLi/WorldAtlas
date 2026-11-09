import numpy as np
def rle(array):
 rows=[0];runs=[]
 for row in array:
  for i,x in enumerate(row):
   if i==len(row)-1 or row[i+1]!=x:runs.extend((i+1,int(x)))
  rows.append(len(runs)//2)
 return np.array(rows,dtype='<u4'),np.array(runs,dtype='<u4')
