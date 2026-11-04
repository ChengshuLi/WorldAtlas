// Exact discrete grid-run minimum haversine values, per mainland category.
// No geography decisions are encoded here. Fixed-grid lookup tables are
// computed by the caller; all lengths and values are validated there.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
extern "C" void nearest_haversines(const uint32_t *p, size_t n, uint32_t y,
        uint32_t a, uint32_t b, uint32_t width, const double *sin2,
        const double *coslat, double *best) {
    for (size_t i=0;i<n;++i) {
        const uint32_t yy=p[4*i], left=p[4*i+1], right=p[4*i+2]-1, category=p[4*i+3];
        int64_t shortest=width;
        for (int64_t shift: {-(int64_t)width, (int64_t)0, (int64_t)width}) {
            const int64_t x1=(int64_t)left+shift, x2=(int64_t)right+shift;
            const int64_t d=std::max<int64_t>(0,std::max(x1-((int64_t)b-1),(int64_t)a-x2));
            shortest=std::min(shortest,d);
        }
        const uint32_t dy=(yy>y)?yy-y:y-yy;
        const double hav=sin2[dy]+coslat[y]*coslat[yy]*sin2[shortest];
        if (category>=17 && category<=22) best[category-17]=std::min(best[category-17],hav);
    }
}
