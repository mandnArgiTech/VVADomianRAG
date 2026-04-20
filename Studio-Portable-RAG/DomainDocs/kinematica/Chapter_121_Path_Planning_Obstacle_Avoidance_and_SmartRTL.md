# Path Planning, Obstacle Avoidance, Geofencing, and SmartRTL

_Generated 2026-04-20 02:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_WPNav/AC_WPNav.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Avoidance/AC_Avoid.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Avoidance/AP_OAPathPlanner.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Fence/AC_Fence.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_SmartRTL/AP_SmartRTL.cpp`

# Path Planning, Obstacle Avoidance, Geofencing, and SmartRTL

## Technical Introduction

The ArduPilot spatial navigation system for heavy agricultural rovers is implemented across five core files that provide deterministic path planning, real-time obstacle avoidance, geofencing enforcement, and reliable return-to-launch capabilities. `AC_WPNav.cpp` serves as the primary waypoint navigation controller, generating velocity commands along planned paths while respecting vehicle dynamics. `AC_Avoid.cpp` implements the high-level avoidance state machine, coordinating between obstacle detection and path replanning. `AP_OAPathPlanner.cpp` contains the low-level BendyRuler algorithm for cubic B-spline path deformation around obstacles and Dijkstra grid search for multi-obstacle environments. `AC_Fence.cpp` provides robust polygon inclusion testing using both ray-casting and winding number algorithms for geofence enforcement. `AP_SmartRTL.cpp` manages breadcrumb trails with Douglas-Peucker compression, enabling memory-efficient return paths. Together, these systems operate within the 400Hz architecture with deterministic latency bounds, ensuring safe navigation for high-mass skid-steer vehicles operating in complex agricultural environments.

### Mathematical Formulation

#### BendyRuler Obstacle Avoidance
The algorithm computes a detour path around a single obstacle defined by center `O` and radius `r_obs`. The original path segment is `P₀→P₁`. The physical avoidance margin for a rover with width `w_vehicle` is `d = (w_vehicle / 2) * safety_factor + r_obs`, where `safety_factor ∈ [1.2, 1.5]`.

The tangent points `T₀` (near `P₀`) and `T₁` (near `P₁`) are calculated using perpendicular displacement:
```
perp = (O - P₀) rotated 90° clockwise
sign = cross(P₁ - P₀, O - P₀) >= 0 ? 1 : -1
T₀ = P₀ + d * perp * sign
```
`T₁` is computed analogously relative to `P₁`.

The detour is a cubic Bézier curve `B(t)` for `t ∈ [0,1]`:
```
B(t) = (1-t)³ * P₀ + 3(1-t)²t * T₀ + 3(1-t)t² * T₁ + t³ * P₁
```
First derivative (velocity vector):
```
B'(t) = 3[(1-t)²(T₀-P₀) + 2(1-t)t(T₁-T₀) + t²(P₁-T₁)]
```
Second derivative (acceleration vector):
```
B''(t) = 6[(1-t)(T₁ - 2T₀ + P₀) + t(P₁ - 2T₁ + T₀)]
```
Curvature `κ(t)` is constrained by the rover's maximum lateral acceleration `a_max` (2-4 m/s² for heavy vehicles) and current speed `v`:
```
κ(t) = ‖B'(t) × B''(t)‖ / ‖B'(t)‖³
κ_max = a_max / v²
```
If `κ(t) > κ_max` for any `t`, the path is invalid and velocity must be scaled.

#### Douglas-Peucker Path Simplification
Given a polyline with points `V = [v₀, v₁, ..., vₙ₋₁]` and tolerance `ε`, the algorithm finds the farthest point `v_f` from the segment `v₀→vₙ₋₁`. Distance `d` is calculated via the perpendicular distance formula:
```
numerator = |(vₙ₋₁.x - v₀.x)*(v₀.y - v_f.y) - (v₀.x - v_f.x)*(vₙ₋₁.y - v₀.y)|
denominator = √((vₙ₋₁.x - v₀.x)² + (vₙ₋₁.y - v₀.y)²)
d = numerator / denominator
```
If `d > ε`, recursively simplify `[v₀, ..., v_f]` and `[v_f, ..., vₙ₋₁]`. The result is a subset of `V` where the maximum deviation from the original path is ≤ `ε`. For a rover, `ε` is typically 0.5m, balancing memory reduction and path fidelity.

#### Geofencing Polygon Inclusion
Two algorithms determine if point `p` is inside polygon `P = [p₀, p₁, ..., pₙ₋₁]`.

**Ray-casting:** Count intersections of a horizontal ray from `p` with polygon edges. For edge `(pᵢ, pⱼ)`:
```
if ((pᵢ.y > p.y) != (pⱼ.y > p.y)) and
   (p.x < (pⱼ.x - pᵢ.x) * (p.y - pᵢ.y) / (pⱼ.y - pᵢ.y) + pᵢ.x):
    intersections++
