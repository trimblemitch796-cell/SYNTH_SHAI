#include "SingleModelCache.h"
#include <cassert>
struct Model { int id; };
int main() {
    int live = 0, loads = 0, frees = 0;
    auto destroy = [&](Model* p) { --live; ++frees; delete p; };
    shai::SingleModelCache<Model, decltype(destroy)> cache(destroy);
    auto load = [&]() { assert(live == 0); ++live; ++loads; return new Model{loads}; };
    auto first = cache.get("verified-a", load);
    assert(cache.get("verified-a", load) == first && loads == 1);
    assert(cache.get("verified-b", load)->id == 2 && live == 1 && frees == 1);
    cache.clear(); // Background/memory-pressure release.
    assert(live == 0 && frees == 2);
    cache.clear();
    assert(frees == 2);
    assert(cache.get("verified-b", []() -> Model* { return nullptr; }) == nullptr);
    assert(cache.get("verified-b", load)->id == 3); // Failure never becomes a cache hit.
    cache.clear();
    assert(live == 0 && loads == frees);
}
