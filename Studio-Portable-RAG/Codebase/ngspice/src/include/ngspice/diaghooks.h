#ifndef NGSPICE_DIAGHOOKS_H
#define NGSPICE_DIAGHOOKS_H

#include <stdio.h>

extern FILE *ngspice_diag_fp;

/*
 * Optional host callbacks (Story J): set from ngspice-server before simulation.
 * All function pointers may be NULL. When NULL and ngspice_diag_fp is NULL,
 * emit paths are no-ops (zero overhead after the cheap pointer checks).
 */
typedef struct NgspiceDiagSink {
    void *ctx;
    void (*on_nr_iter)(void *ctx, int iter, double max_rhs, double max_dx,
                       double damp, int noncon, int converged);
    void (*on_limiter_pnj)(void *ctx, const char *instance,
                           double vnew_raw, double vnew_lim, double vold, double vcrit);
    void (*on_limiter_fet)(void *ctx, const char *instance,
                           double vnew_raw, double vnew_lim, double vold, double vto);
    void (*on_gmin)(void *ctx, double val, int converged, int iters);
    void (*on_src_step)(void *ctx, double factor, int converged, int iters);
    void (*on_device_dio)(void *ctx, const char *inst, double vd, double id,
                          double gd, double ieq);
    void (*on_matrix)(void *ctx, int size, double min_piv, double max_piv, double ratio);
} NgspiceDiagSink;

extern const NgspiceDiagSink *ngspice_diag_sink;
/* Correlation id for DiagEvent (UTF-8); may be "" or NULL (treated as ""). */
extern const char *ngspice_diag_request_id;

#define DIAG_EMIT(...) \
    do { \
        if (ngspice_diag_fp) \
            fprintf(ngspice_diag_fp, __VA_ARGS__); \
    } while (0)

void ngspice_diag_init(void);
void ngspice_diag_close(void);

int ngspice_diag_wants_nr(void);
int ngspice_diag_wants_matrix(void);
int ngspice_diag_wants_gmin(void);
int ngspice_diag_wants_src(void);
int ngspice_diag_wants_device(void);
int ngspice_diag_wants_pnjlim(void);
int ngspice_diag_wants_fetlim(void);

void ngspice_diag_emit_nr_iter(int iter, double max_rhs, double max_dx, double damp,
                               int noncon, int converged);
void ngspice_diag_emit_limiter_pnj(const char *instance, double vnew_raw, double vnew_lim,
                                   double vold, double vcrit);
void ngspice_diag_emit_limiter_fet(const char *instance, double vnew_raw, double vnew_lim,
                                   double vold, double vto);
void ngspice_diag_emit_gmin(double val, int converged, int iters);
void ngspice_diag_emit_src_step(double factor, int converged, int iters);
void ngspice_diag_emit_device_dio(const char *inst, double vd, double id, double gd,
                                  double ieq);
void ngspice_diag_emit_matrix(int size, double min_piv, double max_piv, double ratio);

#endif /* NGSPICE_DIAGHOOKS_H */
