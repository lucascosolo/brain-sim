SEED, DT_MS = 1, 1
D_MAX = 8
S_MAX = 600_000

REGIONS = {
    "sense": dict(n_exc=200, n_inh=0, r_target_exc=2.0, r_target_inh=0.0, w_max=2.0, a_plus=0.0, a_minus=0.0),
    "ctx": dict(n_exc=1600, n_inh=400, r_target_exc=4.0, r_target_inh=8.0, w_max=2.0, a_plus=0.01, a_minus=0.012),
    "hpc": dict(n_exc=320, n_inh=80, r_target_exc=1.0, r_target_inh=6.0, w_max=3.0, a_plus=0.05, a_minus=0.06),
}

PROJECTIONS = [
    ("sense", "ctx", 30, 0.12),
    ("ctx", "ctx", 40, 0.25),
    ("ctx", "hpc", 30, 0.25),
    ("hpc", "hpc", 20, 0.25),
    ("hpc", "ctx", 10, 0.25),
]
EI_MOTIF = 0.25
K_IN_IMMATURE_FACTOR = 2.0
WINDUP_WINDOW_SWEEPS = 10
WINDUP_MIN_PROGRESS = 0.02
WINDUP_NOISE_SIGMAS = 3.0
WINDUP_CAP_FRAC = 0.9

TAU_M_MS = 20.0
V_REST_MV = -70.0
V_RESET_MV = -65.0
THETA_0_MV = -50.0
T_REF_MS = 2
TAU_THETA_MS = 150.0
D_THETA_MV = 1.5
NOISE_SIGMA_MV = {"sense": 0.0, "ctx": 2.35, "hpc": 1.8}
SENSE_SPONT_HZ = 5.0
CONDUCT_DELAY_TICKS = 1000

TAU_TRACE_MS = 20.0
G_WAKE, G_SLEEP = 1.0, 0.3
W_INIT_LO, W_INIT_HI = 0.2, 0.6
I_GAIN = 2.5

CONN_SIGMA = 0.25
DELAY_SPREAD = 7.0

ETA_SCALING = 0.1
SCALING_CLIP = 0.1
RATE_EMA_ALPHA = 0.4
ACT_REF_HZ = 10.0

SWEEP_TICKS = 1000
STRUCT_BASE = 0.05
STRUCT_AGE_TAU_S = 60.0
W_PRUNE_FRAC = 0.05
W_GROW_FRAC = 0.15
GROW_BETA = 2.0

WAKE_TICKS, SLEEP_TICKS = 60_000, 20_000

PATTERNS = 4
PATTERN_FRAC = 0.2
PATTERN_AMP_MV = 1.3

FRAME_SPIKE_CAP = 4000
FRAME_STRUCT_CAP = 2000
SYN_SAMPLE = 3000
V_TRACE_TICKS = 500
HIST_BINS = 24

STIMLOG_MAX = 64
STIM_ACTIVE_MAX = 256

# Encode-mode (SPEC 8.12): a labelled proxy schedule, off by default; not biology.
ENCODE_K = 16                      # W = top-k hpc E cells of the identification pass
ENCODE_DELTA_FRAC = 0.15           # donor -> W bump, fraction of w_max_n[post], clamped
ENCODE_RECURRENT_DELTA_FRAC = 0.05 # W -> W bump, same rule
ENCODE_GRACE_TICKS = 1000          # mask stays on W this long after the presentation ends

# Two-timescale weights (SPEC 8.13): a labelled proxy, off by default; not biology.
SLOW_WEIGHTS = False       # the flag; False is today's plant bit for bit
SLOW_TAG_FRAC = 0.85       # fast w / w_max at a sweep at or above this latches the slow component
SLOW_TAU_SWEEPS = 300      # per-sweep decay of the slow component, exp(-1 / SLOW_TAU_SWEEPS)
