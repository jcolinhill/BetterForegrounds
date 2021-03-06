import numpy as np
import glob, pickle
import matplotlib.pyplot as plt
import healpy as hp
from astropy.io import fits

"""
implementation of the estimator from http://arxiv.org/abs/1312.0437 for polarized intensity
all analysis done presently in Galactic coordinates
all analysis done presently at native resolution of Planck 353 GHz maps (fwhm = 4.94 arcmin)
all analysis done presently in terms of Planck/Healpix dust polarization angle (i.e., not IAU B-field angle)
"""
# resolution
Nside=2048
Npix = 12*Nside**2

def P_Plasz(map353,cov353): #map353=[T,Q,U],cov353=[[TT,TQ,TU],[TQ,QQ,QU],[TU,QU,UU]]
    """
    implement the Plaszczynski+ estimator
    """
    # 1) compute unbiased estimator of polar angle (phi_i = arctan(U_i/Q_i)) *Not to be confused with the polarization angle*
    mapphi353 = np.arctan2(map353[2], map353[1])
    
    # 2) compute the "variable bias" (Eq. 35 of http://arxiv.org/abs/1312.0437)
    # first, get theta from their Eq. 32
    Plasz_theta = np.mod(0.5*np.arctan2(2.0*cov353[1,2], cov353[1,1]-cov353[2,2]), np.pi)
    # second, implement their Eq. 33
    Plasz_sigQp2 = cov353[1,1]*(np.cos(Plasz_theta))**2.0 + cov353[2,2]*(np.sin(Plasz_theta))**2.0 + cov353[1,2]*np.sin(2.0*Plasz_theta)
    Plasz_sigUp2 = cov353[1,1]*(np.sin(Plasz_theta))**2.0 + cov353[2,2]*(np.cos(Plasz_theta))**2.0 - cov353[1,2]*np.sin(2.0*Plasz_theta)
    # third, implement their Eq. 35
    mapvarbias353 = np.sqrt(Plasz_sigUp2*(np.cos(mapphi353-Plasz_theta))**2.0 + Plasz_sigQp2*(np.sin(mapphi353-Plasz_theta))**2.0)
    
    # 3) implement their Eq. 37
    mapPnaive353 = np.sqrt(map353[1]**2.0 + map353[2]**2.0)
    mapP353 = mapPnaive353 - mapvarbias353**2.0 * (1.0 - np.exp(-mapPnaive353**2.0 / mapvarbias353**2.0)) / (2.0*mapPnaive353)
    
    # 4) implement their Eq. 36 to obtain a noise estimate
    mapsigP353 = np.sqrt(Plasz_sigQp2*(np.cos(mapphi353-Plasz_theta))**2.0 + Plasz_sigUp2*(np.sin(mapphi353-Plasz_theta))**2.0)
    
    # output naive estimate, debiased estimate, and noise on debiased estimate
    return mapPnaive353, mapP353, mapsigP353

# input Planck 353 GHz maps (Galactic)
planckroot = "/Users/susanclark/Dropbox/Planck/"
planckmapfn = planckroot+"HFI_SkyMap_353_2048_R2.02_full.fits"

# full-mission -- N.B. these maps are already in RING ordering, despite what the header says
map353Gal = np.zeros((3,Npix)) #T,Q,U
cov353Gal = np.zeros((3,3,Npix)) #TT,TQ,TU,QQ,QU,UU
#map353Gal[0], map353Gal[1], map353Gal[2], cov353Gal[0,0], cov353Gal[0,1], cov353Gal[0,2], cov353Gal[1,1], cov353Gal[1,2], cov353Gal[2,2], header353Gal = hp.fitsfunc.read_map(planckmapfn, field=(0,1,2,4,5,6,7,8,9), h=True)

# read in explicitly from HDU name
planck353full = fits.open(planckmapfn)
sigTTsq = planck353full[1].data['II_cov']
sigTQsq = planck353full[1].data['IQ_cov']
sigTUsq = planck353full[1].data['IU_cov']
sigQQsq = planck353full[1].data['QQ_cov']
sigUUsq = planck353full[1].data['UU_cov']
sigQUsq = planck353full[1].data['QU_cov']

cov353Gal[0, 0, :] = sigTTsq
cov353Gal[1, 1, :] = sigQQsq
cov353Gal[1, 2, :] = sigQUsq
cov353Gal[2, 2, :] = sigUUsq

map353Gal[0, :] = planck353full[1].data['I_STOKES']
map353Gal[1, :] = planck353full[1].data['Q_STOKES']
map353Gal[2, :] = planck353full[1].data['U_STOKES']

# apply estimator
mapPnaive353Gal, mapP353Gal, mapsigP353Gal = P_Plasz(map353Gal, cov353Gal)

# save de-biased P map
hp.fitsfunc.write_map(planckroot+'HFI_SkyMap_353_2048_R2.02_full_PdebiasPlasz_RING.fits', mapP353Gal, coord='G')
# save noise estimate for de-biased P map
hp.fitsfunc.write_map(planckroot+'HFI_SkyMap_353_2048_R2.02_full_sigPdebiasPlasz_RING.fits', mapsigP353Gal, coord='G')
# image
plt.clf()
hp.mollview(mapP353Gal, unit='K_CMB', title='P_353 Debiased Plaszczynski', coord='G', min=0.0, max=1.0e-3)
plt.savefig('../figures/HFI_SkyMap_353_2048_R2.02_full_PdebiasPlasz_RING.png')
# image of biased naive estimator
plt.clf()
hp.mollview(mapPnaive353Gal, unit='K_CMB', title='P_353 Naive', coord='G', min=0.0, max=1.0e-3)
plt.savefig('../figures/HFI_SkyMap_353_2048_R2.02_full_Pnaive_RING.png')
# difference of the estimators
plt.clf()
hp.mollview(mapPnaive353Gal-mapP353Gal, unit='K_CMB', title='P_353 Naive - P_353 Debiased Plaszczynski', coord='G', min=0.0, max=1.0e-3)
plt.savefig('../figures/HFI_SkyMap_353_2048_R2.02_full_Pnaive_PdebiasPlasz_diff_RING.png')
# image of the estimated SNR for the debiased estimator
plt.clf()
hp.mollview(mapP353Gal/mapsigP353Gal, unit='SNR', title='P_353 Debiased Plaszczynski SNR', coord='G', min=0.0, max=5.0)
plt.savefig('../figures/HFI_SkyMap_353_2048_R2.02_full_PdebiasPlasz_SNR_RING.png')
