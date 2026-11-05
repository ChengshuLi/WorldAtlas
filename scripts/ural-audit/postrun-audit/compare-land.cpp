// Independent streaming seed/physical/component coverage audit. No geography is selected here.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using U=uint32_t; using Count=uint64_t;
static U read32(std::istream& in) {
 unsigned char b[4]; if(!in.read(reinterpret_cast<char*>(b),4)) throw std::runtime_error("truncated u32");
 return U(b[0])|(U(b[1])<<8)|(U(b[2])<<16)|(U(b[3])<<24);
}
static U number(const char* s) {
 std::string v(s); size_t n=0; unsigned long long x=std::stoull(v,&n);
 if(n!=v.size()||x>std::numeric_limits<U>::max()) throw std::runtime_error("bad integer");return U(x);
}
struct Segment {U start,end,value; bool present;};
class Rows {
 std::ifstream runs; std::vector<U> offsets; U width; bool component;
 public:
 Rows(const char* rowfile,const char* runfile,U w,U h,bool sparse):runs(runfile,std::ios::binary),width(w),component(sparse) {
  if(!runs) throw std::runtime_error("cannot open run file");
  std::ifstream rows(rowfile,std::ios::binary);if(!rows) throw std::runtime_error("cannot open row file");
  rows.seekg(0,std::ios::end);if(rows.tellg()!=std::streamoff(4)*(std::streamoff(h)+1)) throw std::runtime_error("row index size mismatch");rows.seekg(0);
  offsets.reserve(size_t(h)+1);for(Count i=0;i<=h;i++) offsets.push_back(read32(rows));
  if(offsets.front()!=0) throw std::runtime_error("row index does not start at zero");
  for(size_t i=1;i<offsets.size();i++)if(offsets[i]<offsets[i-1]) throw std::runtime_error("nonmonotonic row offsets");
  runs.seekg(0,std::ios::end);if(runs.tellg()!=std::streamoff(offsets.back())*(sparse?12:8)) throw std::runtime_error("run size mismatch");runs.seekg(0);
 }
 std::vector<Segment> row(U y) {
  U n=offsets.at(size_t(y)+1)-offsets.at(y),last=0; if(n>width) throw std::runtime_error("too many runs in row");
  std::vector<Segment> v;v.reserve(size_t(n)*2+1);
  for(U i=0;i<n;i++){
   U a=last,b,code;
   if(component){a=read32(runs);b=read32(runs);code=read32(runs);if(a<last||a>=b||b>width||code==std::numeric_limits<U>::max())throw std::runtime_error("invalid component interval");if(a>last)v.push_back({last,a,0,false});}
   else{b=read32(runs);code=read32(runs);if(b<=last||b>width)throw std::runtime_error("invalid full-width interval");}
   v.push_back({a,b,code,true});last=b;
  }
  if(component&&last<width)v.push_back({last,width,0,false});
  if(!component&&last!=width)throw std::runtime_error("full-width row incomplete");
  return v;
 }
};
int main(int argc,char**argv){try{if(argc!=9)throw std::runtime_error("usage WIDTH HEIGHT physical.rows physical.runs reference.rows reference.runs candidate.rows candidate.runs");U w=number(argv[1]),h=number(argv[2]);if(!w||!h||w>1000000||h>1000000)throw std::runtime_error("invalid dimensions");Rows p(argv[3],argv[4],w,h,false),r(argv[5],argv[6],w,h,false),c(argv[7],argv[8],w,h,false);Count matrix[6][6]={},both=0,match=0,reference_water=0,candidate_water=0,both_water=0;for(U y=0;y<h;y++){auto a=p.row(y),b=r.row(y),d=c.row(y);size_t i=0,j=0,k=0;U x=0;while(x<w){auto A=a.at(i),B=b.at(j),D=d.at(k);U end=std::min({A.end,B.end,D.end});if(end<=x)throw std::runtime_error("bad sweep");if(A.value!=1&&A.value!=17)throw std::runtime_error("invalid physical code");if(B.value<1||B.value>22||(B.value>10&&B.value<17))throw std::runtime_error("invalid reference code");if(D.value!=0&&(D.value<17||D.value>22))throw std::runtime_error("invalid candidate code");bool land=A.value==17,bland=B.value>=17;if(land!=(D.value>=17))throw std::runtime_error("candidate physical mismatch");Count n=Count(end)-x;if(land&&bland){both+=n;matrix[B.value-17][D.value-17]+=n;if(B.value==D.value)match+=n;}else if(land)reference_water+=n;else if(bland)candidate_water+=n;else both_water+=n;x=end;if(A.end==x)i++;if(B.end==x)j++;if(D.end==x)k++;}}std::cout<<"{\"both_land\":"<<both<<",\"same_continent\":"<<match<<",\"different_continent\":"<<both-match<<",\"candidate_land_reference_water\":"<<reference_water<<",\"candidate_water_reference_land\":"<<candidate_water<<",\"both_water\":"<<both_water<<",\"reference_to_candidate_17_to_22\":[";for(int i=0;i<6;i++){if(i)std::cout<<",";std::cout<<"[";for(int j=0;j<6;j++){if(j)std::cout<<",";std::cout<<matrix[i][j];}std::cout<<"]";}std::cout<<"]}\n";return 0;}catch(std::exception const&e){std::cerr<<"comparison error: "<<e.what()<<"\n";return 1;}}