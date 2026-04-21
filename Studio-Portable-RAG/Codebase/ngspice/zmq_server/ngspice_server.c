/*
 * ngspice-server — ZMQ ROUTER (SimRequest / BatchSimRequest) + PUB (DiagEvent protobuf).
 * REQ clients remain compatible. Async worker pool with bounded admission queue.
 */

#define _GNU_SOURCE
#include <ctype.h>
#include <errno.h>
#include <signal.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#include <netinet/in.h>

#include <zmq.h>

#include "ngspice_sim.pb-c.h"
#include "ngspice/diaghooks.h"
#include "ngspice/sharedspice.h"

/* Request id for DiagEvent (mirrors ngspice_diag_request_id for protobuf only). */
static const char *server_diag_request_id = "";

#define WIRE_SIM   1
#define WIRE_BATCH 2
#define WIRE_STATS 3
#define LOG_CAP    131072
#define POOL_MAX   64
#define DEFAULT_ADMIT_CAP 1024
#define DEFAULT_WORKER_CAP 50

/* ngspice ZMQ server wire/API version (bump when proto or behavior changes). */
#define NG_SERVER_VERSION "1.2.0"

/* Shared-spice vector capture for .tran / .ac / .dc (SendInitData / SendData). */
#define MAX_VECS      256
#define VEC_GROW      4096
#define MAX_VEC_NPTS  4000000

static int vec_capture_enabled;
static int vec_count;
static char *vec_names[MAX_VECS];
static int vec_is_complex[MAX_VECS];
static double *vec_real[MAX_VECS];
static double *vec_imag[MAX_VECS];
static int vec_npts;
static int vec_cap;

/*
 * libngspice may reference hcomp() from frontend command sorting, but the
 * object is not always linked into the shared library. Provide a stub so
 * the dynamic loader can resolve the symbol (unused in server-only flows).
 */
int
hcomp(const void *a, const void *b)
{
    (void) a;
    (void) b;
    return 0;
}

static volatile sig_atomic_t stop_server;
static volatile sig_atomic_t sigchld_pending;
static void *zmq_ctx;
static void *sock_router;
static void *sock_pub;
/* Worker processes PUSH packed DiagEvent here; master forwards to sock_pub. */
static void *sock_worker_diag_push;
static void *sock_res_pull;
static void *sock_diag_pull;
static int pool_size = 4;
static size_t admit_cap = DEFAULT_ADMIT_CAP;
static void **worker_push_socks;
static pid_t *worker_pids;
typedef struct BatchPending {
    uint8_t *rid;
    size_t rid_len;
    Ngspice__BatchSimRequest *batch;
    size_t n;
    size_t next_send;
    int remaining;
    Ngspice__SimResult **slots;
    struct timespec t0;
} BatchPending;
typedef struct {
    int active; /* 0 idle, 1 sim, 2 batch slot */
    uint32_t seq;
    uint8_t *rid;
    size_t rid_len;
    char *req_label; /* sim: request_id for timeout reply; batch slots NULL */
    int64_t deadline_mono_ns; /* 0 = unset */
    BatchPending *bp;
    size_t batch_idx;
} worker_state_t;
static worker_state_t *worker_states;
typedef struct {
    uint8_t *rid;
    size_t rid_len;
    uint8_t *payload;
    size_t paylen;
} admit_entry_t;
static admit_entry_t *admit_q;
static size_t admit_head;
static size_t admit_tail;
static size_t admit_count;
static uint32_t seq_gen;
static pid_t server_master_pid;
static double request_timeout_sec = 300.0;
static uint64_t stat_requests_completed;
static uint64_t stat_server_busy_replies;
static uint64_t stat_worker_restarts;
static uint64_t stat_request_timeouts;
static int64_t sim_t0_us;
static int nr_emit_count;

static char logbuf[LOG_CAP];
static size_t loglen;

static int
send_char(char *str, int id, void *ctx)
{
    size_t l;
    const char *s = str;

    (void) id;
    (void) ctx;
    if (!str)
        return 0;
    /* sharedspice prefixes lines so low-latency callbacks can tell streams apart */
    if (strncmp(s, "stdout ", 7) == 0)
        s += 7;
    else if (strncmp(s, "stderr ", 7) == 0)
        s += 7;
    l = strlen(s);
    if (loglen + l >= LOG_CAP - 1)
        return 0;
    memcpy(logbuf + loglen, s, l);
    loglen += l;
    logbuf[loglen] = '\0';
    return 0;
}

static int send_stat(char *str, int p, void *ctx)
{
    (void) str;
    (void) p;
    (void) ctx;
    return 0;
}

static int
ngexit(int status, bool immediate, bool quit, int ident, void *userdata)
{
    (void) status;
    (void) immediate;
    (void) quit;
    (void) ident;
    (void) userdata;
    return 0;
}

static void
vec_accum_reset(void)
{
    int i;

    vec_capture_enabled = 0;
    for (i = 0; i < MAX_VECS; i++) {
        free(vec_names[i]);
        vec_names[i] = NULL;
        free(vec_real[i]);
        vec_real[i] = NULL;
        free(vec_imag[i]);
        vec_imag[i] = NULL;
        vec_is_complex[i] = 0;
    }
    vec_count = 0;
    vec_npts = 0;
    vec_cap = 0;
}

static int
send_data(pvecvaluesall data, int n, int ident, void *ctx)
{
    int i;
    int newcap;
    size_t newsz;

    (void) n;
    (void) ident;
    (void) ctx;
    if (!vec_capture_enabled || !data || vec_count <= 0)
        return 0;
    if (vec_npts >= MAX_VEC_NPTS)
        return 0;
    if (vec_npts >= vec_cap) {
        newcap = vec_cap ? vec_cap * 2 : VEC_GROW;
        newsz = (size_t) newcap * sizeof(double);
        for (i = 0; i < vec_count; i++) {
            double *nr = realloc(vec_real[i], newsz);

            if (!nr)
                return 0;
            vec_real[i] = nr;
            if (vec_is_complex[i]) {
                double *ni = realloc(vec_imag[i], newsz);

                if (!ni)
                    return 0;
                vec_imag[i] = ni;
            }
        }
        vec_cap = newcap;
    }
    for (i = 0; i < vec_count && i < (int) data->veccount; i++) {
        pvecvalues pv = data->vecsa[i];

        if (!pv)
            continue;
        vec_real[i][vec_npts] = pv->creal;
        if (vec_is_complex[i] && vec_imag[i])
            vec_imag[i][vec_npts] = pv->cimag;
    }
    vec_npts++;
    return 0;
}

static int
send_initdata(pvecinfoall iv, int ident, void *ctx)
{
    int i;

    (void) ident;
    (void) ctx;
    if (!vec_capture_enabled || !iv || !iv->vecs)
        return 0;
    for (i = 0; i < vec_count; i++) {
        free(vec_names[i]);
        vec_names[i] = NULL;
        free(vec_real[i]);
        vec_real[i] = NULL;
        free(vec_imag[i]);
        vec_imag[i] = NULL;
    }
    vec_npts = 0;
    vec_cap = 0;
    vec_count = iv->veccount > MAX_VECS ? MAX_VECS : (int) iv->veccount;
    for (i = 0; i < vec_count; i++) {
        const char *nm = "_";

        if (iv->vecs[i] && iv->vecs[i]->vecname && iv->vecs[i]->vecname[0])
            nm = iv->vecs[i]->vecname;
        vec_names[i] = strdup(nm);
        if (!vec_names[i])
            return 0;
        vec_is_complex[i] =
            (iv->vecs[i] && !iv->vecs[i]->is_real) ? 1 : 0; /* 1 = complex */
        vec_real[i] = NULL;
        vec_imag[i] = NULL;
    }
    return 0;
}

static int bg_thread(bool noruns, int ident, void *ctx)
{
    (void) noruns;
    (void) ident;
    (void) ctx;
    return 0;
}

static int64_t
now_us(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return 0;
    return (int64_t) ts.tv_sec * 1000000 + (int64_t) ts.tv_nsec / 1000;
}

static void
pub_diag(Ngspice__DiagEvent *ev)
{
    size_t sz;
    uint8_t *buf;
    void *pub;

    pub = sock_worker_diag_push ? sock_worker_diag_push : sock_pub;
    if (!pub || !ev)
        return;
    if (!ev->request_id)
        ev->request_id = (char *) "";
    ev->timestamp_us = now_us() - sim_t0_us;
    sz = ngspice__diag_event__get_packed_size(ev);
    buf = malloc(sz);
    if (!buf)
        return;
    ngspice__diag_event__pack(ev, buf);
    {
        const char *topic =
            (ev->request_id && ev->request_id[0]) ? ev->request_id : "default";
        size_t tlen = strlen(topic);

        (void) zmq_send(pub, topic, tlen, ZMQ_SNDMORE | ZMQ_DONTWAIT);
        (void) zmq_send(pub, buf, sz, ZMQ_DONTWAIT);
    }
    free(buf);
}

static void
on_nr_iter(void *ctx, int iter, double max_rhs, double max_dx, double damp,
           int noncon, int converged)
{
    Ngspice__NRIteration nr = NGSPICE__NRITERATION__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    nr_emit_count++;
    nr.iter = iter;
    nr.max_rhs = max_rhs;
    nr.max_dx = max_dx;
    nr.damp = damp;
    nr.noncon = noncon;
    nr.converged = converged != 0;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.timestamp_us = 0;
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_NR_ITER;
    ev.nr_iter = &nr;
    pub_diag(&ev);
}

static void
on_limiter_pnj(void *ctx, const char *instance, double vnew_raw, double vnew_lim,
             double vold, double vcrit)
{
    Ngspice__LimiterActivation lim = NGSPICE__LIMITER_ACTIVATION__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    lim.function = (char *) "DEVpnjlim";
    lim.instance = (char *) (instance && instance[0] ? instance : "");
    lim.vnew_raw = vnew_raw;
    lim.vnew_limited = vnew_lim;
    lim.vold = vold;
    lim.vcrit = vcrit;
    lim.vto = 0.0;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_LIMITER;
    ev.limiter = &lim;
    pub_diag(&ev);
}

static void
on_limiter_fet(void *ctx, const char *instance, double vnew_raw, double vnew_lim,
               double vold, double vto)
{
    Ngspice__LimiterActivation lim = NGSPICE__LIMITER_ACTIVATION__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    lim.function = (char *) "DEVfetlim";
    lim.instance = (char *) (instance && instance[0] ? instance : "");
    lim.vnew_raw = vnew_raw;
    lim.vnew_limited = vnew_lim;
    lim.vold = vold;
    lim.vcrit = 0.0;
    lim.vto = vto;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_LIMITER;
    ev.limiter = &lim;
    pub_diag(&ev);
}

