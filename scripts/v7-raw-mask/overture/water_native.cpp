// Batch the existing GDAL operations without copying Arrow WKB into Python or
// cloning each geometry into an OGR feature for every tile. Public GDAL C ABI
// declarations keep this helper usable with a runtime-only GDAL installation.
#include <algorithm>
#include <cmath>
#include <chrono>
#include <cstdint>
#include <dlfcn.h>
#include <future>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Envelope { double min_x, max_x, min_y, max_y; };
struct Api {
    void* library = nullptr;
    int (*create_geometry)(const void*, void*, void**, int);
    void (*destroy_geometry)(void*);
    int (*empty)(void*);
    int (*geometry_type)(void*);
    int (*flatten)(int);
    int (*valid)(void*);
    int (*child_count)(void*);
    void* (*child)(void*,int);
    int (*point_count)(void*);
    double (*x)(void*,int);
    double (*y)(void*,int);
    void* (*new_geometry)(int);
    int (*add_geometry)(void*,void*);
    void (*add_point)(void*,double,double);
    void (*envelope)(void*, Envelope*);
    void* (*driver)(const char*);
    void* (*create)(void*, const char*, int, int, int, int, char**);
    int (*transform)(void*, double*);
    void* (*band)(void*, int);
    int (*raster_io)(void*, int, int, int, int, int, void*, int, int, int, int, int);
    int (*rasterize)(void*, int, const int*, int, const void* const*, void*, void*,
                     const double*, char**, void*, void*);
    void (*close)(void*);
    const char* (*version)(const char*);
    template<class T> void load(T& field, const char* name) {
        field = reinterpret_cast<T>(dlsym(library, name));
        if (!field) throw std::runtime_error(std::string("missing GDAL symbol: ") + name);
    }
    void open(const char* path) {
        if (library) return;
        library = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (!library) throw std::runtime_error(dlerror());
        load(create_geometry, "OGR_G_CreateFromWkb");
        load(destroy_geometry, "OGR_G_DestroyGeometry");
        load(empty, "OGR_G_IsEmpty"); load(geometry_type, "OGR_G_GetGeometryType");
        load(flatten, "OGR_GT_Flatten"); load(valid, "OGR_G_IsValid");
        load(child_count,"OGR_G_GetGeometryCount"); load(child,"OGR_G_GetGeometryRef");
        load(point_count,"OGR_G_GetPointCount");load(x,"OGR_G_GetX");load(y,"OGR_G_GetY");
        load(new_geometry,"OGR_G_CreateGeometry");load(add_geometry,"OGR_G_AddGeometryDirectly");
        load(add_point,"OGR_G_AddPoint_2D");
        load(envelope, "OGR_G_GetEnvelope"); load(driver, "GDALGetDriverByName");
        load(create, "GDALCreate"); load(transform, "GDALSetGeoTransform");
        load(band, "GDALGetRasterBand"); load(raster_io, "GDALRasterIO");
        load(rasterize, "GDALRasterizeGeometries"); load(close, "GDALClose");
        load(version, "GDALVersionInfo");
    }
} api;
thread_local std::string error;
struct GeometryDeleter { void operator()(void* p) const { if (p) api.destroy_geometry(p); } };
struct RasterDeleter { void operator()(void* p) const { if (p) api.close(p); } };
using Geometry = std::unique_ptr<void, GeometryDeleter>;
using Raster = std::unique_ptr<void, RasterDeleter>;
struct Tile { int x, y; std::vector<const void*> geometries; };
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }

// Retain every original edge that can intersect this strip. Removing a run of
// vertices strictly above or below it introduces only an outside-strip bridge:
// no visible scanline intersection changes, and every retained coordinate is
// bit-for-bit original. Unlike global VECTOR rasterization, the eventual GDAL
// burn still uses exactly the reference tile-local floating-point transform.
Geometry strip_geometry(void* source,double top,double bottom,double step) {
    const int type=api.flatten(api.geometry_type(source));
    Geometry result(api.new_geometry(type));require(bool(result),"strip geometry creation failed");
    if (type==6) {
        for (int i=0;i<api.child_count(source);++i) {
            auto part=strip_geometry(api.child(source,i),top,bottom,step);
            if (part) {
                require(api.add_geometry(result.get(),part.get())==0,"strip polygon append failed");
                part.release();
            }
        }
        return api.child_count(result.get()) ? std::move(result) : Geometry();
    }
    require(type==3,"unexpected strip geometry type");
    for (int part=0;part<api.child_count(source);++part) {
        void* ring=api.child(source,part);const int count=api.point_count(ring);
        std::vector<unsigned char> keep(count,0);
        for (int j=0;j<count;++j) {
            const int next=(j+1)%count;const double a=api.y(ring,j),b=api.y(ring,next);
            // A complete cell of padding is conservative for center ties and
            // transform roundoff. It affects only pruning, never coordinates.
            if (std::min(a,b)<=top+step && std::max(a,b)>=bottom-step)
                keep[j]=keep[next]=1;
        }
        if (std::find(keep.begin(),keep.end(),1)==keep.end()) {
            if (part==0)return Geometry();
            continue;
        }
        Geometry retained(api.new_geometry(101));require(bool(retained),"strip ring creation failed");
        double first_x=0,first_y=0,last_x=0,last_y=0;bool first=true;
        for (int j=0;j<count;++j) if (keep[j]) {
            const double x=api.x(ring,j),y=api.y(ring,j);api.add_point(retained.get(),x,y);
            if (first) {first_x=x;first_y=y;first=false;}last_x=x;last_y=y;
        }
        if (last_x!=first_x || last_y!=first_y)api.add_point(retained.get(),first_x,first_y);
        require(api.add_geometry(result.get(),retained.get())==0,"strip ring append failed");
        retained.release();
    }
    return result;
}
}