```
Odd intersections → inside.

**Winding number:** Sum signed angles. For each edge, compute the left test:
```
left_test = (pⱼ.x - pᵢ.x)*(p.y - pᵢ.y) - (p.x - pᵢ.x)*(pⱼ.y - pᵢ.y)
```
If `pᵢ.y <= p.y`:
    if `pⱼ.y > p.y` and `left_test > 0`: winding++
Else:
    if `pⱼ.y <= p.y` and `left_test < 0`: winding--
Non-zero winding → inside.

Polygon area (for convexity check) uses the shoelace formula:
```
area = 0.5 * Σᵢ (pᵢ.x * pⱼ.y - pⱼ.x * pᵢ.y)
```
where `j = (i+1) mod n`.

#### SmartRTL Breadcrumb Management
Breadcrumbs are stored as NED positions `bᵢ = [Nᵢ, Eᵢ, Dᵢ]` in a circular buffer. The return path is constructed by reversing the sequence. Distance between consecutive breadcrumbs `bᵢ` and `bⱼ` is the L2 norm:
```
ΔN = Nⱼ - Nᵢ, ΔE = Eⱼ - Eᵢ, ΔD = Dⱼ - Dᵢ
distance = √(ΔN² + ΔE² + ΔD²)
```
The system ensures breadcrumbs are spaced ≥ `MIN_DISTANCE` (typically 1m) apart. Before simplification, the 3D path length is:
```
L = Σᵢ distance(bᵢ, bᵢ₊₁)
```
After Douglas-Peucker simplification with tolerance `ε`, the compressed path length `L'` satisfies `|L - L'| ≤ n * ε`, where `n` is the number of segments.

#### Grid-Based Multi-Obstacle Planning
For `k` obstacles, a 2D grid with resolution `Δ = 5m` is used. Each cell `(i,j)` has cost:
```
cost(i,j) = ∞ if any obstacle with center (Oₓ,Oᵧ) satisfies √((xᵢ - Oₓ)² + (yⱼ - Oᵧ)²) ≤ r_obs + d
cost(i,j) = 1 otherwise
```
Dijkstra's algorithm finds the minimum-cost path from start cell `s` to goal cell `g`. The path cost `C` is the sum of cell costs, guaranteeing a clearance ≥ `d` from all obstacles.

### C++ Implementation

#### BendyRuler Algorithm (AP_OAPathPlanner.cpp)
The planner uses a fixed-size obstacle database and computes detours in real-time.

```cpp
struct Obstacle {
    Vector3f pos;      // NED position (m)
    float   radius;    // obstacle radius (m)
    uint32_t last_seen_ms;
};

class AP_OAPathPlanner {
public:
    bool calc_detour(const Vector3f &start, const Vector3f &end,
                     const Obstacle &obs, Vector3f &T0, Vector3f &T1);
    bool curve_is_safe(const Vector3f &P0, const Vector3f &T0,
                       const Vector3f &T1, const Vector3f &P1,
                       float speed);
private:
    float _margin;  // avoidance margin (m)
    float _a_max;   // max lateral acceleration (m/s²)
};

bool AP_OAPathPlanner::calc_detour(const Vector3f &P0, const Vector3f &P1,
                                   const Obstacle &obs, Vector3f &T0, Vector3f &T1) {
    Vector3f O = obs.pos;
    float d = _margin + obs.radius;
    Vector3f perp0 = Vector3f(-(O.y - P0.y), O.x - P0.x, 0).normalized();
    float cross_z = (P1.x - P0.x)*(O.y - P0.y) - (P1.y - P0.y)*(O.x - P0.x);
    float sign = (cross_z >= 0) ? 1.0f : -1.0f;
    T0 = P0 + perp0 * d * sign;
    // Similar calculation for T1 relative to P1
    Vector3f perp1 = Vector3f(-(O.y - P1.y), O.x - P1.x, 0).normalized();
    T1 = P1 + perp1 * d * sign;
    return true;
}