static void
on_gmin(void *ctx, double val, int converged_ok, int iters)
{
    Ngspice__GminStep g = NGSPICE__GMIN_STEP__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    g.value = val;
    g.converged = converged_ok != 0;
    g.iterations = iters;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_GMIN;
    ev.gmin = &g;
    pub_diag(&ev);
}

static void
on_src_step(void *ctx, double factor, int converged_ok, int iters)
{
    Ngspice__SourceStep s = NGSPICE__SOURCE_STEP__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    s.factor = factor;
    s.converged = converged_ok != 0;
    s.iterations = iters;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_SRC_STEP;
    ev.src_step = &s;
    pub_diag(&ev);
}

static Ngspice__DeviceLoadValuesEntry *
mk_val(const char *k, double v)
{
    Ngspice__DeviceLoadValuesEntry *e = malloc(sizeof *e);

    if (!e)
        return NULL;
    ngspice__device_load_values_entry__init(e);
    e->key = strdup(k);
    e->value = v;
    return e;
}

static void
on_device_dio(void *ctx, const char *inst, double vd, double id, double gd, double ieq)
{
    Ngspice__DeviceLoad dev = NGSPICE__DEVICE_LOAD__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;
    Ngspice__DeviceLoadValuesEntry *ve[4];
    size_t i;

    (void) ctx;
    dev.type = (char *) "DIO";
    dev.instance = strdup(inst && inst[0] ? inst : "");
    if (!dev.instance) {
        return;
    }
    ve[0] = mk_val("vd", vd);
    ve[1] = mk_val("id", id);
    ve[2] = mk_val("gd", gd);
    ve[3] = mk_val("ieq", ieq);
    for (i = 0; i < 4; i++) {
        if (!ve[i]) {
            size_t j;

            for (j = 0; j < i; j++) {
                free(ve[j]->key);
                free(ve[j]);
            }
            free(dev.instance);
            return;
        }
    }
    dev.n_values = 4;
    dev.values = ve;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_DEVICE;
    ev.device = &dev;
    pub_diag(&ev);
    for (i = 0; i < 4; i++) {
        free(ve[i]->key);
        free(ve[i]);
    }
    free(dev.instance);
}

static void
on_matrix(void *ctx, int size, double min_piv, double max_piv, double ratio)
{
    Ngspice__MatrixCondition m = NGSPICE__MATRIX_CONDITION__INIT;
    Ngspice__DiagEvent ev = NGSPICE__DIAG_EVENT__INIT;

    (void) ctx;
    m.size = size;
    m.min_pivot = min_piv;
    m.max_pivot = max_piv;
    m.condition_ratio = ratio;
    ev.request_id = (char *) (server_diag_request_id ? server_diag_request_id : "");
    ev.event_case = NGSPICE__DIAG_EVENT__EVENT_MATRIX;
    ev.matrix = &m;
    pub_diag(&ev);
}

static const NgspiceDiagSink server_sink = {
    .ctx = NULL,
    .on_nr_iter = on_nr_iter,
    .on_limiter_pnj = on_limiter_pnj,
    .on_limiter_fet = on_limiter_fet,
    .on_gmin = on_gmin,
    .on_src_step = on_src_step,
    .on_device_dio = on_device_dio,
    .on_matrix = on_matrix,
};

static void
log_reset(void)
{
    loglen = 0;
    logbuf[0] = '\0';
}

static bool
log_has_ci(const char *needle)
{
    return strcasestr(logbuf, needle) != NULL;
}

static int
netlist_to_lines(const char *netlist, char ***out_lines)
{
    size_t cap = 32, n = 0, i;
    char **lines = calloc(cap, sizeof(char *));
    const char *p = netlist;
    char *cur = NULL;
    size_t cur_len = 0;

    if (!lines)
        return -1;

    while (*p) {
        const char *e = strchr(p, '\n');
        size_t linelen = e ? (size_t) (e - p) : strlen(p);
        char *piece = malloc(linelen + 1);

        if (!piece) {
            for (i = 0; i < n; i++)
                free(lines[i]);
            free(lines);
            free(cur);
            return -1;
        }
        memcpy(piece, p, linelen);
        piece[linelen] = '\0';
        while (linelen > 0 && (piece[linelen - 1] == '\r' || piece[linelen - 1] == ' '))
            piece[--linelen] = '\0';

        if (linelen > 0 && piece[0] == '+') {
            size_t addl = linelen > 1 ? linelen - 1 : 0;
            char *nc = realloc(cur, cur_len + addl + 1);

            if (!nc) {
                free(piece);
                goto fail;
            }
            cur = nc;
            if (addl)
                memcpy(cur + cur_len, piece + 1, addl);
            cur_len += addl;
            cur[cur_len] = '\0';
            free(piece);
        } else {
            if (cur && cur_len > 0) {
                if (n + 1 >= cap) {
                    char **nl = realloc(lines, (cap *= 2) * sizeof(char *));

                    if (!nl) {
                        free(piece);
                        goto fail;
                    }
                    lines = nl;
                }
                lines[n++] = cur;
                cur = NULL;
                cur_len = 0;
            }
            cur = piece;
            cur_len = strlen(cur);
        }
        p = e ? e + 1 : p + linelen;
    }
    if (cur && cur_len > 0) {
        if (n + 1 >= cap) {
            char **nl = realloc(lines, (cap + 2) * sizeof(char *));

            if (!nl)
                goto fail;
            lines = nl;
        }
        lines[n++] = cur;
        cur = NULL;
    } else {
        free(cur);
    }
    if (n + 1 >= cap) {
        char **nl = realloc(lines, (n + 2) * sizeof(char *));

        if (!nl)
            goto fail;
        lines = nl;
    }
    lines[n] = NULL;
    *out_lines = lines;
    return (int) n;

fail:
    for (i = 0; i < n; i++)
        free(lines[i]);
    free(lines);
    free(cur);
    return -1;
}

static void
free_lines(char **lines)
{
    char **p;

    if (!lines)
        return;
    for (p = lines; *p; p++)
        free(*p);
    free(lines);
}

/*
 * ngspice `create_circbyline` feeds the first line as the SPICE *title* card.
 * If the user starts with `V1 ...` or `.param`, that line is not parsed as a
 * device. Prepend a synthetic title when the first line is clearly not a title.
 */
static bool
spice_line_needs_prepended_title(const char *line)
{
    const char *s = line;
    char c0;
    char c1;

    if (!line)
        return false;
    while (*s == ' ' || *s == '\t' || *s == '\r')
        s++;
    if (*s == '\0' || *s == '*' || *s == '+')
        return false;
    if (*s == '.')
        return true;
    c0 = (char) toupper((unsigned char) *s);
    c1 = s[1];
    if (c0 == 'X' && isalnum((unsigned char) c1))
        return true;
    if (isalpha((unsigned char) c0) && isdigit((unsigned char) c1)) {
        switch (c0) {
        case 'R':
        case 'C':
        case 'L':
        case 'V':
        case 'I':
        case 'G':
        case 'E':
        case 'F':
        case 'H':
        case 'D':
        case 'Q':
        case 'J':
        case 'M':
        case 'X':
        case 'K':
        case 'B':
        case 'O':
            return true;
        default:
            return false;
        }
    }
    return false;
}

static int
prepend_spice_title_line(char ***plines)
{
    char **lines = *plines;
    char **nl;
    int n;
    int i;

    if (!lines || !lines[0] || !spice_line_needs_prepended_title(lines[0]))
        return 0;
    for (n = 0; lines[n]; n++)
        ;
    nl = malloc((size_t) (n + 2) * sizeof *nl);
    if (!nl)
        return -1;
    nl[0] = strdup("ngspice-server deck");
    if (!nl[0]) {
        free(nl);
        return -1;
    }
    for (i = 0; i <= n; i++)
        nl[i + 1] = lines[i];
    free(lines);
    *plines = nl;
    return 0;
}

static void
tolower_copy(char *dst, const char *src, size_t max)
{
    size_t i;

    for (i = 0; i + 1 < max && src[i]; i++)
        dst[i] = (char) tolower((unsigned char) src[i]);
    dst[i] = '\0';
}

static bool
has_node_voltage(const Ngspice__SimResult *res, const char *k)
{
    size_t i;

    for (i = 0; i < res->n_node_voltages; i++) {
        if (res->node_voltages[i]->key && !strcasecmp(res->node_voltages[i]->key, k))
            return true;
    }
    return false;
}

static bool
has_branch_current(const Ngspice__SimResult *res, const char *k)
{
    size_t i;

    for (i = 0; i < res->n_branch_currents; i++) {
        if (res->branch_currents[i]->key && !strcasecmp(res->branch_currents[i]->key, k))
            return true;
    }
    return false;
}

static void
add_node_voltage(Ngspice__SimResult *res, const char *k, double v)
{
    Ngspice__SimResult__NodeVoltagesEntry *e = malloc(sizeof *e);

    if (!e)
        return;
    ngspice__sim_result__node_voltages_entry__init(e);
    e->key = strdup(k);
    e->value = v;
    res->node_voltages =
        realloc(res->node_voltages, (res->n_node_voltages + 1) * sizeof *res->node_voltages);
    if (!res->node_voltages) {
        free(e->key);
        free(e);
        return;
    }
    res->node_voltages[res->n_node_voltages++] = e;
}

static void
add_branch_current(Ngspice__SimResult *res, const char *k, double v)
{
    Ngspice__SimResult__BranchCurrentsEntry *e = malloc(sizeof *e);

    if (!e)
        return;
    ngspice__sim_result__branch_currents_entry__init(e);
    e->key = strdup(k);
    e->value = v;
    res->branch_currents =
        realloc(res->branch_currents, (res->n_branch_currents + 1) * sizeof *res->branch_currents);
    if (!res->branch_currents) {
        free(e->key);
        free(e);
        return;
    }
    res->branch_currents[res->n_branch_currents++] = e;
}

static void
add_warning(Ngspice__SimResult *res, const char *w)
{
    char *c = strdup(w);

    if (!c)
        return;
    res->warnings = realloc(res->warnings, (res->n_warnings + 1) * sizeof *res->warnings);
    if (!res->warnings) {
        free(c);
        return;
    }
    res->warnings[res->n_warnings++] = c;
}

