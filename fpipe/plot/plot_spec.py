import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter as gf
from scipy.signal import medfilt
from scipy.signal import convolve2d

from fpipe.plot import plot_map as pm

from scipy.interpolate import interp1d


def get_calibrator_spec(freq, cal_data_path='', cal_param=None):

    if cal_param is None:
        cal_data = np.loadtxt(cal_data_path)
        cal_spec_func = np.poly1d(np.polyfit(np.log10(cal_data[:,0]),
                                             np.log10(cal_data[:,1]),
                                             deg=2,))
                                             #w = 1./ cal_data[:,2]))
                                             #w = 1./ np.log10(cal_data[:,2])))

        cal_flux = 10. ** cal_spec_func(np.log10(freq)) # in mJy
    else:
        a, nu, idx = cal_param
        cal_flux = (10 ** a) * ((freq / nu) ** (idx) )

    kBol = 1.38e6 # mJy m^2 /K

    #eta   = 1. #0.6
    #_lambda = 2.99e8 / (freq * 1.e9)
    #_sigma = 1.02 * _lambda / 300. / 2. / (2. * np.log(2.))**0.5
    ##_sigma[:] = _sigma.max()
    ##_sigma = _lambda / 300. / 2. / (2. * np.log(2.))**0.5
    #Aeff   = eta * _lambda ** 2. / (2. * np.pi * _sigma ** 2.)
    #mJy2K  = Aeff / 2. / kBol

    #mJy2K  = np.pi * 300. ** 2. / 8. / kBol  * 0.9
    #print mJy2K

    data = np.loadtxt('/users/ycli/code/fpipe/fpipe/data/fwhm.dat')
    f = data[2:, 0] * 1.e-3
    d = data[2:, 1:]
    fwhm = interp1d(f, np.mean(d, axis=1), fill_value="extrapolate")

    eta   = 1.#0.9
    _lambda = 2.99e8 / (freq * 1.e9)
    #_sigma = 1.02 *  _lambda / 300. / np.pi * 180. * 3600.
    _sigma = fwhm(freq) * 60.
    mJy2K = eta * 1.36 * (_lambda*1.e2)**2. / _sigma**2.
    print 'Jy2K : %f'%(mJy2K[-1] * 1.e3)

    cal_T = cal_flux * mJy2K # in K

    return cal_T #, cal_T * factor