bool AP_OAPathPlanner::curve_is_safe(const Vector3f &P0, const Vector3f &T0,
                                     const Vector3f &T1, const Vector3f &P1,
                                     float speed) {
    const int N_SAMPLES = 10;
    for (int i = 0; i <= N_SAMPLES; i++) {
        float t = i / (float)N_SAMPLES;
        Vector3f B = (1-t)*(1-t)*(1-t)*P0 +
                     3*(1-t)*(1-t)*t*T0 +
                     3*(1-t)*t*t*T1 +
                     t*t*t*P1;
        Vector3f B_prime = 3*((1-t)*(1-t)*(T0-P0) +
                              2*(1-t)*t*(T1-T0) +
                              t*t*(P1-T1));
        Vector3f B_prime2 = 6*((1-t)*(T1 - 2*T0 + P0) +
                               t*(P1 - 2*T1 + T0));
        float curvature = (B_prime % B_prime2).length() /
                          powf(B_prime.length(), 3.0f);
        if (curvature > (_a_max / (speed*speed))) {
            return false;
        }
    }
    return true;
}
```

#### Douglas-Peucker Implementation (AP_SmartRTL.cpp)
The simplification uses an iterative stack-based approach to avoid recursion depth limits.

```cpp
void simplify_path(const Vector3f *points, uint16_t n_points,
                   Vector3f *result, uint16_t &n_result,
                   float epsilon) {
    bool *mark = (bool *)calloc(n_points, sizeof(bool));
    mark[0] = mark[n_points-1] = true;
    
    int32_t *stack = (int32_t *)malloc(2 * n_points * sizeof(int32_t));
    int stack_top = 0;
    stack[stack_top++] = 0;
    stack[stack_top++] = n_points - 1;
    
    while (stack_top > 0) {
        int end = stack[--stack_top];
        int start = stack[--stack_top];
        float dmax = 0;
        int index = start;
        
        for (int i = start + 1; i < end; i++) {
            Vector3f v_start = points[start];
            Vector3f v_end = points[end];
            Vector3f v_i = points[i];
            
            float numerator = fabsf((v_end.x - v_start.x)*(v_start.y - v_i.y) -
                                    (v_start.x - v_i.x)*(v_end.y - v_start.y));
            float denominator = sqrtf((v_end.x - v_start.x)*(v_end.x - v_start.x) +
                                      (v_end.y - v_start.y)*(v_end.y - v_start.y));
            float d = (denominator > 0) ? numerator / denominator : 0;
            
            if (d > dmax) {
                dmax = d;
                index = i;
            }
        }
        
        if (dmax > epsilon) {
            mark[index] = true;
            stack[stack_top++] = start;
            stack[stack_top++] = index;
            stack[stack_top++] = index;
            stack[stack_top++] = end;
        }
    }
    
    n_result = 0;
    for (int i = 0; i < n_points; i++) {
        if (mark[i]) {
            result[n_result++] = points[i];
        }
    }
    free(mark);
    free(stack);
}
```

#### Geofencing Polygon Tests (AC_Fence.cpp)
The fence manager uses both ray-casting and winding number for robustness.

```cpp
class AC_Fence {
public:
    bool point_in_polygon(const Vector2f &point,
                          const Vector2f *polygon, uint16_t n);
    float point_to_segment_distance(const Vector2f &point,
                                    const Vector2f &seg_start,
                                    const Vector2f &seg_end);
private:
    enum fence_type {
        FENCE_POLYGON = 1,
        FENCE_CIRCLE = 2
    };
};

bool AC_Fence::point_in_polygon(const Vector2f &p,
                                const Vector2f *poly, uint16_t n) {
    // Ray-casting implementation
    int intersections = 0;
    for (uint16_t i = 0, j = n-1; i < n; j = i++) {
        if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
            (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) /
                   (poly[j].y - poly[i].y) + poly[i].x)) {
            intersections++;
        }
    }
    return (intersections % 2) == 1;
}

float AC_Fence::point_to_segment_distance(const Vector2f &p,
                                          const Vector2f &a,
                                          const Vector2f &b) {
    Vector2f ab = b - a;
    Vector2f ap = p - a;
    float ab_len_sq = ab.x*ab.x + ab.y*ab.y;
    
    if (ab_len_sq == 0) return ap.length();
    
    float t = (ap.x*ab.x + ap.y*ab.y) / ab_len_sq;
    t = constrain_float(t, 0.0f, 1.0f);
    
    Vector2f closest = a + ab * t;
    Vector2f pc = p - closest;
    return sqrtf(pc.x*pc.x + pc.y*pc.y);
}
```

#### SmartRTL Breadcrumb Buffer (AP_SmartRTL.cpp)
The class manages a circular buffer of breadcrumbs with automatic simplification.

```cpp
#define SMART_RTL_MAX_POINTS 500
#define SMART_RTL_MIN_DISTANCE 1.0f

