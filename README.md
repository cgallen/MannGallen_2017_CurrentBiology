# MannGallen_2017_CurrentBiology
### Code to generate Virtual Fly Brain ROI time series from calcium imaging data in *Drosophila*

This repository contains code to reproduce ROI time series from the manuscript "Whole-brain calcium imaging reveals an intrinsic functional network in *Drosophila*"

### Code
- [make_roi_tseries.py](https://github.com/cgallen/MannGallen_2017_CurrentBiology/blob/master/make_roi_tseries.py): Code to generate time series from atlas ROIs

### This code produces the following:

###### ROI nifti files (will be overwritten if they already exist)

- Individual ROI files 

- Eroded ROI files 

###### Motion correction files (will *not* be overwritten if they already exist)

- 100-volume mean nifti file

- Motion corrected functional nifti file

- Motion parameters text file

###### ROI time series text files

- ROI time series array for all imaging volumes (will *not* be overwritten if it already exists)

- ROI time series split in time, as dictated by user input (will be overwritten if they already exist)


### Analysis and software versions

This code was written for Python 2.7

#### To reproduce time series in Figure 2 with make_roi_tseries.py, you will need:

- Functional imaging data and atlas ROIs from Mendeley Data (roi_timeseries_data.zip at http://dx.doi.org/10.17632/8b6nw2xxhn.1)

- AFNI

- FSL

#### Time series in the manuscript were produced with the following software versions:

- AFNI: version Aug 21 2015, AFNI_2011_12_21_1014

- FSL: version 5.0.9 
