#!/usr/bin/env python

#-----------------------------------------------------------------------------
# Script to:
# 1-create eroded atlas roi nifti files
# 2-motion correct functional data
# 3-extract/save eroded roi timeseries, split into separate blocks if desired
# Written by Courtney Gallen May 2015
# Usage: make_roi_tseries.py atlas_dir func_dir nsplit
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
#IMPORTS
#-----------------------------------------------------------------------------
import os,sys
import numpy as np
from os.path import join as pjoin
from glob import glob
import subprocess

#-----------------------------------------------------------------------------
#FUNCTIONS
#-----------------------------------------------------------------------------
        
def test_one_file(glob_result):
    '''Tests that only one file was returned from glob search
    '''
    if len(glob_result) != 1:
        sys.exit('more than one .nii.gz file: %s' %glob_result)
    else:
        return glob_result[0]

    
def run_command(command):
    '''runs commands with subprocess
    '''
    p = subprocess.Popen(command, stdout = subprocess.PIPE, shell = True)
    (tmpout, err) = p.communicate()
    return tmpout, err


def make_roi_niftis(roi_dir, atlas, roi_orig):
    '''Converts single ROI file with multiple ROI values to invidual files for
      each ROI with the original ROI value in the new ROI name
    '''
    print '---------------------------------------------'
    print 'making atlas roi files'

    # get the min and max values in the mask
    # NB: [each ROI should have a different overlay value]
    tmpout, err = run_command("""fslstats %s -R""" %(roi_orig))
    rmin, rmax = tmpout.split()

    # create range of roi numbers, excluding 0-value rois
    roi_values = range(int(float(rmin))+1, int(float(rmax))+1)
    
    # loop over the roi values and create a nifti for each
    new_dir = pjoin(roi_dir, 'niftis')
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
    for rnum in roi_values:
        # make new roi file name
        roi_new = pjoin(new_dir,'%s_%03d.nii.gz' %(atlas, rnum))
        command_roi = """3dcalc -a %s -expr 'within(a,%d,%d)' -prefix %s""" %(roi_orig, rnum,
                                                                              rnum, roi_new)
        # remove roi_new if exists already
        if os.path.exists(roi_new):
            os.remove(roi_new)
        # run command; some rois may be all zeros, will be handled later
        tmpout, err = run_command(command_roi)
        
    # get list of these new roi files
    new_rois = sorted(glob(pjoin(new_dir, '%s*nii.gz' %(atlas))))
    # check that all rois were made
    if len(new_rois) != len(roi_values):
        sys.exit('not all rois were made from %s' %roi_orig)
    
    return new_rois


def erode_roi_niftis(roi_dir, atlas, rois, elevel='1'):
    '''Erodes individual rois  by elevel
    '''
    print '---------------------------------------------'
    print 'eroding atlas roi files'

    # make erode directory
    erode_dir = pjoin(roi_dir, 'eroded_niftis')
    # if erode dir doesnt exist yet, make it
    if not os.path.exists(erode_dir):
        os.mkdir(erode_dir)
    
    # loop through rois, erode by elevel
    for ridx, roi in enumerate(rois):
        
        # make new roi file name
        roi_prefix = roi.split('/')[-1].strip('.nii.gz')  # roi name, without .nii.gz
        roi_new = pjoin(erode_dir, '%s_erode.nii.gz' %(roi_prefix))
        command_roi = """3dmask_tool -input %s -prefix %s -dilate_input -%s""" %(roi, roi_new,
                                                                                 elevel)
        # remove roi_new if exists already
        if os.path.exists(roi_new):
            os.remove(roi_new)
        # run command
        tmpout, err = run_command(command_roi)

    # get list of these new roi files
    new_rois = sorted(glob(pjoin(erode_dir, '%s*erode.nii.gz' %(atlas))))
    # check that all rois were made
    if len(new_rois) != len(rois):
        sys.exit('not all eroded rois were made in' %erode_dir)
    
    return new_rois