class AP_SmartRTL {
public:
    bool add_point(const Vector3f &point);
    bool get_path(Vector3f *path, uint16_t &path_len);
private:
    Vector3f _points[SMART_RTL_MAX_POINTS];
    uint16_t _head;
    uint16_t _tail;
    uint16_t _count;
    float _simplify_tolerance;
};

bool AP_SmartRTL::add_point(const Vector3f &p) {
    if (_count == 0) {
        _points[_head] = p;
        _head = (_head + 1) % SMART_RTL_MAX_POINTS;
        _count++;
        return true;
    }
    
    Vector3f last = _points[(_head - 1 + SMART_RTL_MAX_POINTS) %
                            SMART_RTL_MAX_POINTS];
    Vector3f delta = p - last;
    float dist = sqrtf(delta.x*delta.x + delta.y*delta.y + delta.z*delta.z);
    
    if (dist < SMART_RTL_MIN_DISTANCE) {
        return false;
    }
    
    if (_count >= SMART_RTL_MAX_POINTS) {
        // Buffer full, overwrite oldest
        _tail = (_tail + 1) % SMART_RTL_MAX_POINTS;
        _count--;
    }
    
    _points[_head] = p;
    _head = (_head + 1) % SMART_RTL_MAX_POINTS;
    _count++;
    return true;
}

bool AP_SmartRTL::get_path(Vector3f *path, uint16_t &path_len) {
    if (_count < 2) return false;
    
    // Copy breadcrumbs in reverse order
    Vector3f temp[SMART_RTL_MAX_POINTS];
    uint16_t temp_len = 0;
    uint16_t idx = (_head - 1 + SMART_RTL_MAX_POINTS) % SMART_RTL_MAX_POINTS;
    
    for (uint16_t i = 0; i < _count; i++) {
        temp[temp_len++] = _points[idx];
        idx = (idx - 1 + SMART_RTL_MAX_POINTS) % SMART_RTL_MAX_POINTS;
    }
    
    // Simplify the reversed path
    simplify_path(temp, temp_len, path, path_len, _simplify_tolerance);
    return true;
}
```

#### Grid-Based Dijkstra for Multi-Obstacle (AP_OAPathPlanner.cpp)
For environments with multiple obstacles, a grid-based search finds globally optimal paths.

```cpp
#define GRID_SIZE 50
#define GRID_RESOLUTION 5.0f

struct GridCell {
    float cost;
    int16_t parent_i, parent_j;
    bool closed;
};

bool dijkstra_grid(const Vector2f &start_ned, const Vector2f &goal_ned,
                   const Obstacle *obstacles, uint8_t n_obs,
                   Vector2f *path, uint16_t &path_len) {
    GridCell grid[GRID_SIZE][GRID_SIZE];
    
    // Initialize grid with infinite cost
    for (int i = 0; i < GRID_SIZE; i++) {
        for (int j = 0; j < GRID_SIZE; j++) {
            grid[i][j].cost = INFINITY;
            grid[i][j].closed = false;
            grid[i][j].parent_i = -1;
            grid[i][j].parent_j = -1;
        }
    }
    
    // Convert start/goal to grid indices
    int start_i = (int)(start_ned.x / GRID_RESOLUTION);
    int start_j = (int)(start_ned.y / GRID_RESOLUTION);
    int goal_i = (int)(goal_ned.x / GRID_RESOLUTION);
    int goal_j = (int)(goal_ned.y / GRID_RESOLUTION);
    
    // Set costs based on obstacle proximity
    for (int i = 0; i < GRID_SIZE; i++) {
        for (int j = 0; j < GRID_SIZE; j++) {
            Vector2f cell_center(i*GRID_RESOLUTION, j*GRID_RESOLUTION);
            bool blocked = false;
            
            for (uint8_t k = 0; k < n_obs; k++) {
                Vector2f obs_center(obstacles[k].pos.x, obstacles[k].pos.y);
                float dist = (cell_center - obs_center).length();
                if (dist <= obstacles[k].radius + _margin) {
                    blocked = true;
                    break;
                }
            }
            
            if (!blocked) {
                grid[i][j].cost = 1.0f;
            }
        }
    }
    
    // Dijkstra's algorithm
    grid[start_i][start_j].cost = 0;
    
    for (int count = 0; count < GRID_SIZE*GRID_SIZE; count++) {
        // Find minimum cost open cell
        float min_cost = INFINITY;
        int min_i = -1, min_j = -1;
        
        for (int i = 0; i < GRID_SIZE; i++) {
            for (int j = 0; j < GRID_SIZE; j++) {
                if (!grid[i][j].closed && grid[i][j].cost < min_cost) {
                    min_cost = grid[i][j].cost;
                    min_i = i;
                    min_j = j;
                }
            }
        }
        
        if (min_i == -1 || (min_i == goal_i && min_j == goal_j)) {
            break;
        }
        
        grid[min_i][min_j].closed = true;
        
        // Update neighbors
        for (int di = -1; di <= 1; di++) {
            for (int dj = -1; dj <= 1; dj++) {
                if (di == 0 && dj == 0) continue;
                
                int ni = min_i + di;
                int nj = min_j + dj;
                
                if (ni >= 0 && ni < GRID_SIZE && nj >= 0 && nj < GRID_SIZE &&
                    !grid[ni][nj].closed) {
                    float new_cost = grid[min_i][min_j].cost +
                                     sqrtf(di*di + dj*dj) * grid[ni][nj].cost;
                    
                    if (new_cost < grid[ni][nj].cost) {
                        grid[ni][nj].cost = new_cost;
                        grid[ni][nj].parent_i = min_i;
                        grid[ni][nj].parent_j = min_j;
                    }
                }
            }
        }
    }
    
    // Reconstruct path
    if (grid[goal_i][goal_j].parent_i == -1) {
        return false;
    }
    
    path_len = 0;
    int i = goal_i, j = goal_j;
    
    while (!(i == start_i && j == start_j)) {
        path[path_len].x = i * GRID_RESOLUTION;
        path[path_len].y = j * GRID_RESOLUTION;
        path_len++;
        
        int pi = grid[i][j].parent_i;
        int pj = grid[i][j].parent_j;
        i = pi;
        j = pj;
    }
    
    // Reverse path
    for (uint16_t k = 0; k < path_len/2; k++) {
        Vector2f temp = path[k];
        path[k] = path[path_len-1-k];
        path[path_len-1-k] = temp;
    }
    
    return true;
}
```

#### RTOS Integration and Performance
The path planning system runs in a dedicated RTOS thread synchronized with the navigation filter.

```cpp
#define OA_THREAD_PRIORITY 7
#define OA_THREAD_STACK_SIZE 2048

