/**********
 * Optional JSON-Lines diagnostics (Story I) + optional host callbacks (Story J).
 * Zero cost when NGSPICE_DIAG_FILE unset and ngspice_diag_sink is NULL.
 **********/

#include "ngspice/diaghooks.h"

#include <stdlib.h>
#include <string.h>

#if defined(__GNUC__) && __GNUC__ >= 4
#define DIAG_EXPORT __attribute__((visibility("default")))
#else
#define DIAG_EXPORT
#endif

DIAG_EXPORT FILE *ngspice_diag_fp = NULL;
DIAG_EXPORT const NgspiceDiagSink *ngspice_diag_sink = NULL;
DIAG_EXPORT const char *ngspice_diag_request_id = NULL;

static int diag_atexit_registered;

int
ngspice_diag_wants_nr(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_nr_iter);
}

int
ngspice_diag_wants_matrix(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_matrix);
}

int
ngspice_diag_wants_gmin(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_gmin);
}

int
ngspice_diag_wants_src(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_src_step);
}

int
ngspice_diag_wants_device(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_device_dio);
}

int
ngspice_diag_wants_pnjlim(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_limiter_pnj);
}

int
ngspice_diag_wants_fetlim(void)
{
    return ngspice_diag_fp != NULL
        || (ngspice_diag_sink && ngspice_diag_sink->on_limiter_fet);
}

void
ngspice_diag_emit_nr_iter(int iter, double max_rhs, double max_dx, double damp,
                          int noncon, int converged)
{
    int conv = converged ? 1 : 0;

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"nr_iter\",\"iter\":%d,\"max_rhs\":%.6e,\"max_dx\":%.6e,\"damp\":%.6e,\"conv\":%d}\n",
                iter, max_rhs, max_dx, damp, conv);
    if (ngspice_diag_sink && ngspice_diag_sink->on_nr_iter)
        ngspice_diag_sink->on_nr_iter(ngspice_diag_sink->ctx, iter, max_rhs, max_dx,
                                        damp, noncon, converged);
}

void
ngspice_diag_emit_limiter_pnj(const char *instance, double vnew_raw, double vnew_lim,
                              double vold, double vcrit)
{
    const char *inst = instance ? instance : "";

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"limiter\",\"fn\":\"DEVpnjlim\",\"inst\":\"%s\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vcrit\":%.6e}\n",
                inst, vnew_raw, vnew_lim, vold, vcrit);
    if (ngspice_diag_sink && ngspice_diag_sink->on_limiter_pnj)
        ngspice_diag_sink->on_limiter_pnj(ngspice_diag_sink->ctx, inst,
                                           vnew_raw, vnew_lim, vold, vcrit);
}

void
ngspice_diag_emit_limiter_fet(const char *instance, double vnew_raw, double vnew_lim,
                              double vold, double vto)
{
    const char *inst = instance ? instance : "";

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"limiter\",\"fn\":\"DEVfetlim\",\"inst\":\"%s\",\"vnew_raw\":%.6e,\"vnew_lim\":%.6e,\"vold\":%.6e,\"vto\":%.6e}\n",
                inst, vnew_raw, vnew_lim, vold, vto);
    if (ngspice_diag_sink && ngspice_diag_sink->on_limiter_fet)
        ngspice_diag_sink->on_limiter_fet(ngspice_diag_sink->ctx, inst,
                                           vnew_raw, vnew_lim, vold, vto);
}

void
ngspice_diag_emit_gmin(double val, int converged_ok, int iters)
{
    int conv = converged_ok ? 1 : 0;

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"gmin\",\"val\":%.6e,\"conv\":%d,\"iters\":%d}\n",
                val, conv, iters);
    if (ngspice_diag_sink && ngspice_diag_sink->on_gmin)
        ngspice_diag_sink->on_gmin(ngspice_diag_sink->ctx, val, converged_ok, iters);
}

void
ngspice_diag_emit_src_step(double factor, int converged_ok, int iters)
{
    int conv = converged_ok ? 1 : 0;

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"src_step\",\"factor\":%.6e,\"conv\":%d,\"iters\":%d}\n",
                factor, conv, iters);
    if (ngspice_diag_sink && ngspice_diag_sink->on_src_step)
        ngspice_diag_sink->on_src_step(ngspice_diag_sink->ctx, factor, converged_ok, iters);
}

void
ngspice_diag_emit_device_dio(const char *inst, double vd, double id, double gd,
                              double ieq)
{
    const char *nm = inst ? inst : "";

    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"device\",\"type\":\"DIO\",\"inst\":\"%s\",\"vd\":%.6e,\"id\":%.6e,\"gd\":%.6e,\"ieq\":%.6e}\n",
                nm, vd, id, gd, ieq);
    if (ngspice_diag_sink && ngspice_diag_sink->on_device_dio)
        ngspice_diag_sink->on_device_dio(ngspice_diag_sink->ctx, nm, vd, id, gd, ieq);
}

void
ngspice_diag_emit_matrix(int size, double min_piv, double max_piv, double ratio)
{
    if (ngspice_diag_fp)
        fprintf(ngspice_diag_fp,
                "{\"hook\":\"matrix\",\"size\":%d,\"min_piv\":%.6e,\"max_piv\":%.6e,\"ratio\":%.6e}\n",
                size, min_piv, max_piv, ratio);
    if (ngspice_diag_sink && ngspice_diag_sink->on_matrix)
        ngspice_diag_sink->on_matrix(ngspice_diag_sink->ctx, size, min_piv, max_piv, ratio);
}

void
ngspice_diag_init(void)
{
    const char *path;

    if (ngspice_diag_fp)
        return;

    path = getenv("NGSPICE_DIAG_FILE");
    if (path == NULL || path[0] == '\0')
        return;

    ngspice_diag_fp = fopen(path, "w");
    if (!ngspice_diag_fp) {
        fprintf(stderr, "WARNING: cannot open diag file %s\n", path);
        return;
    }

    if (!diag_atexit_registered) {
        atexit(ngspice_diag_close);
        diag_atexit_registered = 1;
    }
}

void
ngspice_diag_close(void)
{
    if (ngspice_diag_fp) {
        fflush(ngspice_diag_fp);
        fclose(ngspice_diag_fp);
        ngspice_diag_fp = NULL;
    }
}
