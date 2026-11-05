// Exact byte-order authentication of frozen tile index against seed RLE.
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "u32 tile streams require a little-endian host"
#endif
#include <openssl/evp.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
namespace fs=std::filesystem;
void need(bool x,const char*m){if(!x)throw std::runtime_error(m);}
uint64_t available_kib(){std::ifstream f("/proc/meminfo");std::string k,u;uint64_t v;while(f>>k>>v>>u)if(k=="MemAvailable:")return v;throw std::runtime_error("missing MemAvailable");}
struct State{EVP_MD_CTX*ctx=nullptr;uint64_t records=0;};
int main(int argc,char**argv){try{
 need(argc==8,"usage: verify rows runs tile_dir W H tile_size floor_KiB");const std::string rows=argv[1],runs=argv[2],dir=argv[3];const uint32_t W=std::stoul(argv[4]),H=std::stoul(argv[5]),T=std::stoul(argv[6]);const uint64_t floor=std::stoull(argv[7]);need(W>0&&H>0&&T>0,"bad dimensions");uint64_t low=available_kib();auto guard=[&](){auto x=available_kib();low=std::min(low,x);need(x>=floor,"memory guard");};guard();
 FILE*rf=fopen(rows.c_str(),"rb");FILE*sf=fopen(runs.c_str(),"rb");need(rf&&sf,"cannot open input");std::vector<uint32_t> off(H+1);need(fread(off.data(),4,H+1,rf)==H+1&&fgetc(rf)==EOF&&off[0]==0,"bad offsets");fclose(rf);const uint32_t NX=(W+T-1)/T,NY=(H+T-1)/T;std::vector<State> st((size_t)NX*NY);uint64_t records=0;for(uint32_t y=0;y<H;y++){if(y%128==0)guard();need(off[y]<=off[y+1],"nonmonotone offsets");uint32_t start=0,prev=~0u;for(uint32_t i=off[y];i<off[y+1];i++){uint32_t data[2];need(fread(data,4,2,sf)==2,"short runs");uint32_t end=data[0],code=data[1];need(start<end&&end<=W&&code<=22&&(code==0||code>=17)&&code!=prev,"bad seed row");if(code){for(uint32_t x=start;x<end;){uint32_t tx=x/T,z=std::min(end,(tx+1)*T);auto&s=st[(size_t)(y/T)*NX+tx];if(!s.ctx){s.ctx=EVP_MD_CTX_new();need(s.ctx&&EVP_DigestInit_ex(s.ctx,EVP_sha256(),nullptr)==1,"sha init failure");}uint32_t rec[4]={y,x,z,code};need(EVP_DigestUpdate(s.ctx,rec,sizeof rec)==1,"sha update failure");s.records++;records++;x=z;}}start=end;prev=code;}need(start==W,"incomplete row");}need(fgetc(sf)==EOF,"extra runs");fclose(sf);
 std::vector<unsigned char> buf(65536);uint64_t tiles=0;for(uint32_t ty=0;ty<NY;ty++)for(uint32_t tx=0;tx<NX;tx++){auto&s=st[(size_t)ty*NX+tx];char name[64];snprintf(name,sizeof name,"%05u-%05u.bin",ty,tx);fs::path path=fs::path(dir)/name;if(!s.ctx){need(!fs::exists(path),"unexpected tile file");continue;}if(tiles%16==0)guard();need(fs::is_regular_file(path)&&fs::file_size(path)==s.records*16,"missing tile or size mismatch");unsigned char expected[EVP_MAX_MD_SIZE],actual[EVP_MAX_MD_SIZE];unsigned int en=0,an=0;need(EVP_DigestFinal_ex(s.ctx,expected,&en)==1&&en==32,"sha finalize");EVP_MD_CTX_free(s.ctx);EVP_MD_CTX*act=EVP_MD_CTX_new();need(act&&EVP_DigestInit_ex(act,EVP_sha256(),nullptr)==1,"actual init");FILE*fp=fopen(path.c_str(),"rb");need(fp,"tile open");size_t n;while((n=fread(buf.data(),1,buf.size(),fp))>0)need(EVP_DigestUpdate(act,buf.data(),n)==1,"actual update");need(feof(fp),"tile read");fclose(fp);need(EVP_DigestFinal_ex(act,actual,&an)==1&&an==32&&std::equal(expected,expected+32,actual),"tile bytes mismatch");EVP_MD_CTX_free(act);tiles++;}
 for(auto&e:fs::directory_iterator(dir)){auto n=e.path().filename().string();if(e.path().extension()==".bin"){unsigned ty,tx;char extra;need(sscanf(n.c_str(),"%5u-%5u.bin%c",&ty,&tx,&extra)==2&&ty<NY&&tx<NX&&st[(size_t)ty*NX+tx].records>0,"unlisted bin");}}
 std::cout<<"{\"status\":\"verified\",\"tiles\":"<<tiles<<",\"tile_records\":"<<records<<",\"min_mem_available_kib\":"<<low<<"}"<<std::endl;
 return 0;
}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<std::endl;return 1;}}