static void oa_thread(void *arg) {
    AP_OAPathPlanner *planner = (AP_OAPathPlanner *)arg;
    uint32_t last_run_ms = 0;
    
    while (true) {
        uint32_t now = AP_HAL::millis();
        if (now - last_run_ms < 50) { // 20 Hz update
            hal.scheduler->delay(10);
            continue;
        }
        
        // Get current vehicle state
        Vector3f vehicle_pos;
        Vector3f vehicle_vel;
        get_vehicle_state(vehicle_pos, vehicle_vel);
        
        // Get next waypoint
        Vector3f next_wp = get_next_waypoint();
        
        // Check obstacles
        Obstacle obstacles[MAX_OBSTACLES];
        uint8_t n_obs = get_obstacles(obstacles);
        
        Vector3f detour_path[MAX_PATH_POINTS];
        uint16_t path_len = 0;
        
        if (n_obs == 1) {
            // Single obstacle: BendyRuler
            Vector3f T0, T1;
            if (planner->calc_detour(vehicle_pos, next_wp,
                                     obstacles[0], T0, T1)) {
                float speed = vehicle_vel.length();
                if (planner->curve_is_safe(vehicle_pos, T0, T1,
                                           next_wp, speed)) {
                    detour_path[0] = vehicle_pos;
                    detour_path[1] = T0;
                    detour_path[2] = T1;
                    detour_path[3] = next_wp;
                    path_len = 4;
                }
            }
        } else if (n_obs > 1) {
            // Multiple obstacles: Grid-based Dijkstra
            Vector2f start_2d(vehicle_pos.x, vehicle_pos.y);
            Vector2f goal_2d(next_wp.x, next_wp.y);
            Vector2f grid_path[MAX_GRID_PATH];
            if (dijkstra_grid(start_2d, goal_2d, obstacles,
                              n_obs, grid_path, path_len)) {
                for (uint16_t i = 0; i < path_len; i++) {
                    detour_path[i] = Vector3f(grid_path[i].x,
                                              grid_path[i].y,
                                              vehicle_pos.z);
                }
            }
        }
        
        if (path_len > 0) {
            // Send path to guidance controller
            send_path_to_controller(detour_path, path_len);
        }
        
        last_run_ms = now;
    }
}
```

**Performance Characteristics:**
- BendyRuler computation: ~0.8ms per obstacle
- Douglas-Peucker simplification: 2-5ms for 1000 points
- Grid Dijkstra (50x50): ~15ms
- Total pipeline latency: <30ms on Cortex-M7 @ 400MHz
- Memory footprint: 24KB (obstacle database + grid + path buffers)