static bool
is_plain_node_name(const char *s)
{
    if (!s || !isalpha((unsigned char) s[0]))
        return false;
    for (; *s; s++) {
        if (!isalnum((unsigned char) *s) && *s != '_')
            return false;
    }
    return true;
}

static void
parse_print_assignments(Ngspice__SimResult *res, const char *from)
{
    const char *p = from;
    char keybuf[256];

    while (p && *p) {
        char lhs[96];
        double val;
        char *t;
        char *e;
        int nch = 0;

        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
            p++;
        if (!*p)
            break;
        if (sscanf(p, "%95[^=] = %lf%n", lhs, &val, &nch) < 2) {
            const char *nl = strchr(p, '\n');

            if (!nl)
                break;
            p = nl + 1;
            continue;
        }
        p += nch;
        t = lhs;
        while (*t == ' ' || *t == '\t')
            t++;
        e = t + strlen(t);
        while (e > t && (e[-1] == ' ' || e[-1] == '\t'))
            *--e = '\0';
        if ((t[0] == 'v' || t[0] == 'V') && t[1] == '(') {
            const char *q = strchr(t + 2, ')');

            if (q) {
                size_t n = (size_t) (q - (t + 2));

                if (n < sizeof(keybuf)) {
                    memcpy(keybuf, t + 2, n);
                    keybuf[n] = '\0';
                    tolower_copy(keybuf, keybuf, sizeof(keybuf));
                    add_node_voltage(res, keybuf, val);
                }
            }
        } else if ((t[0] == 'i' || t[0] == 'I') && t[1] == '(') {
            const char *q = strchr(t + 2, ')');

            if (q) {
                size_t n = (size_t) (q - (t + 2));

                if (n < sizeof(keybuf)) {
                    memcpy(keybuf, t + 2, n);
                    keybuf[n] = '\0';
                    tolower_copy(keybuf, keybuf, sizeof(keybuf));
                    if (!has_branch_current(res, keybuf))
                        add_branch_current(res, keybuf, val);
                }
            }
        } else {
            const char *dot = strchr(t, '.');

            if (dot && (size_t) (dot - t) < sizeof(lhs) &&
                strncasecmp(t, "op", 2) == 0) {
                const char *rhs = dot + 1;

                if (is_plain_node_name(rhs)) {
                    tolower_copy(keybuf, rhs, sizeof(keybuf));
                    if (!has_node_voltage(res, keybuf))
                        add_node_voltage(res, keybuf, val);
                }
            } else if (is_plain_node_name(t)) {
                tolower_copy(keybuf, t, sizeof(keybuf));
                if (!has_node_voltage(res, keybuf))
                    add_node_voltage(res, keybuf, val);
            }
        }
    }
}

/*
 * ngGet_Vec_Info uses a single static vector_info buffer; reading many
 * vectors in one pass is unreliable. ngspice shared `print` output is
 * authoritative for .op and is captured via SendChar into logbuf.
 */
static int
append_fmt(char *buf, size_t cap, const char *fmt, ...)
{
    size_t L = strlen(buf);
    va_list ap;
    int n;

    if (L >= cap - 1)
        return -1;
    va_start(ap, fmt);
    n = vsnprintf(buf + L, cap - L, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t) n >= cap - L)
        return -1;
    return 0;
}

static void
fill_voltages_currents(Ngspice__SimResult *res, int converged_ok)
{
    char *cur;
    char **vecs;
    int vi;
    char pcmd[8192];
    size_t mark = loglen;

    if (!converged_ok)
        return;
    /*
     * `print all` prints the *vector named "all"*, not every node.
     * Build `print op1.n1 op1.n2 ...` from the current op* plot.
     */
    cur = ngSpice_CurPlot();
    if (!cur || strncasecmp(cur, "op", 2) != 0)
        return;
    vecs = ngSpice_AllVecs(cur);
    if (!vecs)
        return;
    pcmd[0] = '\0';
    if (append_fmt(pcmd, sizeof pcmd, "print") != 0)
        return;
    for (vi = 0; vecs[vi]; vi++) {
        const char *vn = vecs[vi];

        if (is_plain_node_name(vn)) {
            if (append_fmt(pcmd, sizeof pcmd, " %s", vn) != 0)
                return;
        } else {
            if (append_fmt(pcmd, sizeof pcmd, " %s.%s", cur, vn) != 0)
                return;
        }
    }
    if (strlen(pcmd) <= strlen("print"))
        return;
    ngSpice_Command(pcmd);
    parse_print_assignments(res, logbuf + mark);
}

static void
fill_vectors(Ngspice__SimResult *res)
{
    int j;
    size_t nbytes;
    size_t out;

    if (!res || vec_count <= 0 || vec_npts <= 0)
        return;
    nbytes = (size_t) vec_npts * sizeof(double);
    res->vectors = calloc((size_t) vec_count, sizeof *res->vectors);
    if (!res->vectors) {
        add_warning(res, "out of memory allocating vectors");
        return;
    }
    res->num_points = vec_npts;
    out = 0;
    for (j = 0; j < vec_count; j++) {
        Ngspice__VectorData *vd;

        if (!vec_names[j] || !vec_real[j])
            continue;
        vd = calloc(1, sizeof *vd);
        if (!vd) {
            add_warning(res, "out of memory allocating VectorData");
            return;
        }
        ngspice__vector_data__init(vd);
        vd->name = strdup(vec_names[j]);
        if (!vd->name) {
            free(vd);
            add_warning(res, "out of memory copying vector name");
            return;
        }
        vd->real_values = malloc(nbytes);
        if (!vd->real_values) {
            free(vd->name);
            free(vd);
            add_warning(res, "out of memory copying real_values");
            return;
        }
        memcpy(vd->real_values, vec_real[j], nbytes);
        vd->n_real_values = (size_t) vec_npts;
        if (vec_is_complex[j] && vec_imag[j]) {
            vd->imag_values = malloc(nbytes);
            if (!vd->imag_values) {
                free(vd->real_values);
                free(vd->name);
                free(vd);
                add_warning(res, "out of memory copying imag_values");
                return;
            }
            memcpy(vd->imag_values, vec_imag[j], nbytes);
            vd->n_imag_values = (size_t) vec_npts;
        }
        res->vectors[out++] = vd;
    }
    res->n_vectors = out;
    if (out == 0) {
        free(res->vectors);
        res->vectors = NULL;
    }
}

