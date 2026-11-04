// Four-neighbor shortest path through an explicit local water mask; research only.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
int main(int argc,char** argv){try{
 if(argc!=9)throw std::runtime_error("mask width height sx sy tx ty output");
 auto val=[&](int i){std::size_t n=0;auto v=std::stoull(argv[i],&n);if(n!=std::string(argv[i]).size())throw std::runtime_error("bad integer");return v;};
 auto w=val(2),h=val(3),sx=val(4),sy=val(5),tx=val(6),ty=val(7);
 if(!w||!h||w>UINT32_MAX||h>UINT32_MAX||w>INT32_MAX/h||sx>=w||tx>=w||sy>=h||ty>=h)throw std::runtime_error("invalid dimensions or endpoints");
 std::size_t n=w*h;std::vector<uint8_t> land(n);std::ifstream in(argv[1],std::ios::binary);in.read(reinterpret_cast<char*>(land.data()),n);
 if(!in||in.peek()!=std::char_traits<char>::eof()||std::any_of(land.begin(),land.end(),[](auto x){return x>1;}))throw std::runtime_error("invalid binary mask");
 int32_t start=sy*w+sx,end=ty*w+tx;if(land[start]||land[end])throw std::runtime_error("endpoint not water");
 std::vector<int32_t> prev(n,-1),queue(n);std::size_t head=0,tail=0;prev[start]=start;queue[tail++]=start;
 while(head<tail&&prev[end]==-1){int32_t z=queue[head++],x=z%w,y=z/w;auto add=[&](int xx,int yy){if(xx<0||yy<0||xx>=static_cast<int>(w)||yy>=static_cast<int>(h))return;int32_t p=yy*w+xx;if(!land[p]&&prev[p]<0){prev[p]=z;queue[tail++]=p;}};add(x-1,y);add(x,y+1);add(x,y-1);add(x+1,y);}
 if(prev[end]==-1)throw std::runtime_error("no water path");
 std::vector<uint32_t> path;for(int32_t z=end;;z=prev[z]){path.push_back(z);if(z==start)break;}std::reverse(path.begin(),path.end());
 std::ofstream out(argv[8],std::ios::binary);out.write(reinterpret_cast<const char*>(path.data()),path.size()*4);if(!out)throw std::runtime_error("route write failure");std::cerr<<"visited "<<tail<<", path cells "<<path.size()<<"\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