extern "C" const char* water_error() { return error.c_str(); }

extern "C" int water_init(const char* library, const char* version) {
    try {
        api.open(library);
        require(std::string(api.version("VERSION_NUM")) == version, "GDAL runtime version mismatch");
        return 0;
    } catch (const std::exception& e) { error = e.what(); return -1; }
}

// status: 1 polygon, 2 malformed/empty, 3 nonpolygon, 4 invalid polygon,
// 5 null WKB, 6 nonfinite envelope. A positive return is the fatal row + 1.
extern "C" int64_t water_batch(void* raster, const unsigned char* data,
        const void* offsets, int large_offsets, int64_t array_offset,
        const unsigned char* validity, const unsigned char* selected,
        int64_t count, const double* grid, int tile_size, int vector_mode, int validation_threads,
        unsigned char* status, double* timings) {
    try {
        const auto started = std::chrono::steady_clock::now();
        const int width = static_cast<int>(grid[0]), height = static_cast<int>(grid[1]);
        const double west = grid[2], north = grid[3], step = grid[4];
        require(vector_mode==0 || vector_mode==2,"global vector mode does not preserve tile-local pixel-center ties");
        std::vector<Geometry> owned(count);
        std::vector<Envelope> envelopes(count);
        std::vector<Geometry> strip_geometries;
        std::vector<Tile> tiles;
        std::map<std::pair<int,int>, size_t> tile_index;
        // Parsing and GEOS validation are independent per feature. Each task
        // owns separate OGR geometries; only the calling thread uses the raster.
        // Fold results in source order, preserving the first fatal row and all
        // original diagnostic semantics regardless of task completion order.
        auto parse = [&](int64_t i) {
            if (!selected[i]) return;
            const int64_t pos = array_offset + i;
            if (validity && !(validity[pos / 8] & (1u << (pos % 8)))) {
                status[i] = 5; return;
            }
            auto offset = [&](int64_t j) -> int64_t {
                return large_offsets ? static_cast<const int64_t*>(offsets)[j]
                                     : static_cast<const int32_t*>(offsets)[j];
            };
            const int64_t start = offset(pos), length = offset(pos + 1) - start;
            void* raw = nullptr;
            if (length <= 0 || length > std::numeric_limits<int>::max() ||
                    api.create_geometry(data + start, nullptr, &raw, static_cast<int>(length)) != 0) {
                if (raw) api.destroy_geometry(raw);
                status[i] = 2; return;
            }
            Geometry geometry(raw);
            if (!raw || api.empty(raw)) { status[i] = 2; return; }
            const int type = api.flatten(api.geometry_type(raw));
            if (type != 3 && type != 6) { status[i] = 3; return; }
            if (!api.valid(raw)) { status[i] = 4; return; }
            Envelope bounds; api.envelope(raw, &bounds);
            if (!std::isfinite(bounds.min_x) || !std::isfinite(bounds.max_x) ||
                    !std::isfinite(bounds.min_y) || !std::isfinite(bounds.max_y)) {
                status[i] = 6; return;
            }
            owned[i]=std::move(geometry);envelopes[i]=bounds;status[i]=1;
        };
        require(validation_threads>0,"validation thread count must be positive");
        const int threads=static_cast<int>(std::min<int64_t>(validation_threads,count));
        std::vector<std::future<void>> tasks;
        for (int thread=1;thread<threads;++thread) {
            tasks.push_back(std::async(std::launch::async,[&,thread] {
                for (int64_t i=thread;i<count;i+=threads) parse(i);
            }));
        }
        if (threads) for (int64_t i=0;i<count;i+=threads) parse(i);
        for (auto& task:tasks) task.get();
        for (int64_t i=0;i<count;++i) {
            if (status[i]==2 || status[i]==5 || status[i]==6) {
                std::fill(status+i+1,status+count,0);return i+1;
            }
        }
        for (int64_t i=0;i<count;++i) {
            if (status[i]!=1) continue;
            void* raw=owned[i].get();const auto& bounds=envelopes[i];
            const int type=api.flatten(api.geometry_type(raw));
            const double x0 = std::max(0., std::floor((bounds.min_x - west) / step));
            const double x1 = std::min(double(width - 1), std::floor((bounds.max_x - west) / step));
            const double y0 = std::max(0., std::floor((north - bounds.max_y) / step));
            const double y1 = std::min(double(height - 1), std::floor((north - bounds.min_y) / step));
            if (x0 <= x1 && y0 <= y1) {
                // Prune off-strip edges once per geometry/strip, then share that
                // view across longitude tiles. All burns remain tile-local.
                const bool spans_rows=int(y0)/tile_size!=int(y1)/tile_size;
                std::map<int,void*> strips;
                auto add_tile = [&](int tx,int ty) {
                    void* raster_geometry=raw;
                    if (vector_mode==2 && spans_rows) {
                        auto found=strips.find(ty);
                        if (found==strips.end()) {
                            auto view=strip_geometry(raw,north-ty*tile_size*step,
                                north-std::min(height,(ty+1)*tile_size)*step,step);
                            raster_geometry=view.get();strips.emplace(ty,raster_geometry);
                            if (view)strip_geometries.push_back(std::move(view));
                        } else raster_geometry=found->second;
                    }
                    if (!raster_geometry)return;
                    auto key = std::make_pair(tx, ty);
                    auto [it, inserted] = tile_index.emplace(key, tiles.size());
                    if (inserted) tiles.push_back({tx, ty, {}});
                    tiles[it->second].geometries.push_back(raster_geometry);
                };
                if (vector_mode==2 && type==6) {
                    std::set<std::pair<int,int>> candidates;
                    for (int part=0;part<api.child_count(raw);++part) {
                        void* component=api.child(raw,part);
                        if (api.empty(component)) continue;
                        Envelope b;api.envelope(component,&b);
                        const double a=std::max(0.,std::floor((b.min_x-west)/step));
                        const double c=std::min(double(width-1),std::floor((b.max_x-west)/step));
                        const double d=std::max(0.,std::floor((north-b.max_y)/step));
                        const double e=std::min(double(height-1),std::floor((north-b.min_y)/step));
                        if (a<=c && d<=e) {
                            for (int ty=int(d)/tile_size;ty<=int(e)/tile_size;++ty)
                                for (int tx=int(a)/tile_size;tx<=int(c)/tile_size;++tx)
                                    candidates.emplace(ty,tx);
                        }
                    }
                    for (const auto& [ty,tx]:candidates) add_tile(tx,ty);
                } else {
                for (int ty = int(y0) / tile_size; ty <= int(y1) / tile_size; ++ty) {
                    for (int tx = int(x0) / tile_size; tx <= int(x1) / tile_size; ++tx) {
                        add_tile(tx,ty);
                    }
                }
                }
            }
        }
        const auto validated = std::chrono::steady_clock::now();
        timings[0] = std::chrono::duration<double>(validated - started).count();
        for (const auto& tile : tiles) {
            const int x = tile.x * tile_size, y = tile.y * tile_size;
            const int w = std::min(tile_size, width - x), h = std::min(tile_size, height - y);
            std::vector<unsigned char> values(size_t(w) * h);
            require(api.raster_io(api.band(raster, 1), 0, x, y, w, h, values.data(), w, h, 1, 0, 0) == 0,
                    "water tile read failed");
            Raster target(api.create(api.driver("MEM"), "", w, h, 1, 1, nullptr));
            require(bool(target), "water tile creation failed");
            double transform[] = {west + x * step, step, 0., north - y * step, 0., -step};
            require(api.transform(target.get(), transform) == 0, "water tile transform failed");
            require(api.raster_io(api.band(target.get(), 1), 1, 0, 0, w, h, values.data(), w, h, 1, 0, 0) == 0,
                    "water tile initialization failed");
            const int band = 1;
            const std::vector<double> burns(tile.geometries.size(), 1.);
            char raster_option[] = "OPTIM=RASTER";
            char* options[] = {raster_option, nullptr};
            require(tile.geometries.size() <= size_t(std::numeric_limits<int>::max()), "too many tile geometries");
            require(api.rasterize(target.get(), 1, &band, int(tile.geometries.size()),
                    tile.geometries.data(), nullptr, nullptr, burns.data(), options, nullptr, nullptr) == 0,
                    "water geometry rasterization failed");
            require(api.raster_io(api.band(target.get(), 1), 0, 0, 0, w, h, values.data(), w, h, 1, 0, 0) == 0,
                    "water tile result read failed");
            require(api.raster_io(api.band(raster, 1), 1, x, y, w, h, values.data(), w, h, 1, 0, 0) == 0,
                    "water tile write failed");
        }
        timings[1] = std::chrono::duration<double>(std::chrono::steady_clock::now() - validated).count();
        return 0;
    } catch (const std::exception& e) { error = e.what(); return -1; }
}