static Ngspice__SimResult *
run_one_request(const Ngspice__SimRequest *req, bool stream_diag)
{
    Ngspice__SimResult *res;
    char **lines = NULL;
    int circ_rc;
    int cmd_rc;
    struct timespec t0, t1;
    static char req_id_store[512];
    const char *req_id =
        (req->request_id && req->request_id[0]) ? req->request_id : "default";

    res = calloc(1, sizeof *res);
    if (!res)
        return NULL;
    ngspice__sim_result__init(res);
    res->request_id = strdup(req_id);
    res->converged = 0;
    res->iterations = 0;
    res->wall_time_ms = 0;
    res->error = NGSPICE__SIM_RESULT__ERROR_CODE__OK;

    strncpy(req_id_store, req_id, sizeof(req_id_store) - 1);
    req_id_store[sizeof(req_id_store) - 1] = '\0';
    ngspice_diag_request_id = req_id_store;
    server_diag_request_id = req_id_store;

    /* Workers use PUSH to master (sock_worker_diag_push); master would use PUB.
     * pub_diag() picks the right socket; do not require sock_pub here or workers
     * never attach the sink and no DiagEvents reach the bridge SUB. */
    if (stream_diag && (sock_pub || sock_worker_diag_push))
        ngspice_diag_sink = &server_sink;
    else
        ngspice_diag_sink = NULL;

    log_reset();
    nr_emit_count = 0;
    sim_t0_us = now_us();

    if (!req->netlist || !req->netlist[0]) {
        add_warning(res, "empty netlist");
        res->error = NGSPICE__SIM_RESULT__ERROR_CODE__PARSE_ERROR;
        goto done;
    }

    if (netlist_to_lines(req->netlist, &lines) < 0 || !lines) {
        add_warning(res, "out of memory parsing netlist");
        res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
        goto done;
    }

    if (prepend_spice_title_line(&lines) < 0) {
        add_warning(res, "out of memory inserting spice title line");
        res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
        goto done;
    }

    clock_gettime(CLOCK_MONOTONIC, &t0);
    circ_rc = ngSpice_Circ(lines);
    free_lines(lines);
    lines = NULL;

    if (circ_rc != 0) {
        add_warning(res, "ngSpice_Circ failed (parse error)");
        res->error = NGSPICE__SIM_RESULT__ERROR_CODE__PARSE_ERROR;
        clock_gettime(CLOCK_MONOTONIC, &t1);
        res->wall_time_ms =
            (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;
        goto done;
    }

    vec_accum_reset();

    if (!req->analysis || !req->analysis[0] || strcasecmp(req->analysis, "op") == 0) {
        cmd_rc = ngSpice_Command((char *) "op");
        clock_gettime(CLOCK_MONOTONIC, &t1);
        res->wall_time_ms =
            (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;

        if (cmd_rc != 0) {
            add_warning(res, "ngSpice_Command(op) failed");
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
            goto done;
        }

        if (log_has_ci("singular")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__SINGULAR_MATRIX;
            add_warning(res, "singular matrix reported");
        } else if (log_has_ci("too many iterations") ||
                   (log_has_ci("iteration") && log_has_ci("convergence"))) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__CONVERGENCE_FAILURE;
            res->converged = 0;
        } else if (log_has_ci("error:") || log_has_ci("parse error")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__PARSE_ERROR;
        } else {
            res->converged = 1;
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__OK;
        }

        fill_voltages_currents(res, res->converged);
        res->analysis_type = strdup("op");
        if (!res->analysis_type)
            add_warning(res, "out of memory for analysis_type");
        res->num_points = res->converged ? 1 : 0;
    } else if (strcasecmp(req->analysis, "tran") == 0 ||
               strcasecmp(req->analysis, "ac") == 0 ||
               strcasecmp(req->analysis, "dc") == 0) {
        vec_accum_reset();
        vec_capture_enabled = 1;
        cmd_rc = ngSpice_Command((char *) "run");
        vec_capture_enabled = 0;
        clock_gettime(CLOCK_MONOTONIC, &t1);
        res->wall_time_ms =
            (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;

        if (cmd_rc != 0) {
            add_warning(res, "ngSpice_Command(run) failed");
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
            goto done;
        }

        if (log_has_ci("singular")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__SINGULAR_MATRIX;
            add_warning(res, "singular matrix reported");
        } else if (log_has_ci("too many iterations") ||
                   (log_has_ci("iteration") && log_has_ci("convergence"))) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__CONVERGENCE_FAILURE;
            res->converged = 0;
        } else if (log_has_ci("error:") || log_has_ci("parse error")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__PARSE_ERROR;
        } else {
            res->converged = 1;
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__OK;
        }

        if (res->converged && vec_npts > 0)
            fill_vectors(res);
        else if (res->converged && vec_npts == 0)
            add_warning(res, "run finished with no vector data points");

        res->analysis_type = strdup(req->analysis);
        if (!res->analysis_type)
            add_warning(res, "out of memory for analysis_type");
    } else {
        char w[256];

        snprintf(w, sizeof w, "unknown analysis '%s'; running op", req->analysis);
        add_warning(res, w);
        cmd_rc = ngSpice_Command((char *) "op");
        clock_gettime(CLOCK_MONOTONIC, &t1);
        res->wall_time_ms =
            (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;

        if (cmd_rc != 0) {
            add_warning(res, "ngSpice_Command(op) failed");
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
            goto done;
        }

        if (log_has_ci("singular")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__SINGULAR_MATRIX;
            add_warning(res, "singular matrix reported");
        } else if (log_has_ci("too many iterations") ||
                   (log_has_ci("iteration") && log_has_ci("convergence"))) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__CONVERGENCE_FAILURE;
            res->converged = 0;
        } else if (log_has_ci("error:") || log_has_ci("parse error")) {
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__PARSE_ERROR;
        } else {
            res->converged = 1;
            res->error = NGSPICE__SIM_RESULT__ERROR_CODE__OK;
        }

        fill_voltages_currents(res, res->converged);
        res->analysis_type = strdup("op");
        if (!res->analysis_type)
            add_warning(res, "out of memory for analysis_type");
        res->num_points = res->converged ? 1 : 0;
    }

    res->iterations = nr_emit_count;
    if (res->iterations == 0 && res->converged)
        res->iterations = 1;

done:
    vec_capture_enabled = 0;
    vec_accum_reset();
    ngspice_diag_sink = NULL;
    ngspice_diag_request_id = NULL;
    server_diag_request_id = "";
    ngSpice_Command((char *) "reset");
    return res;
}

static void
handle_sig(int sig)
{
    int i;

    (void) sig;
    stop_server = 1;
    if (!worker_pids)
        return;
    for (i = 0; i < pool_size; i++) {
        if (worker_pids[i] != 0)
            kill(worker_pids[i], SIGTERM);
    }
}

static void
usage(const char *argv0)
{
    fprintf(stderr,
            "Usage: %s [--rep-port N] [--pub-port N] [--bind-addr HOST]\n"
            "       [--workers N] [--admit-cap N] [--request-timeout SEC]\n"
            "       %s --version\n"
            "  Default: tcp://127.0.0.1:5555 (ROUTER, REQ clients OK), tcp://127.0.0.1:5556 (PUB)\n"
            "  Workers: default min(%d, nproc), max %d (override with NGSPICE_WORKERS).\n"
            "  Admission queue: default %zu (NGSPICE_ADMIT_CAP).\n"
            "  Per-job worker deadline: NGSPICE_REQUEST_TIMEOUT_SEC or --request-timeout (default 300s).\n"
            "  Run with SPICE_LIB_DIR pointing at ngspice install share/ngspice.\n",
            argv0, argv0, DEFAULT_WORKER_CAP, DEFAULT_WORKER_CAP, (size_t) DEFAULT_ADMIT_CAP);
}

static void
batch_add(Ngspice__BatchSimResult *b, Ngspice__SimResult *r)
{
    b->results = realloc(b->results, (b->n_results + 1) * sizeof *b->results);
    if (!b->results)
        return;
    b->results[b->n_results++] = r;
}

static void
unlink_zmq_ipc(const char *ipc_url)
{
    const char *path;

    if (!ipc_url || strncmp(ipc_url, "ipc://", 6) != 0)
        return;
    path = ipc_url + 6;
    if (path[0] == '/')
        (void) unlink(path);
}

static void
drain_diag_forward(void)
{
    if (!sock_diag_pull || !sock_pub)
        return;
    for (;;) {
        zmq_msg_t m0, m1;
        int rc;
        int more;

        zmq_msg_init(&m0);
        rc = zmq_msg_recv(&m0, sock_diag_pull, ZMQ_DONTWAIT);
        if (rc < 0) {
            zmq_msg_close(&m0);
            return;
        }
        more = zmq_msg_more(&m0);
        if (more) {
            zmq_msg_init(&m1);
            if (zmq_msg_recv(&m1, sock_diag_pull, 0) < 0) {
                zmq_msg_close(&m1);
                zmq_msg_close(&m0);
                return;
            }
            (void) zmq_send(sock_pub, zmq_msg_data(&m0), zmq_msg_size(&m0), ZMQ_SNDMORE | ZMQ_DONTWAIT);
            (void) zmq_send(sock_pub, zmq_msg_data(&m1), zmq_msg_size(&m1), ZMQ_DONTWAIT);
            zmq_msg_close(&m1);
        } else {
            /* Legacy single-frame DiagEvent (no topic): default subscription */
            (void) zmq_send(sock_pub, "default", (size_t) 7, ZMQ_SNDMORE | ZMQ_DONTWAIT);
            (void) zmq_send(sock_pub, zmq_msg_data(&m0), zmq_msg_size(&m0), ZMQ_DONTWAIT);
        }
        zmq_msg_close(&m0);
    }
}

static Ngspice__SimResult *
ipc_fail_result(const char *req_id, const char *msg)
{
    Ngspice__SimResult *res = calloc(1, sizeof *res);

    if (!res)
        return NULL;
    ngspice__sim_result__init(res);
    res->request_id = strdup(req_id && req_id[0] ? req_id : "default");
    if (!res->request_id)
        res->request_id = (char *) protobuf_c_empty_string;
    res->converged = 0;
    res->error = NGSPICE__SIM_RESULT__ERROR_CODE__INTERNAL_ERROR;
    if (msg)
        add_warning(res, msg);
    return res;
}

static Ngspice__SimResult *
ipc_busy_result(const char *req_id)
{
    Ngspice__SimResult *res = calloc(1, sizeof *res);

    if (!res)
        return NULL;
    ngspice__sim_result__init(res);
    res->request_id = strdup(req_id && req_id[0] ? req_id : "default");
    if (!res->request_id)
        res->request_id = (char *) protobuf_c_empty_string;
    res->converged = 0;
    res->error = NGSPICE__SIM_RESULT__ERROR_CODE__SERVER_BUSY;
    add_warning(res, "server busy (workers and wait queue full); retry");
    stat_server_busy_replies++;
    return res;
}

static Ngspice__SimResult *
ipc_timeout_result(const char *req_id)
{
    Ngspice__SimResult *res = calloc(1, sizeof *res);

    if (!res)
        return NULL;
    ngspice__sim_result__init(res);
    res->request_id = strdup(req_id && req_id[0] ? req_id : "default");
    if (!res->request_id)
        res->request_id = (char *) protobuf_c_empty_string;
    res->converged = 0;
    res->error = NGSPICE__SIM_RESULT__ERROR_CODE__TIMEOUT;
    add_warning(res, "exceeded server per-request deadline");
    return res;
}

static int64_t
mono_ns_now(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return 0;
    return (int64_t) ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static int
router_send_reply(const uint8_t *rid, size_t rid_len, const void *body, size_t body_len)
{
    if (!sock_router || !rid || !body)
        return -1;
    if (zmq_send(sock_router, rid, rid_len, ZMQ_SNDMORE) < 0)
        return -1;
    if (zmq_send(sock_router, "", 0, ZMQ_SNDMORE) < 0)
        return -1;
    if (zmq_send(sock_router, body, body_len, 0) < 0)
        return -1;
    return 0;
}

static int
first_idle_worker(void)
{
    int w;

    for (w = 0; w < pool_size; w++) {
        if (!worker_states[w].active)
            return w;
    }
    return -1;
}

static int
admit_enqueue_copy(const uint8_t *rid, size_t rid_len, const uint8_t *pay, size_t paylen)
{
    admit_entry_t *e;

    if (admit_count >= admit_cap || !admit_q)
        return -1;
    e = &admit_q[admit_tail];
    e->rid = malloc(rid_len);
    e->payload = malloc(paylen);
    if (!e->rid || !e->payload) {
        free(e->rid);
        free(e->payload);
        e->rid = NULL;
        e->payload = NULL;
        return -1;
    }
    memcpy(e->rid, rid, rid_len);
    e->rid_len = rid_len;
    memcpy(e->payload, pay, paylen);
    e->paylen = paylen;
    admit_tail = (admit_tail + 1) % admit_cap;
    admit_count++;
    return 0;
}

static void
admit_clear_all(void)
{
    size_t i;

    if (!admit_q)
        return;
    for (i = 0; i < admit_cap; i++) {
        free(admit_q[i].rid);
        free(admit_q[i].payload);
        admit_q[i].rid = NULL;
        admit_q[i].payload = NULL;
    }
    admit_head = admit_tail = admit_count = 0;
}

static int
send_worker_job(int widx, uint32_t seq, int stream_diag, const Ngspice__SimRequest *req)
{
    size_t psz, tot;
    uint8_t *buf;
    uint32_t seq_net = htonl(seq);

    if (widx < 0 || widx >= pool_size || !worker_push_socks || !worker_push_socks[widx] || !req)
        return -1;
    psz = ngspice__sim_request__get_packed_size(req);
    tot = 5 + psz;
    buf = malloc(tot);
    if (!buf)
        return -1;
    memcpy(buf, &seq_net, 4);
    buf[4] = stream_diag ? (uint8_t) 1 : (uint8_t) 0;
    ngspice__sim_request__pack(req, buf + 5);
    if (zmq_send(worker_push_socks[widx], buf, tot, 0) < 0) {
        free(buf);
        return -1;
    }
    free(buf);
    return 0;
}

/* 1 = got result, 0 = EAGAIN, -1 = error */
static int
recv_worker_result_now(Ngspice__SimResult **res_out, uint32_t *seq_out)
{
    zmq_msg_t m;
    size_t sz;
    uint8_t *d;
    uint32_t seq_net;
    uint32_t seq_host;
    Ngspice__SimResult *res;

    zmq_msg_init(&m);
    if (zmq_msg_recv(&m, sock_res_pull, ZMQ_DONTWAIT) < 0) {
        zmq_msg_close(&m);
        if (errno == EAGAIN)
            return 0;
        return -1;
    }
    sz = zmq_msg_size(&m);
    d = (uint8_t *) zmq_msg_data(&m);
    if (sz < 4) {
        zmq_msg_close(&m);
        return -1;
    }
    memcpy(&seq_net, d, 4);
    seq_host = ntohl(seq_net);
    if (seq_out)
        *seq_out = seq_host;
    res = ngspice__sim_result__unpack(NULL, sz - 4, d + 4);
    zmq_msg_close(&m);
    if (!res)
        return -1;
    *res_out = res;
    return 1;
}

static void
admit_pop_free_head(void)
{
    admit_entry_t *e;

    if (admit_count == 0 || !admit_q)
        return;
    e = &admit_q[admit_head];
    free(e->rid);
    free(e->payload);
    e->rid = NULL;
    e->payload = NULL;
    admit_head = (admit_head + 1) % admit_cap;
    admit_count--;
}

static void
batch_try_pipeline(BatchPending *bp);

static int fork_one_worker(int wid, int is_respawn);
static void kill_respawn_worker(int w);

static void
batch_finalize_and_reply(BatchPending *bp)
{
    Ngspice__BatchSimResult *bres;
    struct timespec bt1;
    size_t olen;
    uint8_t *out;
    size_t i;

    if (!bp)
        return;
    clock_gettime(CLOCK_MONOTONIC, &bt1);
    bres = calloc(1, sizeof *bres);
    if (!bres) {
        ngspice__batch_sim_request__free_unpacked(bp->batch, NULL);
        free(bp->slots);
        free(bp->rid);
        free(bp);
        return;
    }
    ngspice__batch_sim_result__init(bres);
    bres->total_wall_time_ms =
        (bt1.tv_sec - bp->t0.tv_sec) * 1000.0 + (bt1.tv_nsec - bp->t0.tv_nsec) / 1e6;
    for (i = 0; i < bp->n; i++) {
        if (bp->slots[i])
            batch_add(bres, bp->slots[i]);
    }
    free(bp->slots);
    ngspice__batch_sim_request__free_unpacked(bp->batch, NULL);
    olen = ngspice__batch_sim_result__get_packed_size(bres);
    out = malloc(olen + 1);
    if (out && bp->rid) {
        out[0] = WIRE_BATCH;
        ngspice__batch_sim_result__pack(bres, out + 1);
        (void) router_send_reply(bp->rid, bp->rid_len, out, olen + 1);
        free(out);
    } else
        free(out);
    ngspice__batch_sim_result__free_unpacked(bres, NULL);
    free(bp->rid);
    free(bp);
}

static void
batch_try_pipeline(BatchPending *bp)
{
    if (!bp || !bp->batch)
        return;
    while (bp->next_send < bp->n) {
        int w = first_idle_worker();
        uint32_t seq;
        Ngspice__SimRequest *sub;

        if (w < 0)
            return;
        sub = bp->batch->requests[bp->next_send];
        if (!sub)
            return;
        seq = ++seq_gen;
        if (send_worker_job(w, seq, sub->stream_diagnostics, sub) != 0)
            return;
        worker_states[w].active = 2;
        worker_states[w].seq = seq;
        worker_states[w].rid = NULL;
        worker_states[w].rid_len = 0;
        worker_states[w].bp = bp;
        worker_states[w].batch_idx = bp->next_send;
        worker_states[w].req_label = NULL;
        worker_states[w].deadline_mono_ns =
            mono_ns_now() + (int64_t) (request_timeout_sec * 1e9);
        bp->next_send++;
    }
}

static void
dispatch_sim_on_worker(int w, Ngspice__SimRequest *req, const uint8_t *rid, size_t rid_len)
{
    uint32_t seq;
    uint8_t *rid_copy;
    const char *ql;

    if (w < 0 || !req || !rid)
        return;
    seq = ++seq_gen;
    if (send_worker_job(w, seq, req->stream_diagnostics, req) != 0) {
        ngspice__sim_request__free_unpacked(req, NULL);
        return;
    }
    rid_copy = malloc(rid_len);
    if (!rid_copy) {
        ngspice__sim_request__free_unpacked(req, NULL);
        kill_respawn_worker(w);
        return;
    }
    memcpy(rid_copy, rid, rid_len);
    ql = (req->request_id && req->request_id[0]) ? req->request_id : "default";
    worker_states[w].req_label = strdup(ql);
    if (!worker_states[w].req_label) {
        free(rid_copy);
        ngspice__sim_request__free_unpacked(req, NULL);
        kill_respawn_worker(w);
        return;
    }
    worker_states[w].active = 1;
    worker_states[w].seq = seq;
    worker_states[w].rid = rid_copy;
    worker_states[w].rid_len = rid_len;
    worker_states[w].bp = NULL;
    worker_states[w].batch_idx = 0;
    worker_states[w].deadline_mono_ns =
        mono_ns_now() + (int64_t) (request_timeout_sec * 1e9);
    ngspice__sim_request__free_unpacked(req, NULL);
}

static void
try_dispatch_admit(void)
{
    while (admit_count > 0 && first_idle_worker() >= 0) {
        admit_entry_t *e = &admit_q[admit_head];
        uint8_t wire = e->payload[0];

        if (wire == WIRE_SIM) {
            Ngspice__SimRequest *req =
                ngspice__sim_request__unpack(NULL, e->paylen - 1, e->payload + 1);
            int w = first_idle_worker();

            if (!req || w < 0)
                break;
            dispatch_sim_on_worker(w, req, e->rid, e->rid_len);
            admit_pop_free_head();
        } else if (wire == WIRE_BATCH) {
            Ngspice__BatchSimRequest *batch =
                ngspice__batch_sim_request__unpack(NULL, e->paylen - 1, e->payload + 1);
            BatchPending *bp;
            uint8_t *rid_copy;

            if (!batch || batch->n_requests == 0) {
                if (batch)
                    ngspice__batch_sim_request__free_unpacked(batch, NULL);
                admit_pop_free_head();
                continue;
            }
            rid_copy = malloc(e->rid_len);
            if (!rid_copy) {
                ngspice__batch_sim_request__free_unpacked(batch, NULL);
                break;
            }
            memcpy(rid_copy, e->rid, e->rid_len);
            {
                size_t saved_rlen = e->rid_len;

                admit_pop_free_head();
                bp = calloc(1, sizeof *bp);
                if (!bp) {
                    free(rid_copy);
                    ngspice__batch_sim_request__free_unpacked(batch, NULL);
                    break;
                }
                bp->rid = rid_copy;
                bp->rid_len = saved_rlen;
            }
            bp->batch = batch;
            bp->n = batch->n_requests;
            bp->next_send = 0;
            bp->remaining = (int) bp->n;
            bp->slots = calloc(bp->n, sizeof *bp->slots);
            if (!bp->slots) {
                free(rid_copy);
                ngspice__batch_sim_request__free_unpacked(batch, NULL);
                free(bp);
                break;
            }
            clock_gettime(CLOCK_MONOTONIC, &bp->t0);
            batch_try_pipeline(bp);
        } else {
            admit_pop_free_head();
        }
    }
}

static void
complete_worker_result(uint32_t seq_got, Ngspice__SimResult *res)
{
    int w;

    for (w = 0; w < pool_size; w++) {
        if (worker_states[w].active && worker_states[w].seq == seq_got)
            break;
    }
    if (w >= pool_size) {
        ngspice__sim_result__free_unpacked(res, NULL);
        return;
    }
    if (worker_states[w].active == 1) {
        size_t olen;
        uint8_t *out;
        uint8_t *rid = worker_states[w].rid;
        size_t rid_len = worker_states[w].rid_len;

        olen = ngspice__sim_result__get_packed_size(res);
        out = malloc(olen + 1);
        if (!out || !rid) {
            free(out);
            free(rid);
            free(worker_states[w].req_label);
            worker_states[w].req_label = NULL;
            worker_states[w].rid = NULL;
            worker_states[w].deadline_mono_ns = 0;
            worker_states[w].active = 0;
            ngspice__sim_result__free_unpacked(res, NULL);
            try_dispatch_admit();
            return;
        }
        out[0] = WIRE_SIM;
        ngspice__sim_result__pack(res, out + 1);
        (void) router_send_reply(rid, rid_len, out, olen + 1);
        free(out);
        free(rid);
        free(worker_states[w].req_label);
        worker_states[w].req_label = NULL;
        worker_states[w].rid = NULL;
        worker_states[w].deadline_mono_ns = 0;
        worker_states[w].active = 0;
        ngspice__sim_result__free_unpacked(res, NULL);
        stat_requests_completed++;
        try_dispatch_admit();
        return;
    }
    if (worker_states[w].active == 2) {
        BatchPending *bp = worker_states[w].bp;
        size_t idx = worker_states[w].batch_idx;

        worker_states[w].active = 0;
        worker_states[w].bp = NULL;
        worker_states[w].deadline_mono_ns = 0;
        if (!bp) {
            ngspice__sim_result__free_unpacked(res, NULL);
            try_dispatch_admit();
            return;
        }
        if (idx < bp->n && bp->slots[idx])
            ngspice__sim_result__free_unpacked(bp->slots[idx], NULL);
        if (idx < bp->n)
            bp->slots[idx] = res;
        bp->remaining--;
        stat_requests_completed++;
        batch_try_pipeline(bp);
        if (bp->remaining <= 0)
            batch_finalize_and_reply(bp);
        try_dispatch_admit();
    }
}

static void
drain_worker_results(void)
{
    for (;;) {
        Ngspice__SimResult *res = NULL;
        uint32_t seq = 0;
        int rc = recv_worker_result_now(&res, &seq);

        if (rc == 0)
            break;
        if (rc < 0)
            break;
        complete_worker_result(seq, res);
    }
}

static void __attribute__((noreturn)) worker_loop(int wid);

static void
handle_sigchld(int sig)
{
    (void) sig;
    sigchld_pending = 1;
}

static void
emit_sim_reply_clear_slot(int w, Ngspice__SimResult *res)
{
    uint8_t *rid;
    size_t rid_len;
    size_t olen;
    uint8_t *out;

    if (w < 0 || w >= pool_size || !res)
        return;

    rid = worker_states[w].rid;
    rid_len = worker_states[w].rid_len;
    free(worker_states[w].req_label);
    worker_states[w].req_label = NULL;
    worker_states[w].deadline_mono_ns = 0;
    worker_states[w].active = 0;
    worker_states[w].bp = NULL;
    worker_states[w].seq = 0;
    worker_states[w].rid = NULL;
    worker_states[w].rid_len = 0;

    olen = ngspice__sim_result__get_packed_size(res);
    out = malloc(olen + 1);
    if (!out) {
        fprintf(stderr, "emit_sim_reply_clear_slot: OOM packing reply (worker %d)\n", w);
        free(rid);
        ngspice__sim_result__free_unpacked(res, NULL);
        return;
    }
    if (!rid) {
        fprintf(stderr, "emit_sim_reply_clear_slot: missing ROUTER identity (worker %d)\n", w);
        free(out);
        ngspice__sim_result__free_unpacked(res, NULL);
        return;
    }
    out[0] = WIRE_SIM;
    ngspice__sim_result__pack(res, out + 1);
    if (router_send_reply(rid, rid_len, out, olen + 1) == 0)
        stat_requests_completed++;
    else
        fprintf(stderr, "emit_sim_reply_clear_slot: router_send_reply failed (worker %d)\n", w);
    free(out);
    free(rid);
    ngspice__sim_result__free_unpacked(res, NULL);
}

static void
fail_batch_slot_with_result(int w, Ngspice__SimResult *res)
{
    BatchPending *bp;
    size_t idx;

    if (w < 0 || w >= pool_size || !res || worker_states[w].active != 2)
        return;
    bp = worker_states[w].bp;
    idx = worker_states[w].batch_idx;
    worker_states[w].active = 0;
    worker_states[w].bp = NULL;
    worker_states[w].deadline_mono_ns = 0;
    worker_states[w].seq = 0;
    if (!bp || idx >= bp->n) {
        ngspice__sim_result__free_unpacked(res, NULL);
        return;
    }
    if (bp->slots[idx])
        ngspice__sim_result__free_unpacked(bp->slots[idx], NULL);
    bp->slots[idx] = res;
    bp->remaining--;
    stat_requests_completed++;
    batch_try_pipeline(bp);
    if (bp->remaining <= 0)
        batch_finalize_and_reply(bp);
    try_dispatch_admit();
}

static int
reconnect_worker_push(int wid)
{
    char wu[200];
    int r;

    if (wid < 0 || wid >= pool_size || !worker_push_socks || !worker_push_socks[wid])
        return -1;
    snprintf(wu, sizeof wu, "ipc:///tmp/ngspice-srv-%d-w%d.ipc", (int) server_master_pid, wid);
    (void) zmq_disconnect(worker_push_socks[wid], wu);
    usleep(20000);
    for (r = 0; r < 200; r++) {
        if (zmq_connect(worker_push_socks[wid], wu) == 0)
            return 0;
        usleep(10000);
    }
    return -1;
}

static int
fork_one_worker(int wid, int is_respawn)
{
    pid_t p = fork();

    if (p < 0) {
        fprintf(stderr, "fork worker %d: %s\n", wid, strerror(errno));
        return -1;
    }
    if (p == 0)
        worker_loop(wid);
    worker_pids[wid] = p;
    if (is_respawn)
        stat_worker_restarts++;
    return 0;
}

static void
kill_respawn_worker(int w)
{
    if (w < 0 || w >= pool_size)
        return;
    if (worker_pids[w] > 0) {
        kill(worker_pids[w], SIGKILL);
        (void) waitpid(worker_pids[w], NULL, 0);
    }
    worker_pids[w] = 0;
    if (fork_one_worker(w, 1) != 0)
        fprintf(stderr, "failed to respawn worker %d after kill\n", w);
    if (reconnect_worker_push(w) != 0)
        fprintf(stderr, "reconnect worker push %d failed\n", w);
}

static void
fail_inflight_worker_crash(int w, const char *msg)
{
    Ngspice__SimResult *res;
    const char *qid = "default";

    if (w < 0 || w >= pool_size || !worker_states[w].active)
        return;
    if (worker_states[w].active == 1) {
        qid = worker_states[w].req_label && worker_states[w].req_label[0]
                  ? worker_states[w].req_label
                  : "default";
        res = ipc_fail_result(qid, msg);
        if (!res) {
            fprintf(stderr, "fail_inflight_worker_crash: OOM sim result (worker %d)\n", w);
            free(worker_states[w].rid);
            worker_states[w].rid = NULL;
            free(worker_states[w].req_label);
            worker_states[w].req_label = NULL;
            worker_states[w].deadline_mono_ns = 0;
            worker_states[w].active = 0;
        } else
            emit_sim_reply_clear_slot(w, res);
    } else if (worker_states[w].active == 2) {
        BatchPending *bp = worker_states[w].bp;
        size_t idx = worker_states[w].batch_idx;
        Ngspice__SimRequest *sub = NULL;

        if (bp && idx < bp->n)
            sub = bp->batch->requests[idx];
        if (sub && sub->request_id && sub->request_id[0])
            qid = sub->request_id;
        res = ipc_fail_result(qid, msg);
        if (!res)
            res = ipc_fail_result("default", msg);
        if (!res) {
            fprintf(stderr, "fail_inflight_worker_crash: total OOM batch fail (worker %d)\n", w);
            worker_states[w].active = 0;
            worker_states[w].bp = NULL;
            worker_states[w].deadline_mono_ns = 0;
            worker_states[w].seq = 0;
        } else
            fail_batch_slot_with_result(w, res);
    }
    try_dispatch_admit();
}

static void
check_request_deadlines(void)
{
    int64_t now = mono_ns_now();
    int w;

    for (w = 0; w < pool_size; w++) {
        Ngspice__SimResult *tres;
        const char *qid;

        if (!worker_states[w].active || worker_states[w].deadline_mono_ns == 0)
            continue;
        if (now <= worker_states[w].deadline_mono_ns)
            continue;
        stat_request_timeouts++;
        if (worker_states[w].active == 1) {
            qid = worker_states[w].req_label && worker_states[w].req_label[0]
                      ? worker_states[w].req_label
                      : "default";
            tres = ipc_timeout_result(qid);
            if (!tres)
                tres = ipc_timeout_result("default");
            if (!tres) {
                fprintf(stderr, "check_request_deadlines: total OOM timeout sim (worker %d)\n", w);
                free(worker_states[w].rid);
                worker_states[w].rid = NULL;
                free(worker_states[w].req_label);
                worker_states[w].req_label = NULL;
                worker_states[w].deadline_mono_ns = 0;
                worker_states[w].active = 0;
                kill_respawn_worker(w);
                try_dispatch_admit();
                continue;
            }
            emit_sim_reply_clear_slot(w, tres);
            kill_respawn_worker(w);
            try_dispatch_admit();
        } else if (worker_states[w].active == 2) {
            BatchPending *bp = worker_states[w].bp;
            size_t idx = worker_states[w].batch_idx;

            qid = "default";
            if (bp && idx < bp->n && bp->batch->requests[idx]
                && bp->batch->requests[idx]->request_id
                && bp->batch->requests[idx]->request_id[0])
                qid = bp->batch->requests[idx]->request_id;
            tres = ipc_timeout_result(qid);
            if (!tres)
                tres = ipc_timeout_result("default");
            if (!tres) {
                fprintf(stderr, "check_request_deadlines: total OOM timeout batch (worker %d)\n", w);
                worker_states[w].active = 0;
                worker_states[w].bp = NULL;
                worker_states[w].deadline_mono_ns = 0;
                worker_states[w].seq = 0;
                kill_respawn_worker(w);
                try_dispatch_admit();
                continue;
            }
            fail_batch_slot_with_result(w, tres);
            kill_respawn_worker(w);
            try_dispatch_admit();
        }
    }
}

static void
reap_exited_workers(void)
{
    int status;
    pid_t p;
    int w;

    while ((p = waitpid(-1, &status, WNOHANG)) > 0) {
        for (w = 0; w < pool_size; w++) {
            if (worker_pids[w] == p)
                break;
        }
        if (w >= pool_size)
            continue;
        worker_pids[w] = 0;
        if (worker_states[w].active)
            fail_inflight_worker_crash(w, "worker process exited unexpectedly");
        if (fork_one_worker(w, 1) != 0)
            fprintf(stderr, "failed to respawn worker %d after exit\n", w);
        if (reconnect_worker_push(w) != 0)
            fprintf(stderr, "reconnect worker push %d failed (after exit)\n", w);
        try_dispatch_admit();
    }
}

static void
handle_router_wire_stats(const uint8_t *rid, size_t rid_len)
{
    Ngspice__ServerStats st;
    size_t olen;
    uint8_t *out;
    uint8_t stackbuf[192];
    int wb = 0;
    int w;

    for (w = 0; w < pool_size; w++) {
        if (worker_states[w].active)
            wb++;
    }
    ngspice__server_stats__init(&st);
    st.pool_size = pool_size;
    st.admit_queued = (uint32_t) admit_count;
    st.admit_cap = (uint32_t) admit_cap;
    st.workers_busy = wb;
    st.requests_completed = stat_requests_completed;
    st.server_busy_replies = stat_server_busy_replies;
    st.worker_restarts = stat_worker_restarts;
    st.request_timeouts = stat_request_timeouts;
    olen = ngspice__server_stats__get_packed_size(&st);
    if (olen + 1 > sizeof stackbuf)
        out = malloc(olen + 1);
    else
        out = stackbuf;
    if (!out)
        return;
    out[0] = WIRE_STATS;
    ngspice__server_stats__pack(&st, out + 1);
    (void) router_send_reply(rid, rid_len, out, olen + 1);
    if (out != stackbuf)
        free(out);
}

static void __attribute__((noreturn))
worker_loop(int wid)
{
    char worker_url[200];
    const char *res_e = getenv("NGSPICE_SRV_RES");
    const char *diag_e = getenv("NGSPICE_SRV_DIAG");
    void *wctx;
    void *pull;
    void *pres;
    void *pdiag;
    int a;

    (void) wid;
    if (!res_e || !diag_e) {
        fprintf(stderr, "worker: missing NGSPICE_SRV_RES / NGSPICE_SRV_DIAG\n");
        _exit(2);
    }
    snprintf(worker_url, sizeof worker_url, "ipc:///tmp/ngspice-srv-%d-w%d.ipc",
             (int) getppid(), wid);
    wctx = zmq_ctx_new();
    pull = zmq_socket(wctx, ZMQ_PULL);
    pres = zmq_socket(wctx, ZMQ_PUSH);
    pdiag = zmq_socket(wctx, ZMQ_PUSH);
    if (!wctx || !pull || !pres || !pdiag) {
        fprintf(stderr, "worker: zmq alloc failed\n");
        _exit(3);
    }
    if (zmq_bind(pull, worker_url) != 0) {
        fprintf(stderr, "worker bind %s: %s\n", worker_url, zmq_strerror(errno));
        _exit(4);
    }
    for (a = 0; a < 400; a++) {
        if (zmq_connect(pres, res_e) == 0 && zmq_connect(pdiag, diag_e) == 0)
            break;
        usleep(10000);
    }
    if (a >= 400) {
        fprintf(stderr, "worker: connect to master IPC failed\n");
        _exit(5);
    }
    sock_worker_diag_push = pdiag;
    sock_pub = NULL;
    if (ngSpice_Init(send_char, send_stat, ngexit, send_data, send_initdata, bg_thread,
                     NULL) != 0) {
        fprintf(stderr, "worker ngSpice_Init failed\n");
        _exit(6);
    }
    for (;;) {
        zmq_msg_t m;
        size_t sz;
        uint8_t *data;
        uint32_t seq_net, seq_host;
        uint8_t stream;
        Ngspice__SimRequest *req;
        Ngspice__SimResult *res;
        size_t rsz, outsz;
        uint8_t *outb;

        zmq_msg_init(&m);
        if (zmq_msg_recv(&m, pull, 0) < 0) {
            zmq_msg_close(&m);
            continue;
        }
        sz = zmq_msg_size(&m);
        data = (uint8_t *) zmq_msg_data(&m);
        if (sz < 5) {
            zmq_msg_close(&m);
            continue;
        }
        memcpy(&seq_net, data, 4);
        seq_host = ntohl(seq_net);
        stream = data[4];
        req = ngspice__sim_request__unpack(NULL, sz - 5, data + 5);
        zmq_msg_close(&m);
        if (!req)
            continue;
        res = run_one_request(req, stream != 0);
        ngspice__sim_request__free_unpacked(req, NULL);
        if (!res)
            continue;
        rsz = ngspice__sim_result__get_packed_size(res);
        outsz = 4 + rsz;
        outb = malloc(outsz);
        if (!outb) {
            ngspice__sim_result__free_unpacked(res, NULL);
            continue;
        }
        seq_net = htonl(seq_host);
        memcpy(outb, &seq_net, 4);
        ngspice__sim_result__pack(res, outb + 4);
        ngspice__sim_result__free_unpacked(res, NULL);
        (void) zmq_send(pres, outb, outsz, 0);
        free(outb);
    }
}

static int
start_worker_children(pid_t master_pid)
{
    char res_u[200], diag_u[200], wk_u[200];
    int wid;

    snprintf(res_u, sizeof res_u, "ipc:///tmp/ngspice-srv-%d-res.ipc", (int) master_pid);
    snprintf(diag_u, sizeof diag_u, "ipc:///tmp/ngspice-srv-%d-diag.ipc", (int) master_pid);
    unlink_zmq_ipc(res_u);
    unlink_zmq_ipc(diag_u);
    for (wid = 0; wid < pool_size; wid++) {
        snprintf(wk_u, sizeof wk_u, "ipc:///tmp/ngspice-srv-%d-w%d.ipc", (int) master_pid, wid);
        unlink_zmq_ipc(wk_u);
    }
    if (setenv("NGSPICE_SRV_RES", res_u, 1) != 0 || setenv("NGSPICE_SRV_DIAG", diag_u, 1) != 0)
        return -1;
    for (wid = 0; wid < pool_size; wid++) {
        if (fork_one_worker(wid, 0) != 0)
            return -1;
    }
    return 0;
}

static void
handle_router_wire_sim(const uint8_t *rid, size_t rid_len, const uint8_t *payload, size_t psz)
{
    Ngspice__SimRequest *req;
    const char *req_id;
    int w;

    if (psz < 2)
        return;
    req = ngspice__sim_request__unpack(NULL, psz - 1, payload + 1);
    if (!req) {
        Ngspice__SimResult *sres = ipc_fail_result("default", "invalid SimRequest protobuf");
        size_t olen;
        uint8_t *out;

        if (!sres)
            return;
        olen = ngspice__sim_result__get_packed_size(sres);
        out = malloc(olen + 1);
        if (out) {
            out[0] = WIRE_SIM;
            ngspice__sim_result__pack(sres, out + 1);
            (void) router_send_reply(rid, rid_len, out, olen + 1);
            free(out);
        }
        ngspice__sim_result__free_unpacked(sres, NULL);
        return;
    }
    req_id = (req->request_id && req->request_id[0]) ? req->request_id : "default";
    w = first_idle_worker();
    if (w >= 0) {
        dispatch_sim_on_worker(w, req, rid, rid_len);
        return;
    }
    if (admit_enqueue_copy(rid, rid_len, payload, psz) == 0) {
        ngspice__sim_request__free_unpacked(req, NULL);
        return;
    }
    {
        Ngspice__SimResult *busy = ipc_busy_result(req_id);
        size_t olen;
        uint8_t *out;

        ngspice__sim_request__free_unpacked(req, NULL);
        if (!busy)
            return;
        olen = ngspice__sim_result__get_packed_size(busy);
        out = malloc(olen + 1);
        if (out) {
            out[0] = WIRE_SIM;
            ngspice__sim_result__pack(busy, out + 1);
            (void) router_send_reply(rid, rid_len, out, olen + 1);
            free(out);
        }
        ngspice__sim_result__free_unpacked(busy, NULL);
    }
}

static void
reply_batch_busy(const uint8_t *rid, size_t rid_len)
{
    Ngspice__BatchSimResult *bres;
    Ngspice__SimResult *busy;
    size_t olen;
    uint8_t *out;

    busy = ipc_busy_result("default");
    if (!busy)
        return;
    bres = calloc(1, sizeof *bres);
    if (!bres) {
        ngspice__sim_result__free_unpacked(busy, NULL);
        return;
    }
    ngspice__batch_sim_result__init(bres);
    batch_add(bres, busy);
    olen = ngspice__batch_sim_result__get_packed_size(bres);
    out = malloc(olen + 1);
    if (out) {
        out[0] = WIRE_BATCH;
        ngspice__batch_sim_result__pack(bres, out + 1);
        (void) router_send_reply(rid, rid_len, out, olen + 1);
        free(out);
    }
    ngspice__batch_sim_result__free_unpacked(bres, NULL);
}

static void
handle_router_wire_batch(const uint8_t *rid, size_t rid_len, const uint8_t *payload, size_t psz)
{
    Ngspice__BatchSimRequest *batch;
    BatchPending *bp;
    uint8_t *rid_copy;

    if (psz < 2)
        return;
    if (first_idle_worker() < 0) {
        if (admit_enqueue_copy(rid, rid_len, payload, psz) == 0)
            return;
        reply_batch_busy(rid, rid_len);
        return;
    }
    batch = ngspice__batch_sim_request__unpack(NULL, psz - 1, payload + 1);
    if (!batch || batch->n_requests == 0) {
        Ngspice__BatchSimResult *bres;
        Ngspice__SimResult *sres;
        size_t olen;
        uint8_t *out;

        if (batch)
            ngspice__batch_sim_request__free_unpacked(batch, NULL);
        sres = ipc_fail_result("default", "invalid or empty BatchSimRequest");
        if (!sres)
            return;
        bres = calloc(1, sizeof *bres);
        if (!bres) {
            ngspice__sim_result__free_unpacked(sres, NULL);
            return;
        }
        ngspice__batch_sim_result__init(bres);
        batch_add(bres, sres);
        olen = ngspice__batch_sim_result__get_packed_size(bres);
        out = malloc(olen + 1);
        if (out) {
            out[0] = WIRE_BATCH;
            ngspice__batch_sim_result__pack(bres, out + 1);
            (void) router_send_reply(rid, rid_len, out, olen + 1);
            free(out);
        }
        ngspice__batch_sim_result__free_unpacked(bres, NULL);
        return;
    }
    rid_copy = malloc(rid_len);
    if (!rid_copy) {
        ngspice__batch_sim_request__free_unpacked(batch, NULL);
        return;
    }
    memcpy(rid_copy, rid, rid_len);
    bp = calloc(1, sizeof *bp);
    if (!bp) {
        free(rid_copy);
        ngspice__batch_sim_request__free_unpacked(batch, NULL);
        return;
    }
    bp->rid = rid_copy;
    bp->rid_len = rid_len;
    bp->batch = batch;
    bp->n = batch->n_requests;
    bp->next_send = 0;
    bp->remaining = (int) bp->n;
    bp->slots = calloc(bp->n, sizeof *bp->slots);
    if (!bp->slots) {
        free(rid_copy);
        ngspice__batch_sim_request__free_unpacked(batch, NULL);
        free(bp);
        return;
    }
    clock_gettime(CLOCK_MONOTONIC, &bp->t0);
    batch_try_pipeline(bp);
}

static void
handle_router_message(const uint8_t *rid, size_t rid_len, const uint8_t *body, size_t body_len)
{
    uint8_t wire;

    if (!body || body_len < 1)
        return;
    wire = body[0];
    if (wire == WIRE_SIM)
        handle_router_wire_sim(rid, rid_len, body, body_len);
    else if (wire == WIRE_BATCH)
        handle_router_wire_batch(rid, rid_len, body, body_len);
    else if (wire == WIRE_STATS)
        handle_router_wire_stats(rid, rid_len);
    else {
        Ngspice__SimResult *sres = ipc_fail_result("default", "invalid or unsupported request");
        size_t olen;
        uint8_t *out;

        if (!sres)
            return;
        olen = ngspice__sim_result__get_packed_size(sres);
        out = malloc(olen + 1);
        if (out) {
            out[0] = WIRE_SIM;
            ngspice__sim_result__pack(sres, out + 1);
            (void) router_send_reply(rid, rid_len, out, olen + 1);
            free(out);
        }
        ngspice__sim_result__free_unpacked(sres, NULL);
    }
}

int
main(int argc, char **argv)
{
    int rep_port = 5555;
    int pub_port = 5556;
    const char *bind_host = "127.0.0.1";
    char rep_url[160], pub_url[160];
    char res_url[200], diag_url[200], wu[200];
    pid_t master_pid = getpid();
    int wid;
    int i;
    long nproc;
    int hwm = 1024;
    int diag_rcv_ms = 250;

    nproc = sysconf(_SC_NPROCESSORS_ONLN);
    if (nproc < 1)
        nproc = 1;
    pool_size = (int) (nproc < DEFAULT_WORKER_CAP ? nproc : DEFAULT_WORKER_CAP);

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--rep-port") && i + 1 < argc)
            rep_port = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--pub-port") && i + 1 < argc)
            pub_port = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--bind-addr") && i + 1 < argc)
            bind_host = argv[++i];
        else if (!strcmp(argv[i], "--workers") && i + 1 < argc)
            pool_size = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--admit-cap") && i + 1 < argc)
            admit_cap = (size_t) atoi(argv[++i]);
        else if (!strcmp(argv[i], "--request-timeout") && i + 1 < argc)
            request_timeout_sec = strtod(argv[++i], NULL);
        else if (!strcmp(argv[i], "--version")) {
            printf("ngspice-server " NG_SERVER_VERSION "\n");
            return 0;
        } else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        }
    }
    {
        const char *ew = getenv("NGSPICE_WORKERS");
        const char *ea = getenv("NGSPICE_ADMIT_CAP");
        const char *er = getenv("NGSPICE_REQUEST_TIMEOUT_SEC");

        if (ew && ew[0])
            pool_size = atoi(ew);
        if (ea && ea[0])
            admit_cap = (size_t) atoi(ea);
        if (er && er[0])
            request_timeout_sec = strtod(er, NULL);
    }
    if (request_timeout_sec <= 0.0 || request_timeout_sec > 86400.0)
        request_timeout_sec = 300.0;
    if (pool_size < 1)
        pool_size = 1;
    if (pool_size > DEFAULT_WORKER_CAP)
        pool_size = DEFAULT_WORKER_CAP;
    if (pool_size > POOL_MAX)
        pool_size = POOL_MAX;
    if (admit_cap < 8)
        admit_cap = 8;
    if (admit_cap > 65536)
        admit_cap = 65536;

    worker_push_socks = calloc((size_t) pool_size, sizeof *worker_push_socks);
    worker_pids = calloc((size_t) pool_size, sizeof *worker_pids);
    worker_states = calloc((size_t) pool_size, sizeof *worker_states);
    admit_q = calloc(admit_cap, sizeof *admit_q);
    if (!worker_push_socks || !worker_pids || !worker_states || !admit_q) {
        fprintf(stderr, "out of memory allocating worker/admit tables\n");
        return 1;
    }
    memset(worker_states, 0, (size_t) pool_size * sizeof *worker_states);
    seq_gen = 1;
    server_master_pid = master_pid;

    snprintf(rep_url, sizeof rep_url, "tcp://%s:%d", bind_host, rep_port);
    snprintf(pub_url, sizeof pub_url, "tcp://%s:%d", bind_host, pub_port);
    snprintf(res_url, sizeof res_url, "ipc:///tmp/ngspice-srv-%d-res.ipc", (int) master_pid);
    snprintf(diag_url, sizeof diag_url, "ipc:///tmp/ngspice-srv-%d-diag.ipc", (int) master_pid);

    if (start_worker_children(master_pid) != 0) {
        fprintf(stderr, "start_worker_children failed\n");
        free(worker_push_socks);
        free(worker_pids);
        free(worker_states);
        admit_clear_all();
        free(admit_q);
        return 1;
    }

    zmq_ctx = zmq_ctx_new();
    if (!zmq_ctx) {
        fprintf(stderr, "zmq_ctx_new failed\n");
        return 1;
    }
    sock_res_pull = zmq_socket(zmq_ctx, ZMQ_PULL);
    sock_diag_pull = zmq_socket(zmq_ctx, ZMQ_PULL);
    if (!sock_res_pull || !sock_diag_pull) {
        fprintf(stderr, "zmq_socket PULL failed\n");
        return 1;
    }
    (void) zmq_setsockopt(sock_res_pull, ZMQ_RCVHWM, &hwm, sizeof hwm);
    (void) zmq_setsockopt(sock_diag_pull, ZMQ_RCVHWM, &hwm, sizeof hwm);
    (void) zmq_setsockopt(sock_diag_pull, ZMQ_RCVTIMEO, &diag_rcv_ms, sizeof diag_rcv_ms);
    if (zmq_bind(sock_res_pull, res_url) != 0 || zmq_bind(sock_diag_pull, diag_url) != 0) {
        fprintf(stderr, "zmq_bind IPC failed: %s\n", zmq_strerror(errno));
        return 1;
    }
    usleep(80000);
    for (wid = 0; wid < pool_size; wid++) {
        int r;

        worker_push_socks[wid] = zmq_socket(zmq_ctx, ZMQ_PUSH);
        if (!worker_push_socks[wid]) {
            fprintf(stderr, "zmq_socket PUSH worker %d failed\n", wid);
            return 1;
        }
        (void) zmq_setsockopt(worker_push_socks[wid], ZMQ_SNDHWM, &hwm, sizeof hwm);
        snprintf(wu, sizeof wu, "ipc:///tmp/ngspice-srv-%d-w%d.ipc", (int) master_pid, wid);
        for (r = 0; r < 200; r++) {
            if (zmq_connect(worker_push_socks[wid], wu) == 0)
                break;
            usleep(10000);
        }
        if (r >= 200) {
            fprintf(stderr, "zmq_connect worker %d failed\n", wid);
            return 1;
        }
    }

    sock_router = zmq_socket(zmq_ctx, ZMQ_ROUTER);
    sock_pub = zmq_socket(zmq_ctx, ZMQ_PUB);
    if (!sock_router || !sock_pub) {
        fprintf(stderr, "zmq_socket failed\n");
        return 1;
    }
    (void) zmq_setsockopt(sock_router, ZMQ_RCVHWM, &hwm, sizeof hwm);
    (void) zmq_setsockopt(sock_router, ZMQ_SNDHWM, &hwm, sizeof hwm);
    (void) zmq_setsockopt(sock_pub, ZMQ_SNDHWM, &hwm, sizeof hwm);
    if (zmq_bind(sock_router, rep_url) != 0 || zmq_bind(sock_pub, pub_url) != 0) {
        fprintf(stderr, "zmq_bind failed: %s\n", zmq_strerror(errno));
        return 1;
    }

    signal(SIGINT, handle_sig);
    signal(SIGTERM, handle_sig);
    {
        struct sigaction sa;

        memset(&sa, 0, sizeof sa);
        sa.sa_handler = handle_sigchld;
        sigemptyset(&sa.sa_mask);
        sa.sa_flags = SA_RESTART | SA_NOCLDSTOP;
        (void) sigaction(SIGCHLD, &sa, NULL);
    }

    fprintf(stderr, "ngspice-server " NG_SERVER_VERSION " ready ROUTER=%s PUB=%s (pool=%d admit=%zu)\n",
            rep_url, pub_url, pool_size, admit_cap);

    while (!stop_server) {
        zmq_pollitem_t items[3];
        int pr;

        items[0].socket = sock_router;
        items[0].fd = -1;
        items[0].events = ZMQ_POLLIN;
        items[0].revents = 0;
        items[1].socket = sock_diag_pull;
        items[1].fd = -1;
        items[1].events = ZMQ_POLLIN;
        items[1].revents = 0;
        items[2].socket = sock_res_pull;
        items[2].fd = -1;
        items[2].events = ZMQ_POLLIN;
        items[2].revents = 0;
        pr = zmq_poll(items, 3, 250);
        if (pr < 0) {
            if (errno == EINTR)
                continue;
            break;
        }
        if (items[1].revents & ZMQ_POLLIN)
            drain_diag_forward();
        if (items[2].revents & ZMQ_POLLIN)
            drain_worker_results();
        if (items[0].revents & ZMQ_POLLIN) {
            zmq_msg_t idm, sep, body;
            uint8_t *rid;
            size_t rid_len;
            uint8_t *bod;
            size_t bod_len;

            zmq_msg_init(&idm);
            if (zmq_msg_recv(&idm, sock_router, 0) < 0) {
                zmq_msg_close(&idm);
                break;
            }
            rid = (uint8_t *) zmq_msg_data(&idm);
            rid_len = zmq_msg_size(&idm);
            if (!zmq_msg_more(&idm)) {
                zmq_msg_close(&idm);
                continue;
            }
            zmq_msg_init(&sep);
            if (zmq_msg_recv(&sep, sock_router, 0) < 0) {
                zmq_msg_close(&sep);
                zmq_msg_close(&idm);
                continue;
            }
            zmq_msg_close(&sep);
            zmq_msg_init(&body);
            bod = NULL;
            bod_len = 0;
            if (zmq_msg_recv(&body, sock_router, 0) < 0) {
                zmq_msg_close(&body);
                zmq_msg_close(&idm);
                continue;
            }
            bod = (uint8_t *) zmq_msg_data(&body);
            bod_len = zmq_msg_size(&body);
            while (zmq_msg_more(&body)) {
                zmq_msg_close(&body);
                zmq_msg_init(&body);
                if (zmq_msg_recv(&body, sock_router, 0) < 0) {
                    zmq_msg_close(&body);
                    zmq_msg_close(&idm);
                    bod = NULL;
                    bod_len = 0;
                    break;
                }
                bod = (uint8_t *) zmq_msg_data(&body);
                bod_len = zmq_msg_size(&body);
            }
            if (bod)
                handle_router_message(rid, rid_len, bod, bod_len);
            zmq_msg_close(&body);
            zmq_msg_close(&idm);
        }
        if (sigchld_pending) {
            sigchld_pending = 0;
            reap_exited_workers();
        }
        check_request_deadlines();
        drain_diag_forward();
        drain_worker_results();
    }

    for (i = 0; i < pool_size; i++) {
        if (worker_pids[i] != 0) {
            kill(worker_pids[i], SIGTERM);
            (void) waitpid(worker_pids[i], NULL, 0);
            worker_pids[i] = 0;
        }
    }
    unlink_zmq_ipc(res_url);
    unlink_zmq_ipc(diag_url);
    for (wid = 0; wid < pool_size; wid++) {
        snprintf(wu, sizeof wu, "ipc:///tmp/ngspice-srv-%d-w%d.ipc", (int) master_pid, wid);
        unlink_zmq_ipc(wu);
    }
    zmq_close(sock_router);
    sock_router = NULL;
    zmq_close(sock_pub);
    for (wid = 0; wid < pool_size; wid++) {
        if (worker_push_socks[wid]) {
            zmq_close(worker_push_socks[wid]);
            worker_push_socks[wid] = NULL;
        }
    }
    zmq_close(sock_res_pull);
    zmq_close(sock_diag_pull);
    sock_res_pull = NULL;
    sock_diag_pull = NULL;
    admit_clear_all();
    free(admit_q);
    admit_q = NULL;
    free(worker_push_socks);
    worker_push_socks = NULL;
    free(worker_pids);
    worker_pids = NULL;
    free(worker_states);
    worker_states = NULL;
    zmq_ctx_term(zmq_ctx);
    return 0;
}