def moco_func_data(func_dir, func_data):
    '''Motion corrects functional data to a 100-volume mean
    NB: [will NOT overwrite mean and motion corrected files if they already exist,
    as the volreg step can be slow on large datasets]
    '''
    
    # make volreg directory
    volreg_dir = pjoin(func_dir, 'volreg')
    # if erode dir doesnt exist yet, make it
    if not os.path.exists(volreg_dir):
        os.mkdir(volreg_dir)

    # make 100-volume mean to generate motion correction base
    mean_fname = pjoin(volreg_dir, 'func_mean.nii.gz')
    mean_command = """3dTstat -mean -prefix %s '%s[0-99]'""" %(mean_fname, func_data)
    # only run if mean file does not yet exist
    if os.path.exists(mean_fname):
        print '*** WARNING: %s already exists, not overwriting ***' %mean_fname
    else:
        print '---------------------------------------------'
        print 'motion correcting func data'
        tmpout, err = run_command(mean_command)

    # motion correct to mean image using 3dvolreg
    volreg_fname = pjoin(volreg_dir, 'func_volreg.nii.gz')
    motion_fname = pjoin(volreg_dir, 'motion_params.1D')
    volreg_command = """3dvolreg -prefix %s -1Dfile %s -base %s %s""" %(volreg_fname, motion_fname,
                                                                        mean_fname, func_data)
    # only run if volreg file does not yet exist
    if os.path.exists(volreg_fname):
        print '*** WARNING: %s already exists, not overwriting ***' %volreg_fname
    else:
        tmpout, err = run_command(volreg_command)

    return volreg_fname

    
def get_roi_tseries(func_data, rois, ts_dir):
    '''Gets time series for each roi (average over voxels in each roi)
    NB: [will NOT run/overwrite full roi tseries if it already exists,
    as this step can be slow on large datasets and/or with many rois
    '''
    
    # only run if timeseries file does not yet exist in ts_dir
    ts_fname = pjoin(ts_dir, 'tseries_all.txt')
    
    if os.path.exists(ts_fname):
        print '*** WARNING: %s already exists, not overwriting ***' %ts_fname
        # load the existing file
        roi_all = np.loadtxt(ts_fname)

    else:
        print '---------------------------------------------'
        print 'getting roi timeseries'

        # get number of volumes (imaging frames)
        tmpout, err = run_command("""fslnvols %s""" %(func_data))
        out = tmpout.split()
        timeslen = int(out[0])

        # loop through rois to get timeseries across roi voxels
        for count,roi in enumerate(rois):

            # get the +1 index for roi (corresponding to number in roi filename)
            r = count+1

            # get number roi voxels
            tmpout, err = run_command("""fslstats %s -V""" %(roi))
            out = tmpout.split()
            roivol = float(out[0])

            # if no roi exists, make tseries all nans
            # typically, if roi was not imaged -or- not enough left after erosion
            if roivol==0:
                command = """roi%03d=np.empty((timeslen,))""" %(r)
                exec(command)
                command = """roi%03d.fill(np.nan)""" %(r)
                exec(command)

            # otherwise, get tseries for the roi
            else:
                # run mask ave command to get roi tseries
                tmpout, err = run_command("""3dmaskave -quiet -mask %s %s""" %(roi, func_data))
                out = tmpout.split()
                # add tseries to roi variable
                command = """roi%03d=np.asarray(out)""" %(r)
                exec(command)
                # change from array of strings to floats
                command = """roi%03d=roi%03d.astype(np.float)""" %(r,r) 
                exec(command)

            # add timeseries to roi_all array (shape = [nvolumes, nrois])
            if count==0:
                # need to make the roi_all variable
                command = """roi_all=np.hstack((roi%03d[:,np.newaxis]))""" %(r)
            elif count==1:
                 # need to add dimension to roi_all b/c it's still 1-d
                command = """roi_all=np.hstack((roi_all[:,np.newaxis],roi%03d[:,np.newaxis]))""" %(r)
            else:
                # add to existing roi_all variable
                command = """roi_all=np.hstack((roi_all,roi%03d[:,np.newaxis]))""" %(r)
            exec(command)

        # make ts_dir and save roi_all
        if not os.path.exists(ts_dir):
            os.mkdir(ts_dir)
        np.savetxt(ts_fname, roi_all, fmt = '%.12f', delimiter = '\t', newline = '\n')

    return roi_all


