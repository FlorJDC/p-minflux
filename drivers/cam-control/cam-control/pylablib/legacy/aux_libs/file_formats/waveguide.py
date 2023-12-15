"""
File formats generated by the LabView code on the waveguide project.
"""


from io import open

from .cam import load_cam, iter_cam_frames, combine_cam_frames, save_cam, CamReader
from ...core.utils import string, funcargparse
from ...core.fileio import loadfile
from ...core.dataproc import interpolate, filters, waveforms
from ...core.datatable.table import DataTable
from ...core.datatable.wrapping import wrap
import os.path

import numpy as np



##### _info.txt format (file info) #####
def load_info(path):
    """
    Load the info file (ends with ``"_info.txt"``).

    Return information as a dictionary ``{name: value}``, where `value` is a list (single-element list for a scalar property).
    """
    nextline_markers=["locking scheme", "channels"]
    lines=[]
    with open(path) as f:
        for ln in f.readlines():
            ln=ln.strip()
            while ln.endswith(":"):
                ln=ln[:-1]
            items=[i.strip() for i in ln.split("\t")]
            items=[i for i in items if i]
            if items:
                lines.append(items)
    info_dict={}
    n=0
    while n<len(lines):
        ln=lines[n]
        if len(ln)==1 and ln[0].lower() in nextline_markers:
            key=ln[0].lower()
            if len(lines)==n+1:
                raise IOError("key line {} doesn't have a following value line".format(ln[0]))
            value=[string.from_string(i) for i in lines[n+1]]
            n+=1
        elif len(ln)>=2:
            key=ln[0].lower()
            value=[string.from_string(i) for i in ln[1:]]
        else:
            raise IOError("unusual line format: {}".format(ln))
        if key in info_dict:
            raise IOError("duplicate key: {}".format(key))
        info_dict[key]=value
        n+=1
    return info_dict


def _filter_channel_name(name):
    return name.replace(" ","").replace("-","_")
def load_sweep(prefix, force_info=True):
    """
    Load binary sweep located at ``prefix+".dat"`` with an associated info file located at ``prefix+"_info.txt"``.

    Return tuple ``(table, info)``, where `table` is the data table, and `info` is the info dictionary (see :func:`load_info`).
    If ``force_info==True``, raise an error if the info file is missing.
    The columns for `table` are extracted from the info file. If it is missing or the channels info is not in the file, `table` has a single column.
    """
    info_path=prefix+"_info.txt"
    if os.path.exists(info_path):
        info_dict=load_info(info_path)
    elif force_info:
        raise IOError("info file {} doesn't exits".format(info_path))
    else:
        info_dict={}
    if "channels" in info_dict:
        info_dict["channels"]=[_filter_channel_name(ch) for ch in info_dict["channels"]]
        channels=info_dict["channels"]
    else:
        channels=[]
    data_path=prefix+".dat"
    data=loadfile.load(data_path,"bin",dtype="<f8",columns=channels)
    return data,info_dict




##### Normalizing sweep (frequency and column data) #####
def cut_outliers(sweep, jump_size, length, padding=0, x_column=None, ignore_last=0):
    """
    Cut out sections of the waveform with large jumps.

    Remove sections of the waveform which are at most `length` long and have jumps of at least `jump_size` on both size.
    If ``padding>0``, remove additional `padding` points on both sides of the outlier section.
    if ``ignore_last>0``, do not consider jumps in the last `ignore_last` points.
    For multi-column data, `x_column` specifies the columns of interest.
    """
    xs=waveforms.get_x_column(sweep,x_column=x_column)
    dxs=xs[1:]-xs[:-1]
    jumps=abs(dxs)>jump_size
    jump_locs=np.append(jumps.nonzero()[0],[len(xs)-1])
    prev_jump=-1
    include=np.ones(len(xs)).astype("bool")
    for jl in jump_locs:
        if jl>len(include)-ignore_last:
            break
        if jl-prev_jump<length:
            start=max(prev_jump+1-padding,0)
            end=min(jl+1+padding,len(include))
            include[start:end]=False
        prev_jump=jl
    return wrap(sweep).t[include,:].copy()