def get_source_spec(source, map_path='', map_name_list=['',], smoothing=True,
        c_list = None, label_list=None, n_rebin=64):

    if c_list is None:
        c_list = ['r',]  * len(map_name_list)
    if label_list is None:
        label_list = [None, ] * len(map_name_list)

    s_ra = source['ra']
    s_dec = source['dec']

    fig = plt.figure(figsize=[8, 3])
    ax  = fig.add_axes([0.1, 0.1, 0.85, 0.85])
    freq_min = 1.e9
    freq_max = -1.e9
    df = 0.001
    for mm, map_name in enumerate( map_name_list ):
        _c = c_list[mm]
        try:
            imap, ra, dec, ra_edges, dec_edges, freq, mask\
                = pm.load_maps(map_path, map_name, 'clean_map')
            nmap, ra, dec, ra_edges, dec_edges, freq, mask\
                = pm.load_maps(map_path, map_name, 'noise_diag')
        except IOError:
            print 'Map not found %s'%map_name
            continue

        if smoothing:
            map_mask = imap == 0.
            _pix = np.abs(dec[1] - dec[0]) * 60.
            pm.smooth_map(imap, _pix, freq)
            imap[map_mask] = 0.

        freq = freq / 1.e3
        print 'Freq. range %f - %f'%( freq.min(), freq.max())

        if freq.min() < freq_min: freq_min = freq.min()
        if freq.max() > freq_max: freq_max = freq.max()

        #_sig = 3./(8. * np.log(2.))**0.5 / 1.
        #imap = gf(imap, [1, _sig, _sig])
        #imap = gf(imap, [2, 1, 1])

        ra_idx = np.digitize(s_ra, ra_edges) - 1
        dec_idx = np.digitize(s_dec, dec_edges) - 1

        if ra_idx == -1 or ra_idx == imap.shape[1]:
            print "source %s out side of map ra range"%source['name']
            continue
        if dec_idx == -1 or dec_idx == imap.shape[2]:
            print "source %s out side of map dec range"%source['name']
            continue

        spec = imap[:, ra_idx, dec_idx]
        nois = nmap[:, ra_idx, dec_idx]

        #nois[nois<0.1] = 0
        spec[nois==0] = 0

        spec = np.ma.masked_equal(spec, 0)
        nois = np.ma.masked_equal(nois, 0)

        #spec[~spec.mask] = medfilt(spec[~spec.mask], 25)
        #ax.plot(freq, spec, '.', color='0.5', zorder=-1000)

        #n_rebin = 64
        if n_rebin != 1:
            freq_rebin = np.mean(freq.reshape(-1, n_rebin), axis=1)
            spec_rebin = spec.reshape(-1, n_rebin)
            nois_rebin = nois.reshape(-1, n_rebin)

            freq_rebin += df * mm/2

            spec_error = np.std(spec_rebin, axis=1)

            nois_rebin[nois_rebin==0] = np.inf
            nois_rebin = 1./nois_rebin

            spec_rebin = np.sum(spec_rebin * nois_rebin, axis=1)

            norm = np.sum(nois_rebin, axis=1)
            norm[norm==0] = np.inf
            spec_rebin /= norm
        else:
            freq_rebin = freq
            spec_rebin = spec
            spec_error = np.zeros_like(spec)

        ax.errorbar(freq_rebin, spec_rebin, yerr=spec_error,
                     fmt= 'o', color=_c, mfc='w', mec=_c, ms=3,
                     label=label_list[mm])

        # plot off
        spec = imap[:, ra_idx, dec_idx - 10]
        nois = nmap[:, ra_idx, dec_idx - 10]

        #nois[nois<0.1] = 0
        spec[nois==0] = 0

        spec = np.ma.masked_equal(spec, 0)
        nois = np.ma.masked_equal(nois, 0)

        #spec[~spec.mask] = medfilt(spec[~spec.mask], 25)
        #ax.plot(freq, spec, '.', color='0.5', zorder=-1000)

        #n_rebin = 64
        freq_rebin = np.mean(freq.reshape(-1, n_rebin), axis=1)
        spec_rebin = spec.reshape(-1, n_rebin)
        nois_rebin = nois.reshape(-1, n_rebin)

        spec_error = np.std(spec_rebin, axis=1)

        nois_rebin[nois_rebin==0] = np.inf
        nois_rebin = 1./nois_rebin

        spec_rebin = np.sum(spec_rebin * nois_rebin, axis=1)

        norm = np.sum(nois_rebin, axis=1)
        norm[norm==0] = np.inf
        spec_rebin /= norm

        ax.errorbar(freq_rebin, spec_rebin, yerr=spec_error,
                     fmt='bo', mec='b', ms=3)


    s_path = source['path']
    freq = np.linspace(freq_min, freq_max, 1000)
    cal_T = get_calibrator_spec(freq, s_path)
    ax.plot(freq, cal_T, 'k--', label=source['name'])

    ax.set_ylim(ymin=-0.5)

    ax.set_xlabel('Frequency [GHz]')
    ax.set_ylabel('T [K]')

    ax.legend(loc=1)

def check_spec(source_list):

    fig = plt.figure(figsize=[8, 3])
    ax  = fig.add_axes([0.1, 0.1, 0.85, 0.85])

    x = np.logspace(np.log10(0.05), np.log10(10), 100)

    for source in source_list:
        cal_path = source['path']
        cal_name = source['name']


        cal_data = np.loadtxt(cal_path)
        cal_spec_func = np.poly1d(np.polyfit(np.log10(cal_data[:,0]),
                                             np.log10(cal_data[:,1]),
                                             deg=1,))
        cal_flux = 10. ** cal_spec_func(np.log10(x)) # in mJy
        _l = ax.plot(x, cal_flux, '-', label=cal_name)
        _c = _l[0].get_color()
        ax.errorbar(cal_data[:, 0], cal_data[:, 1], cal_data[:,2], fmt='o',
                ecolor=_c, mec=_c, mfc=_c)

    ax.set_xlabel('Frequency [GHz]')
    ax.set_ylabel('Flux [mJy]')
    ax.legend()
    ax.loglog()

