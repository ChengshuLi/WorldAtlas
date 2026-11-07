// Independent physical-mask connected-component inventory. No continent data is read.
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "component streams require a little-endian host"
#endif
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
struct Run { uint32_t start, end, node; };
struct DSU {
    vector<uint32_t> p, size;
    uint32_t add() {
        if (p.size() == numeric_limits<uint32_t>::max()) throw runtime_error("too many nodes");
        auto id = uint32_t(p.size()); p.push_back(id); size.push_back(1); return id;
    }
    uint32_t find(uint32_t x) { while (p[x] != x) { p[x] = p[p[x]]; x = p[x]; } return x; }
    void unite(uint32_t a, uint32_t b) {
        a=find(a); b=find(b); if (a==b) return;
        if (size[a]<size[b]) swap(a,b);
        p[b]=a; size[a]+=size[b];
    }
};
vector<uint32_t> read_u32(const string &path) {
    ifstream f(path,ios::binary|ios::ate); if (!f) throw runtime_error("cannot open "+path);
    auto n=f.tellg(); if (n<0 || n%4) throw runtime_error("invalid u32 file "+path);
    vector<uint32_t> v(size_t(n)/4); f.seekg(0); f.read((char*)v.data(), n);
    if (!f) throw runtime_error("short read "+path);
    return v;
}
void write_u32(const string &path, const vector<uint32_t> &v) {
    ifstream exists(path,ios::binary); if(exists) throw runtime_error("output exists "+path);
    ofstream out(path,ios::binary); if(!out) throw runtime_error("cannot create "+path);
    out.write((const char*)v.data(), v.size()*sizeof(uint32_t)); if(!out) throw runtime_error("write failed "+path);
}
int main(int argc,char **argv) try {
    if (argc!=7) throw runtime_error("usage: build_components WIDTH HEIGHT physical_rows physical_runs output_rows output_runs");
    auto w=stoul(argv[1]), h=stoul(argv[2]); if(!w||!h||w>UINT32_MAX||h>UINT32_MAX) throw runtime_error("invalid dimensions");
    auto rows=read_u32(argv[3]), runs=read_u32(argv[4]);
    if(rows.size()!=h+1 || rows.front()!=0 || runs.size()%2 || rows.back()!=runs.size()/2) throw runtime_error("invalid stream lengths");
    DSU d; vector<Run> prev, cur; vector<vector<Run>> all; all.reserve(h); uint64_t cells=0;
    for(uint32_t y=0;y<h;++y){
        if(rows[y]>rows[y+1] || rows[y+1]>runs.size()/2) throw runtime_error("nonmonotonic row offsets");
        cur.clear(); uint32_t x=0, last_code=0;
        for(uint32_t i=rows[y];i<rows[y+1];++i){
            uint32_t end=runs[2*i], code=runs[2*i+1];
            if(end<=x || end>w || (code!=1 && code!=17) || code==last_code) throw runtime_error("invalid or noncanonical physical run");
            last_code=code;
            if(code==17){ cur.push_back({x,end,d.add()}); cells+=end-x; } x=end;
        }
        if(x!=w) throw runtime_error("incomplete physical row");
        size_t i=0,j=0;
        while(i<prev.size() && j<cur.size()){
            if(max(prev[i].start,cur[j].start)<min(prev[i].end,cur[j].end)) d.unite(prev[i].node,cur[j].node);
            if(prev[i].end<cur[j].end) ++i; else ++j;
        }
        if(!cur.empty() && cur.front().start==0 && cur.back().end==w) d.unite(cur.front().node,cur.back().node);
        all.push_back(cur); prev=cur;
    }
    vector<uint32_t> outrows(h+1), outruns; if(d.p.size()>UINT32_MAX) throw runtime_error("too many runs");
    outruns.reserve(d.p.size()*3);
    for(uint32_t y=0;y<h;++y){ outrows[y+1]=outrows[y]+all[y].size();
        for(auto &r:all[y]) { outruns.push_back(r.start); outruns.push_back(r.end); outruns.push_back(d.find(r.node)); }
    }
    write_u32(argv[5],outrows); write_u32(argv[6],outruns);
    uint64_t components=0; for(uint32_t i=0;i<d.p.size();++i) if(d.find(i)==i) ++components;
    cout<<"runs="<<d.p.size()<<" components="<<components<<" land_cells="<<cells<<"\n";
    return 0;
} catch(const exception &e) { cerr<<"error: "<<e.what()<<"\n"; return 1; }
