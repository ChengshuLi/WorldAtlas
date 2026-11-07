// WGS84-weighted shortest path over four-neighbor physical-water cells.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv){try{
 if(argc!=11)throw std::runtime_error("mask width height sx sy tx ty east-costs north-costs output");
 auto val=[&](int i){std::size_t n=0;auto v=std::stoull(argv[i],&n);if(n!=std::string(argv[i]).size())throw std::runtime_error("bad integer");return v;};
 auto w=val(2),h=val(3),sx=val(4),sy=val(5),tx=val(6),ty=val(7);
 if(!w||!h||w>UINT32_MAX||h>UINT32_MAX||w>INT32_MAX/h||sx>=w||tx>=w||sy>=h||ty>=h)throw std::runtime_error("invalid dimensions or endpoints");
 std::size_t n=w*h;std::vector<uint8_t> land(n);std::ifstream in(argv[1],std::ios::binary);in.read(reinterpret_cast<char*>(land.data()),n);
 if(!in||in.peek()!=std::char_traits<char>::eof()||std::any_of(land.begin(),land.end(),[](auto x){return x>1;}))throw std::runtime_error("invalid binary mask");
 auto read_costs=[](const char* path,std::size_t count){std::vector<uint64_t> v(count);std::ifstream f(path,std::ios::binary);f.read(reinterpret_cast<char*>(v.data()),static_cast<std::streamsize>(count*sizeof(uint64_t)));if(!f||f.peek()!=std::char_traits<char>::eof()||std::any_of(v.begin(),v.end(),[](auto x){return x==0;}))throw std::runtime_error("invalid WGS84 edge-cost table");return v;};
 auto east=read_costs(argv[8],h),north=read_costs(argv[9],h-1);
 uint32_t start=static_cast<uint32_t>(sy*w+sx),end=static_cast<uint32_t>(ty*w+tx);if(land[start]||land[end])throw std::runtime_error("endpoint not water");
 const uint64_t inf=std::numeric_limits<uint64_t>::max();
 std::vector<uint64_t> dist(n,inf);std::vector<int32_t> prev(n,-1),heap(n,-1),position(n,-1);std::size_t used=0;
 auto less=[&](int32_t a,int32_t b){return dist[static_cast<uint32_t>(a)]<dist[static_cast<uint32_t>(b)]||(dist[static_cast<uint32_t>(a)]==dist[static_cast<uint32_t>(b)]&&a<b);};
 auto swap_heap=[&](std::size_t a,std::size_t b){std::swap(heap[a],heap[b]);position[static_cast<uint32_t>(heap[a])]=static_cast<int32_t>(a);position[static_cast<uint32_t>(heap[b])]=static_cast<int32_t>(b);};
 auto sift_up=[&](std::size_t i){while(i){std::size_t p=(i-1)/2;if(!less(heap[i],heap[p]))break;swap_heap(i,p);i=p;}};
 auto sift_down=[&](std::size_t i){for(;;){std::size_t l=2*i+1,r=l+1,b=i;if(l<used&&less(heap[l],heap[b]))b=l;if(r<used&&less(heap[r],heap[b]))b=r;if(b==i)break;swap_heap(i,b);i=b;}};
 auto push_or_decrease=[&](uint32_t node){int32_t p=position[node];if(p==-2)return;if(p<0){heap[used]=static_cast<int32_t>(node);position[node]=static_cast<int32_t>(used);sift_up(used++);}else sift_up(static_cast<std::size_t>(p));};
 auto pop=[&](){uint32_t out=static_cast<uint32_t>(heap[0]);position[out]=-2;--used;if(used){heap[0]=heap[used];position[static_cast<uint32_t>(heap[0])]=0;sift_down(0);}return out;};
 dist[start]=0;push_or_decrease(start);
 while(used){uint32_t z=pop();if(z==end)break;uint32_t x=z%w,y=z/w;
  auto relax=[&](uint32_t p,uint64_t cost){if(land[p]||position[p]==-2)return;if(dist[z]>inf-cost)return;uint64_t nd=dist[z]+cost;
   if(nd<dist[p]){dist[p]=nd;prev[p]=static_cast<int32_t>(z);push_or_decrease(p);}
   else if(nd==dist[p]&&(prev[p]<0||z<static_cast<uint32_t>(prev[p])))prev[p]=static_cast<int32_t>(z);
  };
  if(x>0)relax(z-1,east[y]);
  if(x+1<w)relax(z+1,east[y]);
  if(y>0)relax(z-w,north[y-1]);
  if(y+1<h)relax(z+w,north[y]);
 }
 if(position[end]!=-2)throw std::runtime_error("no water path");
 std::vector<uint32_t> path;for(uint32_t z=end;;z=static_cast<uint32_t>(prev[z])){path.push_back(z);if(z==start)break;if(prev[z]<0)throw std::runtime_error("broken predecessor chain");}std::reverse(path.begin(),path.end());
 std::ofstream out(argv[10],std::ios::binary);out.write(reinterpret_cast<const char*>(path.data()),static_cast<std::streamsize>(path.size()*sizeof(uint32_t)));if(!out)throw std::runtime_error("route write failure");std::cout<<dist[end]<<"\n";std::cerr<<"visited weighted nodes, path cells "<<path.size()<<"\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
