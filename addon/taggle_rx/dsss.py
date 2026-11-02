"""Partial-band DSSS acquisition and tracking; no payload interpretation."""
import numpy as np
from scipy import fft, ndimage, optimize


class Fold:
    """Cubic fractional-delay interpolation onto a common integer period grid."""
    def __init__(self, z, size=2048):
        self.real = ndimage.spline_filter(z.real, order=3)
        self.imag = ndimage.spline_filter(z.imag, order=3)
        self.length = len(z)
        self.size = size

    def rows(self, period, offset=0., indices=None):
        if indices is None:
            indices = np.arange(int((self.length-offset)/period)-1)
        offset = np.asarray(offset)
        if offset.ndim:
            offset = offset[:, None]
        t = offset + np.asarray(indices)[:, None]*period + np.arange(self.size)*period/self.size
        if t.min() < 0 or t.max() >= self.length:
            raise ValueError('fold outside available samples')
        pos = t.ravel()[None, :]
        re = ndimage.map_coordinates(self.real, pos, order=3, prefilter=False)
        im = ndimage.map_coordinates(self.imag, pos, order=3, prefilter=False)
        return (re+1j*im).reshape(t.shape)


def template(rows, iterations=12):
    # Power iteration of the leading complex singular vector; per-row phase
    # and BPSK sign are nuisance scalars. Seeds are deterministic.
    v = rows[len(rows)//2].copy()
    v /= max(np.linalg.norm(v), 1e-30)
    for _ in range(iterations):
        weights = rows @ v.conj()
        v = weights.conj() @ rows
        v /= max(np.linalg.norm(v), 1e-30)
    return v


def projection(rows):
    v = template(rows[::2], 8)
    return float(np.mean(abs(rows[1::2] @ v.conj())**2)), v


def acquire(fold, period_prior, fit_start, fit_end):
    """Fit clock and symbol boundary with disjoint training/validation rows.

    Validation selects timing, so its score is exploratory, not a false-alarm
    probability. Final per-symbol correlations use opposite-parity templates.
    """
    indices = np.unique(np.linspace(fit_start, fit_end, 128).astype(int))
    def loss(p, offset=0):
        return -projection(fold.rows(p, offset, indices))[0]
    fit = optimize.minimize_scalar(loss, bounds=(period_prior-.10, period_prior+.10),
                                   method='bounded', options={'xatol': .00015})
    period = float(fit.x)
    offsets = np.arange(64)*period/64
    scores = [-loss(period, x) for x in offsets]
    offset = float(offsets[np.argmax(scores)])
    fine = np.arange(-24, 25, 3) + offset
    fine %= period
    scores = [-loss(period, x) for x in fine]
    offset = float(fine[np.argmax(scores)])
    # Refit the period after placing data transitions at row boundaries.
    fit = optimize.minimize_scalar(lambda p: loss(p, offset),
                                   bounds=(period-.012, period+.012),
                                   method='bounded', options={'xatol': .00005})
    return float(fit.x), offset, float(-fit.fun)


def cross_correlations(rows, fit_indices):
    """Each row is projected against a template trained on the other parity."""
    reference = template(rows[fit_indices])
    w = np.empty(len(rows), complex)
    for parity in (0, 1):
        train = fit_indices[fit_indices % 2 != parity]
        v = template(rows[train])
        v *= np.exp(1j*np.angle(np.vdot(v, reference)))
        selected = np.arange(parity, len(rows), 2)
        w[selected] = rows[selected] @ v.conj()
    return w, reference


def active_span(w):
    """Longest sustained matched-filter episode; never bridge a distant event."""
    power = abs(w)**2
    edge = np.r_[power[:40], power[-40:]]
    noise = float(np.median(edge)/np.log(2))
    threshold = max(10*noise, .16*np.percentile(power, 85))
    mask = power > threshold
    mask = ndimage.binary_closing(mask, np.ones(3))
    edges = np.diff(np.r_[False, mask, False].astype(int))
    spans = list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))
    if not spans:
        raise ValueError('no sustained despread signal')
    a, b = max(spans, key=lambda ab: ab[1]-ab[0])
    if b-a < 80:
        raise ValueError('despread episode too short')
    return int(a), int(b), noise