def trim_jumps(sweep, jump_size, trim=1, x_column=None):
    """
    Clean up jumps in the data by removing several data points around them.

    Remove `trim` datapoints on both sides of jumps if at least `jump_size`.
    For multi-column data, `x_column` specifies the columns of interest.
    """
    if not isinstance(trim,(list,tuple)):
        trim=trim,trim
    xs=waveforms.get_x_column(sweep,x_column=x_column)
    dxs=xs[1:]-xs[:-1]
    jumps=abs(dxs)>jump_size
    jump_locs=jumps.nonzero()[0]
    include=np.ones(len(xs)).astype("bool")
    for jl in jump_locs:
        start=max(jl-trim[0]+1,0)
        end=min(jl+1+trim[1],len(include))
        include[start:end]=False
    return wrap(sweep).t[include,:].copy()

def prepare_sweep_frequency(sweep, allowed_frequency_jump=None, ascending_frequency=True, rescale=True):
    """
    Clean up the sweep frequency data (exclude jumps and rescale in Hz).
    
    Find the longest continuous chunk with frequency steps within `allowed_frequency_jump' range (by default, it is ``(-5*mfs,infty)``, where ``mfs`` is the median frequency step).
    If ``ascending_frequency==True``, sort the data so that frequency is in the ascending order.
    If ``rescale==True``, rescale frequency in Hz.
    """
    if rescale:
        sweep["Wavemeter"]*=1E12
    if len(sweep)>1:
        fs=sweep["Wavemeter"]
        dfs=fs[1:]-fs[:-1]
        fdir=1. if np.sum(dfs>0)>len(dfs)//2 else -1.
        valid_dfs=(dfs*fdir)>0
        if allowed_frequency_jump=="auto":
            mfs=np.median(dfs[valid_dfs])
            maxfs=fdir*np.max(dfs[valid_dfs]*fdir)
            allowed_frequency_jump=(-10*mfs, 1.1*maxfs )
        if allowed_frequency_jump is not None:
            bins=filters.collect_into_bins(fs,allowed_frequency_jump,preserve_order=True,to_return="index")
            max_bin=sorted(bins, key=lambda b: b[1]-b[0])[-1]
            sweep=sweep.t[max_bin[0]:max_bin[1],:]
        if ascending_frequency:
            sweep=sweep.sort_by("Wavemeter")
    return sweep

def interpolate_sweep(sweep, columns, frequency_step, rng=None, frequency_column="Wavemeter"):
    """
    Interpolate sweep data over a regular frequency grid with the spacing `frequency_step`.
    """
    rng_min,rng_max=rng or (None,None)
    rng_min=sweep[frequency_column].min() if (rng_min is None) else rng_min
    rng_max=sweep[frequency_column].max() if (rng_max is None) else rng_max
    start_freq=(rng_min//frequency_step)*frequency_step
    stop_freq=(rng_max//frequency_step)*frequency_step
    columns=[funcargparse.as_sequence(c,2) for c in columns]
    freqs=np.arange(start_freq,stop_freq+frequency_step/2.,frequency_step)
    data=[interpolate.interpolate1D(sweep[:,[frequency_column,src]],freqs,bounds_error=False,fill_values="bounds") for src,_ in columns]
    return DataTable([freqs]+data,["Frequency"]+[dst for _,dst in columns])



rep_suffix_patt="_rep_{:03d}"
def load_prepared_sweeps(prefix, reps, min_sweep_length=1, **add_info):
    """
    Load sweeps with the given `prefix` and `reps` and normalize their frequency axes.

    Return list of tuples ``(sweep, info)``. `add_info` is added to the `info` dictionary (`rep` index is added automatically).
    `min_sweep_length` specifies the minimal sweep length (after frequency normalization) to be included in the list.
    """
    sweeps=[]
    if reps:
        for rep in reps:
            sweep_name=prefix+rep_suffix_patt.format(rep)
            sweeps+=load_prepared_sweeps(sweep_name,[],min_sweep_length=min_sweep_length,rep=rep,**add_info)
    else:
        try:
            sweep,info=load_sweep(prefix,force_info=True)
            sweep=prepare_sweep_frequency(sweep)
            if len(sweep)>=min_sweep_length:
                info["rep"]=0
                info.update(add_info)
                sweeps.append((sweep,info))
        except IOError:
            pass
    return sweeps