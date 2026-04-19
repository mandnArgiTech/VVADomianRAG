# MAVLink Architecture, Network Routing, and Cryptographic Signing

_Generated 2026-04-15 12:33 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/ap_message.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_Dummy.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_Dummy.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_MAVLink.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_MAVLink.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/MAVLink_routing.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/MAVLink_routing.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/GCS_MAVLink/GCS_Signing.cpp`

# Chapter: MAVLink Architecture, Network Routing, and Cryptographic Signing

### Introduction
This chapter details the mathematical and software architecture for the MAVLink communication stack in ArduPilot, specifically engineered for the deterministic, high-reliability networking required by a 1200 kg agricultural rover. The system must maintain robust multi-channel communication (USB, radios, companion links) despite skid-steering vibrations, EMI from 400A drive motors, and the vehicle's high rotational inertia. The implementation spans the ArduPilot files `MAVLink_routing.cpp`, `GCS_Signing.cpp`, and `GCS_MAVLink.cpp`, providing loop-free packet routing, cryptographic integrity verification, and prioritized, rate-limited telemetry streaming that respects the 400Hz control loop's real-time constraints.

### Mathematical Formulation

#### Multi-Link Network Routing with Loop Prevention
The routing system manages up to \( N = 4 \) physical channels, each assigned a unique bitmask: Channel 0 (USB): \( 0x01 \), Channel 1 (Radio 1): \( 0x02 \), Channel 2 (Radio 2): \( 0x04 \), Channel 3 (Companion): \( 0x08 \). A routing table entry for a source system \( S \) with component \( C \) is a tuple:
\[
R = (\text{sysid}, \text{compid}, \text{route\_mask}, \text{hop\_count}, \text{last\_seen\_ms})
\]
where \( \text{route\_mask} \in [0, 2^N - 1] \) is a bitwise OR of channels that have seen packets from \( S \). When a packet \( P \) arrives on channel \( C_{in} \), the forwarding algorithm is:
1.  Let \( \text{chan\_mask} = 1 \ll C_{in} \).
2.  Lookup \( R \) for \( S \). If it does not exist, create it with \( \text{route\_mask} = \text{chan\_mask} \) and \( \text{hop\_count} = \text{MAX\_HOPS} \).
3.  Update \( R \): \( \text{route\_mask} = \text{route\_mask} \mid \text{chan\_mask} \), reset \( \text{last\_seen\_ms} \).
4.  Forward \( P \) to all channels \( C_{out} \) where \( (\text{route\_mask} \ \& \ (1 \ll C_{out})) \neq 0 \) and \( C_{out} \neq C_{in} \).
5.  Decrement \( R.\text{hop\_count} \). If zero, delete \( R \).

**Loop Prevention Proof:** The system is loop-free because the route mask is monotonic (only adds channels), the hop count strictly decreases per forward, and forwarding excludes the source channel. The maximum path length is bounded by \( \text{MAX\_HOPS} \) (typically 5).

**Rover-Specific Considerations:** The garbage collection timeout \( \text{MAVLINK\_ROUTING\_TIMEOUT\_MS} \) must be longer than the worst-case latency induced by the rover's 150 kg·m² rotational inertia during skid-steering turns, which can cause temporary communication blackouts. The routing table size is limited to 32 entries (\( O(M) \) memory) to fit within the STM32F4's SRAM constraints.

#### MAVLink 2.0 Cryptographic Signing with Inertia-Aware Replay Protection
Packet signing uses HMAC-SHA256 with a 32-byte secret key \( K \). The signature \( \text{SIG} \) for a message with payload \( M \) of length \( L \), link identifier \( \text{link\_id} \), and 48-bit timestamp \( T \) is:
\[
\text{SIG} = \text{Truncate}_6\left( \text{SHA256}\left( K \ \| \ \text{SHA256}\left( K \ \| \ [\text{link\_id} \ | \ T \ | \ M] \right) \right) \right)
\]
where \( \| \) denotes concatenation and \( \text{Truncate}_6 \) takes the first 6 bytes of the 32-byte hash.

**Replay Protection with Skid-Steering Jitter:** The receiver maintains a sliding window \( W \) of the last 64 accepted timestamps. A timestamp \( T_{\text{recv}} \) is accepted if:
1.  \( |T_{\text{current}} - T_{\text{recv}}| \leq \text{TIMEOUT\_MS} \) (typically 60,000 ms).
2.  \( T_{\text{recv}} \notin W \).

For the heavy rover, the timestamp comparison must account for clock drift exacerbated by vibration. The acceptance window is effectively widened by a factor proportional to the vehicle's kinetic energy \( E_k = \frac{1}{2} m v^2 + \frac{1}{2} J_{zz} \dot{\theta}^2 \), where \( m = 1200 \text{ kg} \) and \( J_{zz} = 150 \text{ kg·m}^2 \). This prevents false rejections during high-dynamics maneuvers.

**Collision Resistance:** With a 6-byte (48-bit) signature, the brute-force collision probability is \( \approx 2^{-24} \), requiring ~16.7 million attempts, which is sufficient given the rover's low packet rate and the addition of the timestamp nonce.

#### Asynchronous Telemetry Stream Scheduling via Token Bucket Algorithm
Each communication channel \( i \) implements a token bucket for rate limiting. The bucket state is \( (\text{tokens}_i, \text{rate}_i, \text{capacity}_i, \text{last\_update}_i) \), where 1 token = 1 byte.

**Token Replenishment:** At current time \( t \) (ms):
\[
\Delta t = t - \text{last\_update}_i
\]
\[
\text{new\_tokens}_i = \frac{\Delta t \times \text{rate}_i}{1000}
\]
\[
\text{tokens}_i = \min(\text{tokens}_i + \text{new\_tokens}_i, \ \text{capacity}_i)
\]
\[
\text{last\_update}_i = t
\]

**Transmission Condition:** A message of size \( S \) can be transmitted on channel \( i \) iff \( \text{tokens}_i \geq S \). After transmission, \( \text{tokens}_i = \text{tokens}_i - S \).

**Priority Queueing:** Messages have priority \( p \in [0, 255] \) (0 = CRITICAL, e.g., heartbeat; 255 = BACKGROUND). The scheduler processes all channels, transmitting the highest-priority message available for which tokens are sufficient. This ensures the rover's critical state data (attitude, GPS) is always transmitted ahead of lower-priority telemetry (logs, parameters), maintaining control loop stability even under limited bandwidth.

**Rover Bandwidth Allocation:** The total bandwidth \( B_{\text{total}} \) is divided among channels. For a rover with high-inertia skid-steering, the radio channel to the ground station may be allocated higher \( \text{rate}_i \) to ensure low-latency telemetry during turns, while the companion computer link may have a lower rate to prevent it from monopolizing the STM32's processing budget.

#### STM32 DMA Buffer Sizing for Vibration Tolerance
The DMA double-buffer for UART reception must be sized to prevent overruns during worst-case processing delays caused by the rover's vibration-induced task jitter. The required buffer size \( \text{Buf}_{\text{size}} \) per buffer is:
\[
\text{Buf}_{\text{size}} = R_{\text{baud}} \times \frac{T_{\text{cycle}} + \Delta T_{\text{vib}}(m, a)}{10 \times \text{bits\_per\_byte}}
\]
where \( T_{\text{cycle}} = 2.5 \text{ ms} \) (400Hz period), \( \Delta T_{\text{vib}} = k_v \cdot m \cdot a \) is the vibration-induced jitter, \( m = 1200 \text{ kg} \), \( a \) is chassis acceleration, and \( k_v \) is an empirical constant. For a 921600 baud link and typical rover vibration, this yields a buffer size of ~256 bytes, implemented as two buffers for ping-pong DMA.

### C++ Implementation

### Channel Arbitration and Hop-Count Routing (MAVLink_routing.cpp)

The `MAVLink_routing` class implements the mathematical routing model with deterministic loop prevention. The core data structure is the `RouteEntry` struct, which directly maps to the mathematical routing table entry: `sysid` and `compid` form the source tuple S, `route_mask` is the 8-bit bitmask of channels, `hop_count` implements the decreasing hop counter, and `last_seen_ms` enables garbage collection. The `check_and_forward()` function executes the forwarding algorithm: it converts the incoming channel `chan` to a bitmask `chan_mask = 1U << (uint8_t)chan`, then calls `find_route()` to locate the route entry R for the source system/component. If no route exists, `add_route()` creates one with `route_mask = 0` and `hop_count = MAVLINK_ROUTING_HOP_MAX`. The route is updated with `route->route_mask |= chan_mask`, implementing the mathematical operation `route_mask |= (1 << C)`. The forwarding loop iterates through all channels `i` from 0 to `MAVLINK_COMM_NUM_BUFFERS-1`, checking if `route->route_mask & (1U << i)` is true and `i != chan`. This implements "forward P to all channels in route_mask except C." After forwarding, `--route->hop_count` decrements the hop count, and if zero, the route is removed, guaranteeing the maximum path length ≤ MAX_HOPS. The `update()` method performs garbage collection by scanning all routes and removing those where `now_ms - routes[i].last_seen_ms > MAVLINK_ROUTING_TIMEOUT_MS`. RTOS threading is implicit: `check_and_forward()` is called from UART interrupt handlers or the main loop, while `update()` runs periodically, requiring no explicit locks due to the single-writer (interrupt) design.

### MAVLink 2.0 SHA-256 Packet Signing (GCS_Signing.cpp)

The `GCS_Signing` class implements the HMAC-SHA256 signature generation and verification with timestamp-based replay protection. The mathematical signature formula `SIG = Truncate₆(SHA-256(K || SHA-256(K || [link_id | T | payload])))` is directly implemented in `sign_packet()`. The function constructs the signing buffer `data[]` with layout `[link_id (1B) | timestamp (6B) | payload (L bytes)]`, exactly matching the mathematical buffer B. The `sha256_hmac()` function computes the double-hash: it first calls the hardware-accelerated `HASH_HMAC_Start()` (or software mbedtls fallback) with the secret key `secret_key` and the data buffer, producing the 32-byte `signature_full`. The first 6 bytes are copied to the message payload via `memcpy(&msg->payload64[msg->len], signature_full, 6)`, implementing the truncation `Truncate₆`. The timestamp T is stored in the payload before the signature. The `verify_packet()` function implements the replay protection mathematics: `verify_timestamp()` checks if `|now - timestamp| ≤ SIGNING_TIMESTAMP_MAX_DIFF_US` and scans the `timestamp_window[]` array (size 64) for duplicates, rejecting if found. This implements the sliding window W with acceptance condition `|T_current - T_received| ≤ TIMEOUT_MS` and rejection if `T_received ∈ W`. The signature is recomputed on the received data (excluding the stored timestamp and signature bytes) and compared via `memcmp()`. RTOS considerations: the `timestamp_window` is updated after successful verification, and the window index `window_index` wraps modulo 64. The hardware-accelerated path uses the STM32 HASH peripheral via `HAL_HMAC_Start()`, which offloads the SHA-256 computation from the CPU.

### Asynchronous Telemetry Stream Scheduling (GCS_MAVLink.cpp)

The `StreamScheduler` class implements the token bucket rate limiting algorithm with priority queueing. The `StreamRate` struct holds the token bucket state: `tokens` (current tokens), `rate_bps` (tokens per second), `capacity` (maximum tokens), and `last_update_ms`. The `update_tokens()` method implements the token replenishment formula: for each stream, it calculates `dt_ms = now_ms - stream.last_update_ms`, then computes `new_tokens = (stream.rate_bps * dt_ms) / 1000`. This is the discrete-time implementation of `new_tokens = (Δt × rate) / 1000`. The tokens are added and clamped: `stream.tokens = (total_tokens > stream.capacity) ? stream.capacity : total_tokens`, which is `tokens = min(tokens + new_tokens, capacity)`. The `QueuedMessage` struct holds a message with its `priority` (0-255). The `queue_message()` function adds messages to the circular buffer `queue[]` of size `MAX_QUEUE_SIZE`. The `update()` method implements the scheduling algorithm: it first calls `update_tokens()` to replenish all streams, then iterates through priority levels from 0 to 255. For each channel, `find_message_for_channel()` locates the highest-priority message (lowest priority number) for that channel. If the stream has enough tokens (`stream.tokens >= msg->size`), the message is sent via `mavlink_send_buffer()` and tokens are deducted (`stream.tokens -= msg->size`). This enforces the transmission condition `tokens ≥ S`. The message is then removed from the queue by shifting remaining elements. This priority-based iteration ensures CRITICAL (priority 0) messages are always serviced before HIGH (10), MEDIUM (50), etc., preventing starvation of lower priorities because tokens accumulate during idle periods. RTOS execution: `update()` is called from the main loop, while `queue_message()` may be called from various threads; the circular buffer operations are non-blocking and interrupt-safe.

### STM32 UART DMA Configuration for High-Speed MAVLink

The `MAVLink_UART_DMA` class implements low-level hardware acceleration for MAVLink communication. The `init()` function configures the STM32's USART and DMA controllers. The baud rate is set via `uart->BRR = SystemCoreClock / 921600`, establishing the physical layer data rate. DMA is configured for both transmission and reception: `dma_rx` is set to circular mode with double buffering (`rx_buffer[2][MAVLINK_MAX_PACKET_LEN]`), enabling continuous reception without CPU intervention. The `send_packet()` function queues packets in the `tx_queue` (size 16) and starts transmission via DMA if not already in progress. The `start_next_transmission()` function sets the DMA source address to the packet data and length, then enables the DMA stream. This offloads byte-by-byte transmission from the CPU. The interrupt handlers `handle_tx_complete()` and `handle_rx_complete()` manage buffer switching and packet processing. This DMA-based design ensures that the 400Hz control loop is not blocked by serial I/O, as packet transmission/reception occurs in parallel with main thread execution. The double-buffered receive scheme guarantees no data loss even at high baud rates (921600), meeting the real-time requirements for a 1200 kg rover where communication latency directly affects control responsiveness.

### Hardware Crypto Acceleration for SHA-256

The `HardwareSHA256` class leverages the STM32's cryptographic hardware accelerator. The `init()` function enables the HASH peripheral clock and initializes the `HASH_HandleTypeDef`. The `compute_hmac()` function configures the HMAC with key and algorithm selection (`HASH_ALGOSELECTION_SHA256`), then starts the computation via `HAL_HMAC_Start()`. The hardware computes the full HMAC-SHA256, implementing the mathematical operation `SHA-256(K || SHA-256(K || data))` in dedicated silicon, completing in a fixed number of cycles independent of data length. The function polls `HAL_HMAC_GetState()` until completion, but since the operation is hardware-accelerated, this blocking time is minimal (~μs). This hardware offload is critical for the rover's 400Hz loop: software SHA-256 would consume significant CPU cycles, potentially missing the 2.5ms deadline, especially when signing multiple packets per cycle. The hardware implementation ensures cryptographic integrity without compromising real-time performance, even under the vibration and EMI load from 400A drive motors.