def costas(w, alpha=.45, beta=.045):
    """Second-order BPSK Costas loop, phase ambiguous by pi.

    The first symbol chooses the positive branch; no assumed sync bits enter
    tracking. The independent differential output is real(w[n] conj(w[n-1])).
    """
    phase = float(np.angle(w[0]))
    freq = float(np.median(np.angle((w[1:16]*w[:15].conj())**2)/2))
    phases, corrected, errors = [], [], []
    for x in w:
        predicted = phase + freq
        err = float(np.angle((x*np.exp(-1j*predicted))**2)/2)
        phase = predicted + alpha*err
        freq += beta*err
        phases.append(phase)
        corrected.append(x*np.exp(-1j*phase))
        errors.append(err)
    corrected = np.asarray(corrected)
    bits = (corrected.real < 0).astype(np.uint8)
    differential = ((w[1:]*w[:-1].conj()).real < 0).astype(np.uint8)
    reconstructed = np.r_[0, np.bitwise_xor.accumulate(differential)].astype(np.uint8)
    return bits, differential, reconstructed, corrected, np.array(phases), np.array(errors)


def timing_track(fold, period, offset, a, b, v):
    """Local early/late timing checks; return offsets without fitting bits."""
    track = []
    for first in range(a+8, b-23, 32):
        indices = np.arange(first, min(first+24, b))
        def objective(delta):
            rows = fold.rows(period, offset+delta, indices)
            return -float(np.mean(abs(rows @ v.conj())**2))
        fit = optimize.minimize_scalar(objective, bounds=(-2.5, 2.5), method='bounded')
        track.append((float(indices.mean()), float(fit.x)))
    return track


def recover_dsss(z, carrier, period_prior, fit_start, fit_end, rate=2400000):
    """Shared blind acquisition/tracking for offline and continuous receivers.

    Fit bounds are sample offsets in this bounded IQ window, not capture priors.
    The caller must independently check the spreading code and frame checksums.
    """
    z = np.asarray(z, np.complex64).copy()
    z -= z.mean()
    z *= np.exp(-2j*np.pi*carrier*np.arange(len(z))/rate)
    fold = Fold(z)
    fa = max(1, int(fit_start/period_prior))
    fb = min(int(fit_end/period_prior)-2, int(len(z)/period_prior)-4)
    if fb-fa < 24:
        raise ValueError('too few candidate periods')
    period, offset, score = acquire(fold, period_prior, fa, fb)
    rows = fold.rows(period, offset)
    fit_indices = np.arange(fa, min(fb, len(rows)))
    w, v = cross_correlations(rows, fit_indices)
    a, b, noise = active_span(w)
    track = timing_track(fold, period, offset, a, b, v)
    ticks, delta = np.array(track).T
    poly = np.polyfit(ticks-(a+b)/2, delta, min(2, len(ticks)-1))
    indices = np.arange(len(rows))
    adjustment = np.clip(np.polyval(poly, indices-(a+b)/2), -2.5, 2.5)
    rows = fold.rows(period, offset+adjustment, indices)
    w, v = cross_correlations(rows, fit_indices)
    a, b, noise = active_span(w)
    bits, diff, reconstructed, corrected, phase, error = costas(w[a:b])
    snr = 10*np.log10(np.maximum(abs(w[a:b])**2/noise-1, 1e-12))
    return dict(bits=bits, differential=diff, reconstructed=reconstructed,
                corrected=corrected, phase=phase, phase_error=error,
                period_samples=period, first_sample=offset+a*period+adjustment[a],
                last_sample=offset+b*period+adjustment[b-1],
                snr_median_db=float(np.median(snr)),
                snr_p10_db=float(np.percentile(snr, 10)),
                noise_correlation_power=noise, template=v, acquisition_score=score,
                timing_track=track, timing_polynomial=poly, timing_ticks=ticks,
                timing_delta=delta, adjustment=adjustment, offset=offset,
                active_start=a, active_end=b, correlations=w)


def interior_bins(size, period, rate, carrier_offset):
    bins = np.rint(fft.fftfreq(size)*size).astype(int)
    hz = bins*rate/period
    keep = (hz > max(-.45*rate, -rate/2-carrier_offset)+20000) & (hz < .45*rate)
    return bins, keep


def predicted_template(code, size, period, rate, carrier_offset, chip_shift):
    """Synthesize an interior-band template from chips with a flat RF filter."""
    bins, keep = interior_bins(size, period, rate, carrier_offset)
    spec = fft.fft(2.*np.asarray(code)-1)
    y = np.zeros(size, complex)
    k = bins[keep]
    y[keep] = spec[k % len(code)]*np.exp(-2j*np.pi*k*chip_shift/len(code))
    v = fft.ifft(y)
    return v/np.linalg.norm(v)

