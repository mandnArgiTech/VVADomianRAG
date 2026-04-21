# ngspice-zmq-server: ROUTER/Batch + PUB diagnostics (Story J). Lives in the ngspice fork.
# Requires: ngspice built with --with-ngshared -> ../install/lib/libngspice.so
# Build: make -C zmq_server
#
ZMQ_SRV := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
NG_TOP := $(abspath $(ZMQ_SRV)/..)
NGINST := $(NG_TOP)/install
# zmq_server -> ngspice -> Codebase -> Studio-Portable-RAG -> repo root
VVAD_ROOT := $(abspath $(ZMQ_SRV)/../../../..)

CC ?= gcc
CFLAGS ?= -O2 -g -Wall -Wextra
CPPFLAGS := -I$(ZMQ_SRV) -I$(ZMQ_SRV)/third_party \
	-I$(NG_TOP)/src/include -I$(NGINST)/include
LDFLAGS := -L$(NGINST)/lib -Wl,-rpath,$(NGINST)/lib \
	-L/usr/lib/x86_64-linux-gnu
LDLIBS := -lngspice -lzmq -l:libprotobuf-c.so.1 -lm

ngspice-server: ngspice_server.c ngspice_sim.pb-c.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -o $@ ngspice_server.c ngspice_sim.pb-c.c $(LDFLAGS) $(LDLIBS)

.PHONY: clean
clean:
	rm -f ngspice-server

# VidhuBijakam kernel demo: HTTP bridge -> ZMQ ngspice-server, Vite UI in vidhubijakam-demo/
.PHONY: demo-bridge demo-kernel-ui test-vidhubijakam-bridge
demo-bridge:
	@echo "Recommended: cd $(ZMQ_SRV) && ./ng.sh up   (uses ng.yaml; starts zmq server + bridge + Vite)"
	@echo "  ./ng.sh help | status | probe | down | restart | install | uninstall"
	@echo "Manual: cd vidhubijakam-demo && pip install -r requirements-bridge.txt && \\"
	@echo "  PYTHONPATH=$(abspath $(ZMQ_SRV))/python uvicorn bridge_server:app --host 127.0.0.1 --port 8000"
	@echo "Optional: NGSPICE_ZMQ_REP NGSPICE_ZMQ_PUB NGSPICE_BOOT_CACHE_SEC (boot ping cache, default 5s)"
demo-kernel-ui:
	@echo "Run (needs bridge on :8000):"
	@echo "  Terminal A: cd vidhubijakam-demo && npm run bridge"
	@echo "  Terminal B: cd vidhubijakam-demo && npm run demo:kernel"
	@echo "Or one shell: cd vidhubijakam-demo && npm run demo:kernel:local"
test-vidhubijakam-bridge:
	cd $(VVAD_ROOT) && pytest \
	  Studio-Portable-RAG/Codebase/ngspice/zmq_server/tests/test_vidhubijakam_bridge.py \
	  Studio-Portable-RAG/Codebase/ngspice/zmq_server/tests/test_ngspice_server_binary.py \
	  -o addopts= -q
