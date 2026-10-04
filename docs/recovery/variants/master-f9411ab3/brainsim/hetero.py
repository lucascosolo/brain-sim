import numpy as np

FRAME_CELL_CAP = 32


def constants(p):
    return (getattr(p, "HETERO_TRIGGER_SPIKES", 5), getattr(p, "HETERO_ETA", 0.15),
            getattr(p, "HETERO_Z_CLIP", 2.0), getattr(p, "HETERO_FLOOR_FRAC", 0.10))


def redistribute(x, post, w, w_max, n, eta, z_clip, floor_frac):
    x = np.asarray(x, np.float64)
    k = np.bincount(post, minlength=n).astype(np.float64)
    mean = np.bincount(post, weights=x, minlength=n) / np.maximum(k, 1.0)
    var = np.bincount(post, weights=(x - mean[post]) ** 2, minlength=n) / np.maximum(k, 1.0)
    sd = np.sqrt(var)
    z = np.where(sd[post] > 0, (x - mean[post]) / np.where(sd[post] > 0, sd[post], 1.0), 0.0)
    np.clip(z, -z_clip, z_clip, out=z)
    z -= (np.bincount(post, weights=z, minlength=n) / np.maximum(k, 1.0))[post]
    wm = np.asarray(w_max, np.float64)
    w0 = np.asarray(w, np.float64)
    return np.clip(w0 + eta * wm * z, np.minimum(w0, floor_frac * wm), wm)