#-----------------------------------------------------------------------------
# Main Code
#-----------------------------------------------------------------------------
def main(argv = sys.argv):
    
    atlas_dir = argv[1] # path to directory with atlas file from alignment
    func_dir = argv[2] # path to directory with raw functional data
    nsplit = int(argv[3]) # number of resulting tseries (by splitting the tseries array)
    #-----
    # EXAMPLE:
    # atlas_dir = './vfb_nn' 
    # func_dir = './functional'
    # nsplit = 2
    #-----
    # NB:
    # *_dir inputs assume there is only ONE *.nii.gz file in each directory
    # *_dir inputs should not end in a slash (e.g., NOT ./vfb_nn/)
    # nsplit must equally divide original tseries
    # nsplit of 1 = no splitting
    #-----
    
    #-----
    ### Setup some output directories for roi tseries ###
    #-----
    # get atlas name (final directory in atlas_dir path)
    atlas_name = atlas_dir.split('/')[-1]
    # get dir for full tseries (all volumes)
    tseries_dir = pjoin(func_dir, 'volreg', atlas_name)
    
    #-----
    ### 1-Create eroded atlas rois ###
    #-----
    # get original roi file
    roi_files = glob(pjoin(atlas_dir,'*.nii.gz'))
    roi_orig = test_one_file(roi_files)
    
    # convert single roi atlas file, to individual nii files for each roi
    rois_new = make_roi_niftis(atlas_dir, atlas_name, roi_orig)
    
    # erode individual roi files by elevel (default is 1 voxel on all sides)
    rois_erode = erode_roi_niftis(atlas_dir, atlas_name, rois_new)
    
    #-----
    ### 2-Motion correct functional data ###
    #-----
    # get raw functional file
    func_files = glob(pjoin(func_dir, '*.nii.gz'))
    func_orig = test_one_file(func_files)
    
    # motion correct functional data (default is to 100-volume func. mean)
    volreg_data = moco_func_data(func_dir, func_orig)
    
    #-----
    ### 3-Get roi timeseries ###
    #-----
    # use 3dMaskAve to get/save an roi tseries array, with shape [nvolumes, nrois]
    tseries_all = get_roi_tseries(volreg_data, rois_erode, tseries_dir)
    
    # split the roi_all array by nsplit, along time dimension if nsplit > 1
    if nsplit == 1:
        print 'nsplit of 1 = the full tseries, not generating split tseries'

    else:
        # make split dir
        split_dir = pjoin(tseries_dir, 'nsplit_%d' %(nsplit))
        if not os.path.exists(split_dir):
            os.mkdir(split_dir)
        
        # split tseries_all along the time axis
        # creates a list of len (nsplit) with the split arrays
        tseries_split = np.split(tseries_all, nsplit, axis=0)

        # loop through each split file and save to split_dir (blocks are 1-indexed)
        for split in range(nsplit):
            
            # make block file name, blocks are 1-indexed
            block_num = split+1
            split_fname = pjoin(split_dir, 'tseries_block%02d.txt' %block_num)

            # load tseries for this split and save it
            split_data = tseries_split[split]
            np.savetxt(split_fname, split_data, fmt = '%.12f', delimiter = '\t', newline = '\n')

    print '---------------------------------------------'
    print 'FINISHED!'


if __name__ == '__main__':
    main()
